import os
import torch
import numpy as np
from PIL import Image
from transformers import Mask2FormerForUniversalSegmentation, Mask2FormerImageProcessor
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

    def load(self):
        """Lazy-loads the Mask2Former model and processor into memory."""
        if self.model is None:
            print(f"Loading model from {self.checkpoint}...")
            self.model = Mask2FormerForUniversalSegmentation.from_pretrained(
                self.checkpoint
            ).to(self.device)
            self.processor = Mask2FormerImageProcessor.from_pretrained(self.checkpoint)
            self.model.eval()
        return self

    def segment(self, image_path: str, min_area: int = 700, min_score: float = 0.7) -> Tuple[np.ndarray, np.ndarray, List[np.ndarray], Dict[str, Any]]:
        """Segments person instances in an image.

        Args:
            image_path: Absolute path to the input image.
            min_area: Minimum pixel area for a mask to be kept.
            min_score: Minimum confidence score for a mask to be kept.

        Returns:
            A tuple containing:
                - image_np: The original image as an RGB NumPy array.
                - instance_map: 2D array where values represent instance IDs.
                - person_masks: List of binary masks (0 or 1) for each person instance.
                - outputs: The raw post-processed output dictionary.
        """
        if self.model is None:
            self.load()
            
        image = Image.open(image_path).convert("RGB")
        image_np = np.array(image)

        # Prepare inputs for the model
        inputs = self.processor(images=[image], return_tensors="pt").to(self.device)
        
        # Inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            
        # Post-processing
        outputs = self.processor.post_process_instance_segmentation(
            outputs, 
            target_sizes=[image_np.shape[:2]], 
            threshold=0.3, 
            mask_threshold=0.3
        )[0]

        instance_map = outputs["segmentation"].cpu().numpy()

        # Identify label ID for 'person'
        person_label_id = next((k for k, v in self.model.config.id2label.items() if v == "person"), None)
        
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
                    else:
                        print(f"Skipping instance {segment_info['id']} with area {area}")
                elif segment_info["label_id"] == person_label_id:
                    print(f"Skipping instance {segment_info['id']} with low score {segment_info['score']:.2f}")

        return image_np, instance_map, person_masks, outputs
