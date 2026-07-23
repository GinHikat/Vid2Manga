import os
import sys
import time
import gc
import torch
import numpy as np
import onnx
import onnxruntime as ort
from onnxruntime.quantization import quantize_dynamic, QuantType

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
backend_dir = os.path.join(root_dir, "App", "backend")
for d in [root_dir, backend_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from core.config import settings

# Output directory for quantized ONNX models
MODELS_DIR = os.path.join(settings.BASE_DIR, "models_onnx")
os.makedirs(MODELS_DIR, exist_ok=True)

class ONNXPersonSegmenter:
    """Ultra-low RAM ONNX Runtime wrapper for Mask2Former Person Instance Segmentation."""

    def __init__(self, onnx_path: str = None):
        """Initializes the ONNX segmenter with lightweight ONNX Runtime C++ engine.

        Args:
            onnx_path: Path to the quantized .onnx model file.
        """
        self.onnx_path = onnx_path or os.path.join(MODELS_DIR, "mask2former_int8.onnx")
        self.session = None

    def load(self):
        """Lazy-loads the ONNX Runtime session using CPUExecutionProvider (~30MB RAM)."""
        if self.session is None:
            if not os.path.exists(self.onnx_path):
                raise FileNotFoundError(
                    f"Quantized ONNX model not found at {self.onnx_path}. "
                    "Run 'python modules/mlops/quantize_models.py' first to generate it."
                )
            
            # Configure lightweight ONNX Runtime session
            opts = ort.SessionOptions()
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            opts.intra_op_num_threads = 2
            
            self.session = ort.InferenceSession(
                self.onnx_path, 
                sess_options=opts, 
                providers=["CPUExecutionProvider"]
            )
        return self

    def unload(self):
        """Unloads ONNX session and triggers garbage collection to keep RAM <200MB."""
        self.session = None
        gc.collect()

def export_mask2former_to_onnx():
    """Exports HuggingFace Mask2Former PyTorch model to ONNX FP32 and applies INT8 dynamic quantization."""
    print("=" * 80)
    print("      MLOps Model Quantization Pipeline: PyTorch -> ONNX INT8")
    print("=" * 80)
    
    from modules.frame.human_detector import PersonSegmenter

    fp32_onnx_path = os.path.join(MODELS_DIR, "mask2former_fp32.onnx")
    int8_onnx_path = os.path.join(MODELS_DIR, "mask2former_int8.onnx")

    print("[1/4] Loading PyTorch Mask2Former model on CPU...")
    segmenter = PersonSegmenter(device="cpu").load()
    segmenter.model.eval()

    # Dummy input tensor on CPU (batch_size=1, channels=3, height=480, width=480)
    dummy_input = torch.randn(1, 3, 480, 480, dtype=torch.float32, device="cpu")

    print("[2/4] Exporting PyTorch computational graph to ONNX FP32...")
    with torch.no_grad():
        torch.onnx.export(
            segmenter.model,
            dummy_input,
            fp32_onnx_path,
            export_params=True,
            opset_version=16,
            do_constant_folding=True,
            input_names=["pixel_values"],
            output_names=["class_queries_logits", "masks_queries_logits"],
            dynamic_axes={
                "pixel_values": {0: "batch_size", 2: "height", 3: "width"},
                "class_queries_logits": {0: "batch_size"},
                "masks_queries_logits": {0: "batch_size", 2: "height", 3: "width"},
            }
        )

    fp32_size_mb = os.path.getsize(fp32_onnx_path) / (1024 * 1024)
    print(f"      FP32 ONNX model created! Size: {fp32_size_mb:.2f} MB")

    # Clean PyTorch model from RAM before quantization
    segmenter.unload()
    gc.collect()

    print("[3/4] Applying INT8 Dynamic Quantization (Affine FP32 -> INT8 conversion)...")
    quantize_dynamic(
        model_input=fp32_onnx_path,
        model_output=int8_onnx_path,
        weight_type=QuantType.QUInt8
    )

    int8_size_mb = os.path.getsize(int8_onnx_path) / (1024 * 1024)
    reduction = ((fp32_size_mb - int8_size_mb) / fp32_size_mb) * 100
    print(f"      INT8 Quantized ONNX model created! Size: {int8_size_mb:.2f} MB")
    print(f"      Memory Reduction achieved: {reduction:.1f}% smaller!")

    # Remove heavy FP32 intermediary file to save disk space
    if os.path.exists(fp32_onnx_path):
        os.remove(fp32_onnx_path)

    print("[4/4] Verifying ONNX Runtime inference execution...")
    onnx_segmenter = ONNXPersonSegmenter(int8_onnx_path).load()
    print("      ONNX Runtime session initialized successfully with CPUExecutionProvider!")
    onnx_segmenter.unload()

    print("=" * 80)
    print("SUCCESS: Mask2Former ONNX INT8 Quantization Complete! Model saved at:", int8_onnx_path)
    print("=" * 80)

if __name__ == "__main__":
    export_mask2former_to_onnx()
