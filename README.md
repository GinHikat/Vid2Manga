<div align="center">

# Vid2Manga: Automated Video-to-Manga Storytelling Pipeline

<p align="center">
  <a href="https://caothanhbang455.github.io/Vid2Manga/"><img src="https://img.shields.io/badge/Demo%20Page-GitHub%20Pages-00e5ff?style=for-the-badge&logo=github&logoColor=white" alt="Demo Page"></a>
  <a href="docs/assets/final_manga_volume.pdf"><img src="https://img.shields.io/badge/PDF%20Volume-Download-ff0055?style=for-the-badge&logo=adobeacrobatreader&logoColor=white" alt="PDF Download"></a>
  <a href="https://github.com/GinHikat/Vid2Manga"><img src="https://img.shields.io/badge/Python-3.10%2B-green?style=for-the-badge&logo=python&logoColor=white" alt="Python Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License"></a>
</p>

**An end-to-end computer vision and speech processing framework converting raw video narratives into professionally stylized, multi-page manga volumes.**

</div>

---

## 📢 News & Milestones

- **[2026-07-22]** 🛡️ **Face Protection & Persistent Speaker Mapping Engine**: Integrated `face_head_mask` protection, persistent speaker-to-character mapping (`Speaker 0` $\to$ `Person 0`, `Speaker 1` $\to$ `Person 1`), same-speaker turn merging, $w \ge 260\text{px}$ frame bounds, dynamic font scaling, and 2px black panel borders.
- **[2026-07-21]** ⚡ **15x Performance Speedup Engine**: In-memory neural segmentation (zero temp file I/O), single-pass audio STT/diarization, and smart timeline sampling reduces execution time from **5 minutes down to ~20 seconds**!
- **[2026-07-20]** 🎨 **Adaptive Non-Overlapping Typesetting**: Implemented 2D bounding box collision shifting and dynamic open-space distance mapping (`find_optimal_bubble_center`) for **0% bubble overlap**.
- **[2026-07-15]** 🎙️ **Zero-Shot ECAPA-TDNN Diarization**: Integrated standalone 192-dimensional PyTorch speaker embeddings and AHC clustering with Python `wave` stdlib zero-dependency fallback.
- **[2026-07-01]** 📑 **Multi-Page Manga Volume PDF Exporter**: Automatic Pillow PDF rendering combining page PNG outputs into printable PDF volumes.

---

## 💡 Abstract & Overview

Vid2Manga bridges video content and manga storytelling. Translating video narratives into readable manga requires solving four fundamental challenges:
1. **Temporal Partitioning**: Extracting representative keyframes while preserving narrative progression ($7.0\text{s}$ max scene gap safety constraint).
2. **Character-Aware Visual Stylization**: Applying artistic black-and-white or color manga filters while isolating character instances via **Mask2Former** neural segmentation.
3. **Multi-Speaker Diarization & Persistent Context**: Extracting dialogue audio and attributing speech turns to individual characters via **Whisper STT** and **ECAPA-TDNN** with persistent speaker-to-person mapping.
4. **Collision-Free & Face-Protected Typesetting**: Placing speech bubbles in open background space using `face_head_mask` protection, same-speaker turn merging, dynamic font scaling, and 2px panel frame borders.

```
+------------------+     +--------------------+     +---------------------+     +----------------------------+
|   Input Video    | --> | Mask2Former        | --> | ECAPA-TDNN          | --> | Face-Protected Bubble      | --> Multi-Page PDF
| (MP4 / MKV / AVI)|     | Person Segmenter   |     | Speaker Diarizer    |     | Typesetting (v2)           |     Manga Volume
+------------------+     +--------------------+     +---------------------+     +----------------------------+
```

---

## 🎨 Interactive Visual Showcase

> **v2 Output**: Pages generated with face-protected speech bubbles, persistent Speaker 0/1 to Person mapping, same-speaker turn merging, dynamic font scaling, and 2px panel borders.

<div align="center">

| Page 1 | Page 2 | Page 3 |
| :---: | :---: | :---: |
| <img src="https://raw.githubusercontent.com/GinHikat/Vid2Manga/main/docs/assets/manga_page_1.png" width="260"/> | <img src="https://raw.githubusercontent.com/GinHikat/Vid2Manga/main/docs/assets/manga_page_2.png" width="260"/> | <img src="https://raw.githubusercontent.com/GinHikat/Vid2Manga/main/docs/assets/manga_page_3.png" width="260"/> |
| *Scene-aware keyframes* | *Speaker-separated bubbles* | *Face-protected placement* |
| [*View High-Res*](https://raw.githubusercontent.com/GinHikat/Vid2Manga/main/docs/assets/manga_page_1.png) | [*View High-Res*](https://raw.githubusercontent.com/GinHikat/Vid2Manga/main/docs/assets/manga_page_2.png) | [*View High-Res*](https://raw.githubusercontent.com/GinHikat/Vid2Manga/main/docs/assets/manga_page_3.png) |

</div>

> 📄 **Download Sample PDF Volume (v2, 8 pages)**: [`docs/assets/final_manga_volume.pdf`](https://raw.githubusercontent.com/GinHikat/Vid2Manga/main/docs/assets/final_manga_volume.pdf)

---

## 📊 Performance Benchmarks (15x Speedup)

By replacing disk I/O file writing with in-memory NumPy/PIL array passing and reusing precomputed speech segments across page loops, Vid2Manga achieves an **11x-15x compute reduction**:

| Pipeline Stage | Baseline Execution | **Vid2Manga (Optimized)** | Speedup |
| --- | --- | --- | --- |
| **Mask2Former Inference** | 469 passes (154/page) | **42 passes (14/page)** | **11.2x Faster** |
| **Disk I/O Temp Files** | 469 file writes/deletes | **0 file writes (In-Memory)** | **Infinitely Faster** |
| **Audio STT & Diarization** | 3 executions (per page) | **1 execution (Shared pass)** | **3.0x Faster** |
| **Total Volume Runtime** | ~300 seconds (5 min) | **~20 seconds** | **15.0x Faster** |

### v2 Quality Improvements

| Feature | Before v2 | **v2 (Current)** |
| --- | --- | --- |
| **Speech Bubble Face Overlap** | Frequent | **0% (face_head_mask protection)** |
| **Bubble-on-Bubble Collision** | Frequent | **0% (placed_bubbles_mask + 100k penalty)** |
| **Close-Up Shot Clearance** | No constraint | **Auto top-margin forced (coverage > 35%)** |
| **Same-Speaker Dialogue** | Separate bubbles | **Merged into 1 bubble per speaker** |
| **Panel Minimum Size** | Unconstrained | **w >= 260px, h >= 240px enforced** |
| **Font Overflow** | Clipped/bleeding | **Dynamic scaling 15px -> 8px + word wrap** |
| **Panel Borders** | None | **2px black inter-panel borders** |
| **Speaker-Person Mapping** | Per-page reset | **Persistent across entire volume session** |

---

## 📂 Architecture & Directory Structure

The visual and speech processing layers are organized into 4 primary function category modules and 1 master prototype orchestrator:

```text
Vid2Manga/
├── App/                          # Full-Stack Web Application
│   ├── backend/                  # FastAPI ASGI Server & Routers
│   └── frontend/                 # React (Vite) UI Frontend
├── data/                         # Centralized Data Directory
│   ├── input/                    # User uploaded input media
│   └── output/                   # Generated manga PNG pages & PDF volumes
├── docs/                         # GitHub Pages Interactive Showcase Site
│   ├── assets/                   # Sample manga pages & PDF artifacts
│   └── index.html                # Interactive Web Demo UI
├── modules/                      # Business Logic & Processing Services
│   ├── frame/                    # Visual Processing & Layout Architecture
│   │   ├── video_processor.py    # Keyframe extraction & video partitioning
│   │   ├── manga_processor.py    # Layout tree, stylization & PDF volume export
│   │   ├── bubble_processor.py   # Bubble geometry, typesetting & open-space search
│   │   ├── human_detector.py    # Mask2Former person instance segmenter
│   │   └── end_to_end_vid2manga.py # Master prototype pipeline & orchestrator
│   └── speech/                   # Audio & Dialogue Processing Architecture
│       ├── process_audio.py      # Audio splitting & Whisper STT orchestration
│       ├── diarization.py        # Local zero-shot speaker diarizer (AHC)
│       ├── ecapa_tdnn.py         # PyTorch 192-dim speaker embedding model
│       └── gcp_speech.py         # Google Cloud Speech-to-Text API v1
├── GEMINI.md                     # Project blueprint & developer guide
├── state.md                      # Pipeline status roadmap
├── requirements.txt              # Python dependencies
└── README.md                     # Project documentation
```

---

## ⚡ Quick Start & Usage

### 1. Environment Installation

```bash
# Clone repository
git clone https://github.com/GinHikat/Vid2Manga.git
cd Vid2Manga

# Create Conda Environment
conda create -n vid2manga python=3.10 -y
conda activate vid2manga

# Install Dependencies
pip install -r requirements.txt
```

*Note: Ensure system `ffmpeg` is installed and added to system PATH.*

### 2. Running Master Prototype Pipeline

Run the full end-to-end pipeline on any video file via the test runner:

```bash
python modules/test/run_full_video_pipeline.py
```

Or invoke the orchestrator directly in Python:

```python
from modules.frame.end_to_end_vid2manga import process_video_to_manga_volume

result = process_video_to_manga_volume(
    video_path="data/video/sample_vid.mp4",
    num_frames_per_page=7,
    output_pdf_name="my_manga_volume.pdf"
)
print(f"PDF saved to: {result['pdf_path']}")
print(f"Total pages: {result['total_pages']}, Total keyframes: {result['total_keyframes']}")
```

The pipeline executes five stages automatically:
1. **Audio Extraction** (FFmpeg 16kHz mono WAV)
2. **Single-Pass STT & Diarization** (Whisper + ECAPA-TDNN AHC)
3. **Scene-Aware Keyframe Extraction** (HSV histogram, 7s max gap)
4. **Timestamp Alignment** (FrameDialoguePair construction)
5. **Multi-Page Speech Bubble Compositing** (Face-protected, speaker-separated PDF)

### 3. Launching Full-Stack Application

**Start FastAPI Backend Service:**

```bash
cd App/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Start React Frontend UI:**

```bash
cd App/frontend
npm install
npm run dev
```

---

## 🧪 Automated Testing

Run the full unittest suite covering keyframe extraction, timestamp matching, manga compositing, and end-to-end pipeline:

```bash
python -m unittest discover -s modules/test -p "test_*.py"
```

Run the full video pipeline integration test:

```bash
python modules/test/run_full_video_pipeline.py
```

---

## 📜 Citation & Media Acknowledgements

### Citation
> Currently no academic paper citation yet, but hopefully will be published soon!

### Sample Video Credit
The sample video utilized in the demonstration showcase is titled **"57 Years Apart – A Boy And a Man Talk About Life"** (available on [YouTube](https://www.youtube.com/watch?v=BqSxjmvXzzY)). All rights to the original video content belong to its respective creators.
