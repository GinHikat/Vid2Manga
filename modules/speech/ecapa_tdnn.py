import os
import urllib.request
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchaudio

def length_to_mask(length, max_len=None, dtype=torch.float, device=None):
    """Creates a binary mask from sequence lengths.

    Args:
        length: Tensor of sequence lengths.
        max_len: Maximum length for the mask.
        dtype: Data type of the mask.
        device: Target device for the mask.

    Returns:
        Binary mask tensor of shape (batch, max_len).
    """
    assert len(length.shape) == 1
    if max_len is None:
        max_len = int(length.max().item())
    batch_size = length.shape[0]
    arange = torch.arange(max_len, device=device or length.device).unsqueeze(0).expand(batch_size, -1)
    mask = arange < length.unsqueeze(1)
    return mask.to(dtype)

class TDNNBlock(nn.Module):
    """Time-Delay Neural Network block using standard PyTorch.

    Args:
        in_channels: Number of expected input channels.
        out_channels: Number of output channels.
        kernel_size: The kernel size of the Conv1d layer.
        dilation: The dilation parameter of the Conv1d layer.
        groups: Number of blocked connections from input to output.
        dropout: Rate of dropout applied to the channels.
    """
    def __init__(self, in_channels, out_channels, kernel_size, dilation, groups=1, dropout=0.0):
        super().__init__()
        padding = (kernel_size - 1) * dilation // 2
        self.conv = nn.Conv1d(
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=kernel_size,
            dilation=dilation,
            padding=padding,
            groups=groups
        )
        self.activation = nn.ReLU()
        self.norm = nn.BatchNorm1d(out_channels)
        self.dropout = nn.Dropout(p=dropout)

    def forward(self, x):
        """Performs a forward pass of the TDNN block."""
        return self.dropout(self.norm(self.activation(self.conv(x))))

class Res2NetBlock(nn.Module):
    """Multi-scale residual block w/ dilation.

    Args:
        in_channels: Number of input channels.
        out_channels: Number of output channels.
        scale: The scale factor of the Res2Net block.
        kernel_size: The kernel size of the internal blocks.
        dilation: The dilation parameter of the internal blocks.
        dropout: Rate of dropout applied to channels.
    """
    def __init__(self, in_channels, out_channels, scale=8, kernel_size=3, dilation=1, dropout=0.0):
        super().__init__()
        assert in_channels % scale == 0
        assert out_channels % scale == 0

        in_channel = in_channels // scale
        hidden_channel = out_channels // scale

        self.blocks = nn.ModuleList(
            [
                TDNNBlock(
                    in_channel,
                    hidden_channel,
                    kernel_size=kernel_size,
                    dilation=dilation,
                    dropout=dropout,
                )
                for _ in range(scale - 1)
            ]
        )
        self.scale = scale

    def forward(self, x):
        """Performs a forward pass of the Res2Net block."""
        y = []
        for i, x_i in enumerate(torch.chunk(x, self.scale, dim=1)):
            if i == 0:
                y_i = x_i
            elif i == 1:
                y_i = self.blocks[i - 1](x_i)
            else:
                y_i = self.blocks[i - 1](x_i + y_i)
            y.append(y_i)
        return torch.cat(y, dim=1)

class SEBlock(nn.Module):
    """Squeeze-and-Excitation channel attention block.

    Args:
        in_channels: Number of expected input channels.
        se_channels: Number of channels after squeeze bottleneck.
        out_channels: Number of output channels.
    """
    def __init__(self, in_channels, se_channels, out_channels):
        super().__init__()
        self.conv1 = nn.Conv1d(
            in_channels=in_channels, out_channels=se_channels, kernel_size=1
        )
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv1d(
            in_channels=se_channels, out_channels=out_channels, kernel_size=1
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, x, lengths=None):
        """Performs a forward pass of the Squeeze-and-Excitation block."""
        L = x.shape[-1]
        if lengths is not None:
            mask = length_to_mask(lengths * L, max_len=L, device=x.device)
            mask = mask.unsqueeze(1)
            total = mask.sum(dim=2, keepdim=True)
            s = (x * mask).sum(dim=2, keepdim=True) / total
        else:
            s = x.mean(dim=2, keepdim=True)

        s = self.relu(self.conv1(s))
        s = self.sigmoid(self.conv2(s))
        return s * x

class AttentiveStatisticsPooling(nn.Module):
    """Attentive statistics pooling layer for channel-wise mean and standard deviation.

    Args:
        channels: Number of input channels.
        attention_channels: Number of attention channels.
        global_context: Whether to concatenate global context statistics.
    """
    def __init__(self, channels, attention_channels=128, global_context=True):
        super().__init__()
        self.eps = 1e-12
        self.global_context = global_context
        if global_context:
            self.tdnn = TDNNBlock(channels * 3, attention_channels, 1, 1)
        else:
            self.tdnn = TDNNBlock(channels, attention_channels, 1, 1)
        self.tanh = nn.Tanh()
        self.conv = nn.Conv1d(
            in_channels=attention_channels, out_channels=channels, kernel_size=1
        )

    def forward(self, x, lengths=None):
        """Performs statistical aggregation over the channel dimension."""
        L = x.shape[-1]

        def _compute_statistics(x_tensor, m_tensor, dim=2, eps_val=self.eps):
            mean = (m_tensor * x_tensor).sum(dim)
            std = torch.sqrt(
                (m_tensor * (x_tensor - mean.unsqueeze(dim)).pow(2)).sum(dim).clamp(eps_val)
            )
            return mean, std

        if lengths is None:
            lengths = torch.ones(x.shape[0], device=x.device)

        mask = length_to_mask(lengths * L, max_len=L, device=x.device)
        mask = mask.unsqueeze(1)

        if self.global_context:
            total = mask.sum(dim=2, keepdim=True).float()
            mean, std = _compute_statistics(x, mask / total)
            mean = mean.unsqueeze(2).repeat(1, 1, L)
            std = std.unsqueeze(2).repeat(1, 1, L)
            attn = torch.cat([x, mean, std], dim=1)
        else:
            attn = x

        attn = self.conv(self.tanh(self.tdnn(attn)))
        attn = attn.masked_fill(mask == 0, float("-inf"))
        attn = F.softmax(attn, dim=2)
        
        mean, std = _compute_statistics(x, attn)
        pooled_stats = torch.cat((mean, std), dim=1)
        return pooled_stats.unsqueeze(2)

class SERes2NetBlock(nn.Module):
    """Diarization building block comprising TDNN, Res2Net, TDNN, and SEBlock.

    Args:
        in_channels: Number of expected input channels.
        out_channels: Number of output channels.
        res2net_scale: Scale factor for the Res2Net block.
        se_channels: Bottleneck channel dimension of SEBlock.
        kernel_size: Kernel size of intermediate Conv layers.
        dilation: Dilation rate of intermediate Conv layers.
        groups: Channel grouping factor.
        dropout: Channel dropout rate.
    """
    def __init__(
        self,
        in_channels,
        out_channels,
        res2net_scale=8,
        se_channels=128,
        kernel_size=1,
        dilation=1,
        groups=1,
        dropout=0.0,
    ):
        super().__init__()
        self.out_channels = out_channels
        self.tdnn1 = TDNNBlock(
            in_channels,
            out_channels,
            kernel_size=1,
            dilation=1,
            groups=groups,
            dropout=dropout,
        )
        self.res2net_block = Res2NetBlock(
            out_channels, out_channels, res2net_scale, kernel_size, dilation
        )
        self.tdnn2 = TDNNBlock(
            out_channels,
            out_channels,
            kernel_size=1,
            dilation=1,
            groups=groups,
            dropout=dropout,
        )
        self.se_block = SEBlock(out_channels, se_channels, out_channels)

        self.shortcut = None
        if in_channels != out_channels:
            self.shortcut = nn.Conv1d(
                in_channels=in_channels,
                out_channels=out_channels,
                kernel_size=1,
            )

    def forward(self, x, lengths=None):
        """Performs a forward pass of the combined SERes2Net block."""
        residual = x
        if self.shortcut:
            residual = self.shortcut(x)

        x = self.tdnn1(x)
        x = self.res2net_block(x)
        x = self.tdnn2(x)
        x = self.se_block(x, lengths)
        return x + residual

class ECAPA_TDNN(nn.Module):
    """Pre-trained compatible implementation of ECAPA-TDNN using pure PyTorch.

    Args:
        input_size: Dimension of input acoustic features (standard is 80).
        lin_neurons: Output dimension of speaker embeddings (standard is 192).
        channels: List of channel dimensions for the network blocks.
        kernel_sizes: List of kernel sizes for the network blocks.
        dilations: List of dilation rates for the network blocks.
        attention_channels: Size of attention channels in pooling layer.
        res2net_scale: Scale parameter for Res2Net blocks.
        se_channels: Bottleneck channels for SE blocks.
        global_context: Whether pooling utilizes global statistic context.
        groups: List of grouping factors for the network blocks.
        dropout: Channel dropout rate.
    """
    def __init__(
        self,
        input_size=80,
        lin_neurons=192,
        channels=[1024, 1024, 1024, 1024, 3072],
        kernel_sizes=[5, 3, 3, 3, 1],
        dilations=[1, 2, 3, 4, 1],
        attention_channels=128,
        res2net_scale=8,
        se_channels=128,
        global_context=True,
        groups=[1, 1, 1, 1, 1],
        dropout=0.0,
    ):
        super().__init__()
        assert len(channels) == len(kernel_sizes)
        assert len(channels) == len(dilations)
        self.channels = channels
        self.blocks = nn.ModuleList()

        # Initial TDNN layer
        self.blocks.append(
            TDNNBlock(
                input_size,
                channels[0],
                kernel_sizes[0],
                dilations[0],
                groups[0],
                dropout,
            )
        )

        # Multi scale res2net layers
        for i in range(1, len(channels) - 1):
            self.blocks.append(
                SERes2NetBlock(
                    channels[i - 1],
                    channels[i],
                    res2net_scale=res2net_scale,
                    se_channels=se_channels,
                    kernel_size=kernel_sizes[i],
                    dilation=dilations[i],
                    groups=groups[i],
                    dropout=dropout,
                )
            )

        # Feature aggregation
        self.mfa = TDNNBlock(
            channels[-2] * (len(channels) - 2),
            channels[-1],
            kernel_sizes[-1],
            dilations[-1],
            groups=groups[-1],
            dropout=dropout,
        )

        # Attentive statistical pooling
        self.asp = AttentiveStatisticsPooling(
            channels[-1],
            attention_channels=attention_channels,
            global_context=global_context,
        )
        self.asp_bn = nn.BatchNorm1d(channels[-1] * 2)

        # Final linear embedding projection
        self.fc = nn.Conv1d(
            in_channels=channels[-1] * 2,
            out_channels=lin_neurons,
            kernel_size=1,
        )

    def forward(self, x, lengths=None):
        """Processes 80-dimensional acoustic features and projects to embeddings."""
        # Expected input shape: (batch, time, channel)
        x = x.transpose(1, 2)

        xl = []
        for layer in self.blocks:
            if isinstance(layer, TDNNBlock):
                x = layer(x)
            else:
                x = layer(x, lengths=lengths)
            xl.append(x)

        x = torch.cat(xl[1:], dim=1)
        x = self.mfa(x)
        x = self.asp(x, lengths=lengths)
        x = self.asp_bn(x)
        x = self.fc(x)
        return x.transpose(1, 2)

class PretrainedECAPATDNN(nn.Module):
    """Wrapper that manages pre-trained VoxCeleb model downloads and feature extraction.

    Args:
        model_dir: Directory where pre-trained checkpoints are saved.
        device: Run execution on cpu or cuda.
    """
    def __init__(self, model_dir="secrets/models", device="cpu"):
        super().__init__()
        self.device = torch.device(device)
        self.model_dir = model_dir
        self.checkpoint_path = os.path.join(model_dir, "spkrec-ecapa-voxceleb.ckpt")
        
        # Instantiate model matching VoxCeleb parameters
        self.model = ECAPA_TDNN(
            input_size=80,
            lin_neurons=192,
            channels=[1024, 1024, 1024, 1024, 3072]
        )
        
        # Audio feature extraction parameters matching training
        self.mel_transform = torchaudio.transforms.MelSpectrogram(
            sample_rate=16000,
            n_fft=400,
            win_length=400,
            hop_length=160,
            f_min=0,
            f_max=8000,
            n_mels=80,
            window_fn=torch.hamming_window
        )
        
        self._load_weights()
        self.model.to(self.device)
        self.mel_transform.to(self.device)
        self.model.eval()

    def _load_weights(self):
        """Downloads and maps official SpeechBrain state dict weights to vanilla model."""
        if not os.path.exists(self.checkpoint_path):
            os.makedirs(self.model_dir, exist_ok=True)
            url = "https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb/resolve/main/embedding_model.ckpt"
            print(f"Downloading pre-trained ECAPA-TDNN weights to {self.checkpoint_path}...")
            urllib.request.urlretrieve(url, self.checkpoint_path)
            print("Download completed successfully.")

        try:
            state_dict = torch.load(self.checkpoint_path, map_location="cpu")
            # If standard nested checkpoints are stored, extract core model keys
            if "model" in state_dict:
                state_dict = state_dict["model"]
            
            # Map SpeechBrain custom layers to vanilla PyTorch equivalents
            mapped_state_dict = {}
            for k, v in state_dict.items():
                if k.endswith(".num_batches_tracked"):
                    continue
                
                new_k = k
                new_k = new_k.replace(".conv.conv.", ".conv.")
                new_k = new_k.replace(".norm.norm.", ".norm.")
                new_k = new_k.replace(".conv1.conv.", ".conv1.")
                new_k = new_k.replace(".conv2.conv.", ".conv2.")
                
                # fc and asp_bn wrappers mapping
                if new_k == "fc.conv.weight":
                    new_k = "fc.weight"
                elif new_k == "fc.conv.bias":
                    new_k = "fc.bias"
                elif new_k == "asp_bn.norm.weight":
                    new_k = "asp_bn.weight"
                elif new_k == "asp_bn.norm.bias":
                    new_k = "asp_bn.bias"
                elif new_k == "asp_bn.norm.running_mean":
                    new_k = "asp_bn.running_mean"
                elif new_k == "asp_bn.norm.running_var":
                    new_k = "asp_bn.running_var"
                    
                mapped_state_dict[new_k] = v
                
            self.model.load_state_dict(mapped_state_dict, strict=False)
        except Exception as e:
            print(f"Failed to load standard state dict: {e}")
            raise

    def extract_embedding(self, waveform: torch.Tensor) -> torch.Tensor:
        """Extracts a 192-dimensional speaker embedding from a raw audio waveform.

        Args:
            waveform: Float audio tensor of shape (channels, time) or (batch, channels, time).

        Returns:
            Normalized speaker embedding tensor of shape (batch, 192).
        """
        # Ensure tensor matches working device
        waveform = waveform.to(self.device)
        
        # Handle batch dimensions
        if len(waveform.shape) == 1:
            waveform = waveform.unsqueeze(0)
        elif len(waveform.shape) == 3:
            # Squeeze channel dimension if 1 channel
            if waveform.shape[1] == 1:
                waveform = waveform.squeeze(1)
            else:
                # Merge multi channel into mono
                waveform = torch.mean(waveform, dim=1)

        with torch.no_grad():
            # Compute Mel spectrogram features
            mel_spec = self.mel_transform(waveform)
            # Log transform
            log_mel = torch.log(mel_spec + 1e-6)
            # Cepstral Mean and Variance Normalization over time dimension
            log_mel = log_mel - log_mel.mean(dim=-1, keepdim=True)
            # Reshape from (batch, mels, time) to (batch, time, mels)
            log_mel = log_mel.transpose(1, 2)
            
            # Run model forward pass
            embeddings = self.model(log_mel)
            # Squeeze intermediate time dimension to get shape (batch, 192)
            embeddings = embeddings.squeeze(1)
            # Normalize embeddings along the vector space for cosine distance similarity
            embeddings = F.normalize(embeddings, p=2, dim=-1)
            
        return embeddings
