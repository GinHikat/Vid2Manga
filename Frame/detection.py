import os
import sys

project_root = os.path.abspath(os.path.join(os.getcwd(), ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

from transformers import AutoImageProcessor, Mask2FormerForUniversalSegmentation, Mask2FormerImageProcessor
from PIL import Image
import requests
import torch
import matplotlib.pyplot as plt
import numpy as np
import cv2

class PersonSegmenter:
    def __init__(self, checkpoint=None, device=None):
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        self.checkpoint = checkpoint or "qubvel-hf/finetune-instance-segmentation-ade20k-mini-mask2former"
        self.model = None
        self.processor = None

    def load(self):
        '''
        Loads model and processor into memory/device.
        '''
        if self.model is None:
            print(f"Loading model from {self.checkpoint}...")
            self.model = Mask2FormerForUniversalSegmentation.from_pretrained(
                self.checkpoint
            ).to(self.device)
            self.processor = Mask2FormerImageProcessor.from_pretrained(self.checkpoint)
            self.model.eval()
        return self

    def segment(self, image_path, min_area=700, min_score=0.7):
        """
        Segment people on an image

        Input:
            image_path (str): The file path to the image (should contain at least 1 human).
            min_area (int): Minimum pixel area for a mask to be kept.
            min_score (float): Minimum confidence score for a mask to be kept.

        Returns:
            tuple: A tuple containing:
                - image_np (np.ndarray): The original image as an RGB NumPy array.
                - instance_map (np.ndarray): A 2D NumPy array where each pixel value 
                  represents the instance ID of the segmented person.
                - person_masks (list[np.ndarray]): A list of binary masks (0 or 1), 
                  each representing a single person instance. same resolution to original image.
                - outputs (dict): The post-processed output dictionary.
        """

        if self.model is None:
            self.load()
            
        image = Image.open(image_path).convert("RGB")
        image_np = np.array(image)

        inputs = self.processor(images=[image], return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            
        outputs = self.processor.post_process_instance_segmentation(
            outputs, 
            target_sizes=[image_np.shape[:2]], 
            threshold=0.3, 
            mask_threshold=0.3
        )[0]

        instance_map = outputs["segmentation"].cpu().numpy()

        # Label ID for 'person'
        person_label_id = next((k for k, v in self.model.config.id2label.items() if v == "person"), None)
        
        person_masks = []
        if person_label_id is not None:
            for segment in outputs["segments_info"]:
                # Filter by label, score, and area
                if segment["label_id"] == person_label_id and segment["score"] > min_score:
                    # Create binary mask for this specific person instance
                    mask = (instance_map == segment["id"]).astype(np.uint8)
                    
                    area = np.sum(mask)
                    
                    # Area constraint
                    if area >= min_area:
                        person_masks.append(mask)
                    else:
                        print(f"Dropping instance {segment['id']} with area {area} (min_area={min_area})")
                elif segment["label_id"] == person_label_id:
                    print(f"Dropping instance {segment['id']} with low score {segment['score']:.2f}")

        return image_np, instance_map, person_masks, outputs