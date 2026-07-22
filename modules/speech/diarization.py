import os
import torch
import numpy as np
try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except (ImportError, OSError) as e:
    print(f"Warning: soundfile system dependencies (libsndfile) not found: {e}")
    sf = None
    SOUNDFILE_AVAILABLE = False

import wave
from typing import List, Dict, Any
from sklearn.cluster import AgglomerativeClustering
import torchaudio.functional as F_audio

from .ecapa_tdnn import PretrainedECAPATDNN

def _load_audio_waveform(audio_path: str) -> tuple[torch.Tensor, int]:
    """Loads audio into a (1, N) float32 Tensor at 16kHz using soundfile or wave stdlib."""
    if SOUNDFILE_AVAILABLE and sf is not None:
        try:
            data, sr = sf.read(audio_path)
            if len(data.shape) == 1:
                waveform = torch.from_numpy(data).float().unsqueeze(0)
            else:
                waveform = torch.from_numpy(data).float().transpose(0, 1)
            return waveform, sr
        except Exception:
            pass

    # Standard Python wave stdlib fallback (zero external C dependencies)
    with wave.open(audio_path, 'rb') as wf:
        sr = wf.getframerate()
        n_channels = wf.getnchannels()
        n_frames = wf.getnframes()
        raw_bytes = wf.readframes(n_frames)
        sample_width = wf.getsampwidth()

        if sample_width == 2:
            data_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        elif sample_width == 4:
            data_np = np.frombuffer(raw_bytes, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            data_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        if n_channels > 1:
            data_np = data_np.reshape(-1, n_channels).T
            waveform = torch.from_numpy(data_np).float()
        else:
            waveform = torch.from_numpy(data_np).float().unsqueeze(0)

        return waveform, sr

class LocalDiarizer:
    """Handles offline zero-shot speaker diarization using pre-trained ECAPA-TDNN and AHC.

    This replaces heavy external packages (like pyannote and speechbrain) with a standalone,
    fully local pipeline requiring no internet connection or Hugging Face authentication tokens.
    """

    def __init__(self, model_dir: str = "secrets/models"):
        """Initializes the diarization parameters.

        Args:
            model_dir: Directory where pre-trained model checkpoints are saved.
        """
        self.model_dir = model_dir
        self.embedding_model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def load(self):
        """Lazy-loads the pre-trained ECAPA-TDNN speaker embedding model."""
        if self.embedding_model is None:
            print("Loading offline ECAPA-TDNN speaker embedding model...")
            self.embedding_model = PretrainedECAPATDNN(model_dir=self.model_dir, device=str(self.device))
            print("Offline speaker embedding model loaded successfully.")

    def diarize(self, audio_path: str, min_speakers: int = 1, max_speakers: int = 8) -> List[Dict[str, Any]]:
        """Performs zero-shot speaker diarization on a WAV audio file.

        Args:
            audio_path: Absolute path to the WAV audio file (16kHz standard).
            min_speakers: Minimum estimated speakers in clustering.
            max_speakers: Maximum estimated speakers in clustering.

        Returns:
            A list of segments with 'speaker', 'start', and 'end' keys.
        """
        self.load()
        if self.embedding_model is None:
            print("Diarization: skipped because embedding model could not be loaded.")
            return []

        try:
            waveform, sr = _load_audio_waveform(audio_path)
            if sr != 16000:
                waveform = F_audio.resample(waveform, sr, 16000)
                sr = 16000
        except Exception as e:
            print(f"Diarization: Failed to load audio file: {e}")
            return []

        # Convert multi-channel to mono average
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)

        waveform_np = waveform.squeeze().numpy()
        total_samples = len(waveform_np)

        # Sliding window parameters: 1.5s window width, 0.75s step
        window_size_sec = 1.5
        step_sec = 0.75
        window_samples = int(window_size_sec * sr)
        step_samples = int(step_sec * sr)

        # 1. Slide windows and compute root-mean-square (RMS) energy for Voice Activity Detection
        raw_rms = []
        temp_idx = 0
        while temp_idx + window_samples <= total_samples:
            segment = waveform_np[temp_idx : temp_idx + window_samples]
            rms = np.sqrt(np.mean(segment**2))
            raw_rms.append(rms)
            temp_idx += step_samples

        if not raw_rms:
            return []

        # Calculate a dynamic VAD noise floor
        rms_threshold = np.median(raw_rms) * 0.5
        rms_threshold = max(rms_threshold, 0.005) # Keep a standard minimum threshold constraint

        # 2. Extract speaker embeddings for active voice windows
        embeddings = []
        timestamps = []
        idx = 0
        while idx + window_samples <= total_samples:
            segment_np = waveform_np[idx : idx + window_samples]
            rms = np.sqrt(np.mean(segment_np**2))
            
            if rms >= rms_threshold:
                segment_tensor = torch.from_numpy(segment_np).float()
                
                # Extract 192-dimensional L2-normalized embedding
                with torch.no_grad():
                    # extract_embedding expects shape (channels, time) or (time,)
                    emb = self.embedding_model.extract_embedding(segment_tensor)
                    embeddings.append(emb.cpu().numpy()[0])
                    
                start_sec = idx / sr
                end_sec = (idx + window_samples) / sr
                timestamps.append((start_sec, end_sec))
                
            idx += step_samples

        if not embeddings:
            print("Diarization: No active speech segments detected above VAD threshold.")
            return []

        embeddings = np.array(embeddings)
        num_segments = len(embeddings)

        # 3. Perform unsupervised clustering to group speaker identity
        if num_segments < 2:
            labels = np.zeros(num_segments, dtype=int)
            k_speakers = 1
        else:
            # Precompute pairwise cosine distance matrix (Cosine distance = 1.0 - Cosine similarity)
            similarity_matrix = np.dot(embeddings, embeddings.T)
            cosine_distances = np.clip(1.0 - similarity_matrix, 0.0, 2.0)
            
            # Determine optimal speaker count dynamically
            limit = min(max_speakers, num_segments)
            best_k = min_speakers
            best_score = -1
            best_labels = None
            
            for k in range(min_speakers, limit + 1):
                if k >= num_segments:
                    break
                ahc = AgglomerativeClustering(
                    n_clusters=k,
                    metric='precomputed',
                    linkage='average'
                )
                lbls = ahc.fit_predict(cosine_distances)
                
                from sklearn.metrics import silhouette_score
                try:
                    score = silhouette_score(cosine_distances, lbls, metric='precomputed')
                    if score > best_score:
                        best_score = score
                        best_k = k
                        best_labels = lbls
                except:
                    pass
            
            if best_labels is not None:
                labels = best_labels
                k_speakers = best_k
            else:
                # Fallback to Agglomerative Clustering with a strict threshold (cosine cutoff)
                ahc = AgglomerativeClustering(
                    n_clusters=None,
                    distance_threshold=0.65,
                    metric='precomputed',
                    linkage='average'
                )
                labels = ahc.fit_predict(cosine_distances)
                k_speakers = len(np.unique(labels))

        print(f"Diarization: Discovered {k_speakers} speakers across {num_segments} windows.")

        # 4. Group adjacent/overlapping windows with identical speaker labels into continuous turns
        raw_segments = []
        for i in range(num_segments):
            raw_segments.append({
                "speaker": f"Speaker {labels[i] + 1}",
                "start": timestamps[i][0],
                "end": timestamps[i][1]
            })

        # Merge consecutive turns
        merged_segments = []
        if raw_segments:
            current = raw_segments[0]
            for next_seg in raw_segments[1:]:
                # If same speaker and adjacent (gap <= 0.8s), combine them
                if next_seg["speaker"] == current["speaker"] and next_seg["start"] <= current["end"] + 0.8:
                    current["end"] = next_seg["end"]
                else:
                    merged_segments.append(current)
                    current = next_seg
            merged_segments.append(current)

        return merged_segments

# Singleton instance for modular usage
diarizer = LocalDiarizer()
