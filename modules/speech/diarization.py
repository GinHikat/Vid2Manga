import os
import torch
from pyannote.audio import Pipeline
from typing import List, Dict, Any

class LocalDiarizer:
    """Handles local speaker diarization using pyannote.audio."""

    def __init__(self):
        """Initializes the diarization pipeline with local or HF model."""
        self.pipeline = None
        self.hf_token = os.getenv("HF_TOKEN")

    def load(self):
        """Lazy-loads the pyannote diarization pipeline."""
        if self.pipeline is None:
            if not self.hf_token:
                print("Warning: HF_TOKEN not found in environment. Local diarization might fail.")
            
            try:
                self.pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=self.hf_token
                )
                # Move to GPU if available
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                self.pipeline.to(device)
            except Exception as e:
                print(f"Failed to load local diarization pipeline: {e}")
                raise

    def diarize(self, audio_path: str) -> List[Dict[str, Any]]:
        """Performs diarization on an audio file.

        Args:
            audio_path: Absolute path to the WAV audio file.

        Returns:
            A list of segments with 'speaker', 'start', and 'end' keys.
        """
        self.load()
        if self.pipeline is None:
            return []

        diarization = self.pipeline(audio_path)
        
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                "speaker": f"Speaker {speaker}",
                "start": turn.start,
                "end": turn.end
            })
        
        return segments

# Singleton instance
diarizer = LocalDiarizer()
