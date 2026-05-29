# ==========================================
# Warnings & Logging Suppression
# ==========================================
import os
import logging
import warnings

# Suppress python future and user warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Disable verbose third party libraries logging
logging.getLogger("megatron").setLevel(logging.ERROR)
logging.getLogger("nemo").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)

from .process_audio import split_video_audio, speech2text
from .gcp_speech import transcribe_gcp

