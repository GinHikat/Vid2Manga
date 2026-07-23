import os
import cv2
import torch
import numpy as np
from PIL import Image
from typing import Tuple, List, Dict, Any, Optional

class PersonSegmenter:
    """Class wrapper responsible for loading and running the Mask2Former universal segmentation model."""

    def __init__(self, checkpoint: Optional[str] = None, device: Optional[str] = None):
        """Initializes the segmenter with device and model checkpoint.

        Args:
            checkpoint: HuggingFace model checkpoint path.
            device: Device to run inference on (cuda or cpu).
        """
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        self.checkpoint = checkpoint or "qubvel-hf/finetune-instance-segmentation-ade20k-mini-mask2former"
        self.model = None
        self.processor = None
        self.onnx_session = None
        self.use_onnx = False
        self.id2label = None

    def load(self):
        """Lazy-loads ONNX INT8 model if available, otherwise loads PyTorch Mask2Former model."""
        if self.model is None and self.onnx_session is None:
            from core.config import settings
            onnx_path = os.path.join(settings.BASE_DIR, "models_onnx", "mask2former_int8.onnx")
            
            # Auto-detect pre-baked ONNX INT8 model for ultra-low RAM usage (<200MB)
            if os.path.exists(onnx_path):
                try:
                    import onnxruntime as ort
                    from transformers import Mask2FormerImageProcessor, AutoConfig
                    opts = ort.SessionOptions()
                    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                    opts.intra_op_num_threads = 2
                    self.onnx_session = ort.InferenceSession(
                        onnx_path, 
                        sess_options=opts, 
                        providers=["CPUExecutionProvider"]
                    )
                    self.processor = Mask2FormerImageProcessor.from_pretrained(self.checkpoint)
                    cfg = AutoConfig.from_pretrained(self.checkpoint)
                    self.id2label = cfg.id2label
                    self.use_onnx = True
                    print(f"Loaded ONNX INT8 PersonSegmenter model from {onnx_path}!")
                    return self
                except Exception as e:
                    print(f"ONNX initialization failed, falling back to PyTorch: {e}")

            # PyTorch fallback
            from transformers import Mask2FormerForUniversalSegmentation, Mask2FormerImageProcessor
            self.model = Mask2FormerForUniversalSegmentation.from_pretrained(
                self.checkpoint
            ).to(self.device)
            self.processor = Mask2FormerImageProcessor.from_pretrained(self.checkpoint)
            self.model.eval()
            self.id2label = self.model.config.id2label
            self.use_onnx = False
        return self

    def unload(self):
        """Frees model tensors and triggers garbage collection to prevent OOM."""
        self.model = None
        self.processor = None
        self.onnx_session = None
        self.use_onnx = False
        self.id2label = None
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def segment(self, image_input: Any, min_area: int = 700, min_score: float = 0.7) -> Tuple[np.ndarray, np.ndarray, List[np.ndarray], Dict[str, Any]]:
        """Segments person instances in an image path, PIL Image, or NumPy array.

        Args:
            image_input: Absolute file path (str), PIL.Image object, or NumPy array.
            min_area: Minimum pixel area for a mask to be kept.
            min_score: Minimum confidence score for a mask to be kept.

        Returns:
            A tuple containing:
                - image_np: The original image as an RGB NumPy array.
                - instance_map: 2D array where values represent instance IDs.
                - person_masks: List of binary masks (0 or 1) for each person instance.
                - outputs: The raw post-processed output dictionary.
        """
        if self.model is None and self.onnx_session is None:
            self.load()
            
        if isinstance(image_input, str):
            image = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, Image.Image):
            image = image_input.convert("RGB")
        elif isinstance(image_input, np.ndarray):
            if image_input.shape[2] == 3:
                # Convert BGR to RGB if OpenCV array
                image_rgb = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(image_rgb)
            else:
                image = Image.fromarray(image_input).convert("RGB")
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        image_np = np.array(image)

        # Downscale image copy for model input to keep RAM footprint low (<200MB)
        max_dim = 480
        orig_w, orig_h = image.size
        if max(orig_w, orig_h) > max_dim:
            scale = max_dim / float(max(orig_w, orig_h))
            new_w, new_h = max(1, int(orig_w * scale)), max(1, int(orig_h * scale))
            image_small = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        else:
            image_small = image

        if self.use_onnx:
            # Low-RAM ONNX Runtime C++ engine execution (<30MB framework RAM)
            inputs = self.processor(images=[image_small], return_tensors="np")
            onnx_inputs = {"pixel_values": inputs["pixel_values"]}
            class_logits, mask_logits = self.onnx_session.run(None, onnx_inputs)
            
            from transformers.modeling_outputs import ModelOutput
            raw_outputs = ModelOutput(
                class_queries_logits=torch.from_numpy(class_logits),
                masks_queries_logits=torch.from_numpy(mask_logits)
            )
            outputs = self.processor.post_process_instance_segmentation(
                raw_outputs,
                target_sizes=[image_np.shape[:2]],
                threshold=0.3,
                mask_threshold=0.3
            )[0]
            instance_map = outputs["segmentation"].numpy() if hasattr(outputs["segmentation"], "numpy") else np.array(outputs["segmentation"])
        else:
            # Native PyTorch execution
            with torch.no_grad():
                inputs = self.processor(images=[image_small], return_tensors="pt").to(self.device)
                raw_outputs = self.model(**inputs)
                outputs = self.processor.post_process_instance_segmentation(
                    raw_outputs, 
                    target_sizes=[image_np.shape[:2]], 
                    threshold=0.3, 
                    mask_threshold=0.3
                )[0]
            instance_map = outputs["segmentation"].cpu().numpy()
            del inputs, raw_outputs

        # Identify label ID for 'person'
        person_label_id = next((k for k, v in self.id2label.items() if v == "person"), 12) if self.id2label else 12
        
        person_masks = []
        if person_label_id is not None:
            for segment_info in outputs["segments_info"]:
                # Filter by label, confidence score, and area
                if segment_info["label_id"] == person_label_id and segment_info["score"] > min_score:
                    # Create binary mask for this specific person instance
                    mask = (instance_map == segment_info["id"]).astype(np.uint8)
                    area = np.sum(mask)
                    
                    if area >= min_area:
                        person_masks.append(mask)

        return image_np, instance_map, person_masks, {}
