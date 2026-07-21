# Vid2Manga: Project Blueprint

## Project Introduction

Vid2Manga is an automated pipeline designed to transform video content into professionally styled manga pages. The system integrates advanced computer vision for frame selection and stylization with speech-to-text processing for dialogue extraction and speaker diarization.

## Final Purpose

To provide a seamless, end-to-end tool that converts various video formats (including web content from platforms like YouTube) into readable manga layouts, retaining the narrative flow through synchronized speech breakdown and character-aware visual processing.

---

## Technical Stack

- **Backend**: FastAPI (Python 3.12+)
- **Frontend**: React + Vite (Dark Mode UI)
- **Computer Vision**: OpenCV, Pillow, Mask2Former (Transformers)
- **Speech**: OpenAI Whisper, GCP Speech-to-Text (Diarization)
- **Audio/Video**: FFmpeg

---

## Tasks Breakdown

*This section provides a high-level roadmap of development priorities (to be updated manually).*

### Phase 1: Core Infrastructure

- [X] Backend modularization and service relocation.
- [X] Application path unification (`settings.INPUT_DIR`).
- [X] Basic Speech-to-Text pipeline (local + GCP).

### Phase 2: Visual & Artistic Processing

- [ ] Refine stylization filters (A/B/C).
- [ ] Improve character-aware layout segmentation.
- [ ] Optimize manga page composition performance.

### Phase 3: Speech & Interaction

- [X] Implement speaker diarization interface.
- [X] Integrate local diarization model (**pyannote-audio v3.1**).
- [X] Implement standalone offline zero-shot diarization (**ECAPA-TDNN**).
- [ ] Interactive timeline/audio playback sync.

---

## Future Assessment Requirements

*These requirements MUST be ensured at the start of any future assessment or coding session.*

1. **Environment Activation**: Always verify and activate the correct environment (e.g., `conda activate only_env`) before running tests or performing inference, as it contains heavy dependencies like `torch` and `pyannote-audio`.
2. **Mocking Policy**: When writing or updating tests, always mock heavy ML models (Whisper, Mask2Former, Pyannote) to ensure fast and deterministic CI/CD cycles.
3. **Path Consistency**: Ensure all new modules use `settings.INPUT_DIR` and `settings.OUTPUT_DIR` to maintain Windows/Linux cross-compatibility.
4. **Documentation Sync**: Update `GEMINI.md` after any change to function signatures or project structure.
5. **Sanitization**: Stictly enforce "No Emojis" and "No Special Characters" in all code and commits.
6. **Orientation**: Before you execute something, read this `GEMINI.md` file first to get a grasp of what is in the codebase and what has been done so far.
7. **Log Unification**: After each 5 new changes, concat the logs into 1 unified one with consistent information flow.

---

## Project Structure

### 1. Root Configuration

- `GEMINI.md`: (This file) Project overview and developer guide.
- `state.md`: Pipeline status breakdown and active development roadmap.
- `README.md`: High-level summary and usage instructions.
- `main.py`: Root-level deployment entry point mapping uvicorn ASGI requests to the App service layer.
- `.env`: Environment variables (API keys, model toggles).
- `.gitignore`: Workspace-aware patterns for inputs, outputs, and local models.

### 2. Core Modules (`/modules`)

This directory contains the heavy-lifting logic, decoupled from the API layer.

#### `/modules/frame` (Visual Processing)

#### `/modules/frame` (Visual & Manga Processing Architecture)

The visual processing layer is organized into 4 primary function category modules and 1 master prototype pipeline:

- **`video_processor.py` (Video Ingestion & Partitioning Category)**:
  - `extract_keyframes(video_path: str, interval_sec: float = 5.0, ...)`: Extracts frame images at fixed intervals.
  - `split_vid(video_path: str, partition_length: float = 20.0, ...)`: Splits video into duration-based segment files.
  - `process_video(file: UploadFile)`: Main entry point for synchronous video uploads.
  - `process_video_task(task_id: str, ...)`: Asynchronous background worker for audio extraction and segmentation.
- **`manga_processor.py` (Layout, Stylization & Page Compositing Category)**:
  - `stylize_a`, `stylize_b`, `stylize_c`: Implementation of classic B&W manga, anime color, and edge-preserving comic artistic filters.
  - `frame_clear(image_path: str, ...)`: Quality validation for image sharpness and brightness.
  - `generate_manga_layout(width, height, num_frames, ...)`: Recursive Binary Splitting Tree algorithm for panel layout generation.
  - `create_manga_page(images, frames, ...)`: Composites processed images into panels using Pillow LANCZOS resampling.
  - `save_manga_pages_to_pdf(page_images, output_pdf_path)`: Combines PIL page images or file paths into a multi-page PDF volume.
  - `process_manga_generation(...)`: High-level master endpoint for image-list to manga PNG URL conversion.
- **`bubble_processor.py` (Speech Bubble Typesetting & Alignment Category)**:
  - `Bubble`: Class wrapper for bubble mask extraction, morphology tail segmentation, polygon approximation, and text typesetting.
  - `find_optimal_bubble_center(total_person_mask, bubble_w, bubble_h, ...)`: Distance-transform open space calculation prioritizing maximum clearance from character masks.
- **`human_detector.py` (Neural Instance Segmentation Category)**:
  - `PersonSegmenter`: Wrapper for loading and running **Mask2Former** (`qubvel-hf/finetune-instance-segmentation-ade20k-mini-mask2former`) supporting in-memory array segmentation.
- **`end_to_end_vid2manga.py` (Master Prototype Pipeline & Orchestrator)**:
  - `generate_video_manga_page(video, num_frames=7, time_range=None, ...)`: Converts a video file/path section into a stylized manga page.
  - `generate_full_video_manga_volume(video, num_pages=3, num_frames_per_page=7, output_pdf_name=..., page_width=1000, page_height=1400)`: Master prototype function converting a video into a multi-page manga PDF volume.

#### `/modules/speech` (Audio Processing)

- **`process_audio.py`**:
  - `split_video_audio(input_file: str)`: Uses **FFmpeg** to extract mono 16kHz audio (WAV) and a soundless video (MP4) from a source file.
  - `_transcribe_whisper(audio_path: str, ...)`: Performs local transcription using the **OpenAI Whisper "base"** model, now features local speaker diarization fallback.
  - `_assign_speakers(...)`: Helper to merge diarization segments with transcription data based on temporal overlap.
  - `speech2text(audio_file: str, ...)`: High-level orchestration that selects the correct engine (GCP with Whisper fallback) based on environment configuration.
- **`ecapa_tdnn.py`**:
  - `PretrainedECAPATDNN`: Standalone PyTorch wrapper that lazy-loads and extracts 192-dimensional normalized speaker embeddings using official checkpoints.
- **`diarization.py`**:
  - `LocalDiarizer`: Zero-shot offline speaker diarizer using pre-trained ECAPA-TDNN and Agglomerative Hierarchical Clustering (AHC) with dynamic speaker count estimation.
- **`gcp_speech.py`**:
  - `resolve_credentials_path()`: Dynamically resolves the absolute path to Google Cloud service account JSON keys.
  - `transcribe_gcp(audio_path: str, ...)`: High-precision transcription service using the **Google Cloud Speech-to-Text API v1**, featuring full **Speaker Diarization** (clustering logic) and word-level timestamps.

#### `/modules` (Base)

- **`task_manager.py`**:
  - `Task`, `TaskStatus`, `Result`: Definitions for background job state management.

---

### 3. Application Components (`/App`)

#### `/App/backend` (Service Layer)

- **`main.py`**: FastAPI app setup, CORS configuration, and `/output` static mounting.
- **`api/v1/api.py`**:
  - `@router.post("/api/convert")`: Video upload endpoint.
  - `@router.get("/api/status/{id}")`: Task polling endpoint.
  - `@router.post("/api/manga-layout")`: Direct image-to-manga endpoint.
- **`core/config.py`**: Central `Settings` class for path resolution (`BASE_DIR`, `INPUT_DIR`, `OUTPUT_DIR`).
- **`schemas/video.py`**: Pydantic models for API responses (`VideoResponse`, `SpeechSegment`).

#### `/App/frontend` (User Interface)

- **`src/components/VideoUpload.jsx`**: Logic for file selection, language choosing, and task polling.
- **`src/config.js`**: Dynamic API configuration supporting `VITE_API_BASE_URL`.
- **`src/components/ResultDisplay.jsx`**: Visualizer for result media and the **Speech Breakdown** interface.
- **`src/css/TextResult.css`**: Styling for the interactive timeline and hover states.

---

## File Connections & Import Flow

```mermaid
graph TD
    api[api.py] --> video_proc[video_processor.py]
    api --> manga_proc[manga_processor.py]
    video_proc --> speech_proc[process_audio.py]
    speech_proc --> gcp[gcp_speech.py]
    manga_proc --> stylizer[stylizer.py]
    manga_proc --> human_det[human_detector.py]
    manga_proc --> layout[layout_generator.py]
    video_proc --> task_mgr[task_manager.py]
  
    subgraph Modules Path Injection
    init[__init__.py] -- adds --> backend[App/backend]
    end
```

## Mandatory Coding Standards

### 1. Code Hygiene & Comments

- **Clean First**: Always clean the code before making changes.
- **Sectional Comments**: Use only sectional comments to divide logic blocks.
- **No Ordering**: Do not use numbered (`1.`, `2.`) or lettered (`a)`, `b)`) lists in comments.
- **Line Comments**: Only use line comments if a specific line is exceptionally complex or non-obvious.

### 2. Documentation (Docstrings)

- **Mandatory for All Functions**: Every function MUST have a Google-style or similar docstring.
- **Overall Purpose**: A brief description of what the function does.
- **Input Params**: `param_name: dtype` - Description of the parameter.
- **Output**: `dtype` - Description of the return value.

### 3. Text & Output Sanitization

- **No Emojis**: Never use emojis in code, console logs, print statements, or comments.
- **No Special Characters**: Avoid unusual Unicode characters in technical logs or comments.

### 4. Maintenance

- **Update GEMINI.md**: This file MUST be updated immediately after any code refinement that changes functionality, structure, or function signatures.

---

## Key Developer Notes

- **Paths**: Always use `settings.INPUT_DIR` or `settings.OUTPUT_DIR` to ensure Windows compatibility and workspace consistency.
- **API Configuration**: The frontend uses `import.meta.env.VITE_API_BASE_URL` with a fallback to `http://localhost:8000/api`. The backend router is prefixed with `/api` in `main.py`.
- **Background Tasks**: All media processing happens asynchronously via `BackgroundTasks` in FastAPI. Check current status via `/api/status/{id}`.
- **Speech Breakdown**: The UI expects `segments` in the result object, which include `speaker` name and `text` content. Whisper results currently default to 'Unknown Speaker'.

---

## Development Log

- **Centralized Data Path Routing: 2026-07-21**
  - Updated `Settings` in `App/backend/core/config.py` to route `settings.INPUT_DIR` to `data/input` and `settings.OUTPUT_DIR` to `data/output` under project root `data/`.
  - Prevented writing backend inputs and outputs inside `App/backend/`.

- **State & Architecture Alignment Assessment: 2026-07-21**
  - Evaluated current repository status against master pipeline architecture (`vid2manga_pipeline.png`).
  - Created `state.md` documenting implemented components, functional gaps, and a 4-phase action plan for full video-to-manga automation.

- **GMM-UBM & D-Vector Implementation: 2026-06-01**
  - Implemented the classical GMM-UBM model (Expectation-Maximization training and MAP mean adaptation) from scratch in NumPy for deep learning baseline studies.
  - Implemented the original Google D-Vector framework (dense deep neural network, context stacking, and temporal average pooling) in PyTorch.
  - Developed a standalone evaluation pipeline (`diarization_evolution.py`) to execute, visualize, and trial both frameworks.
  - Created a robust companion markdown study guide (`diarization_evolution.md`) describing speaker verification evolution from frame-level DNNs to x-vectors and ECAPA-TDNNs.

- **Render Native Environment Fallbacks: 2026-05-30**
  - Resolved Render native Python environment port binding timeouts by introducing robust, self-healing try-except fallback layers across all modular speech operations.
  - Implemented safe Soundfile import blocks to bypass system libsndfile dependency crashes.
  - Designed a pure-Python silent WAV builder to avoid ffmpeg system command exceptions.
  - Added scikit-learn to both root-level and nested backend requirements files for Agglomerative Hierarchical Speaker Clustering support.

- **Render Port Binding Support: 2026-05-30**
  - Created a root-level main.py ASGI router to bridge uvicorn calls from Render to the backend App directory structure.

- **Premium Visual Redesign: 2026-05-30**
  - Refactored global App CSS with unified Ink and Crimson screentone variables, responsive workbench grids, and tactile button animations.
  - Redesigned Home page into an asymmetric split panel layout utilizing a custom LCP value proposition and a grid-wide bento showcase.
  - Upgraded Video Converter to a 50/50 split Workbench layout with dynamic loading status logs and detailed extraction progress states.
  - Stylized Manga Generator dashboard and canvas rendering viewport with high-contrast borders and character-aware parameter fields.

- **Zero-Shot Speaker Diarization: 2026-05-27**
  - Designed and built a standalone, pure PyTorch ECAPA-TDNN model (`ecapa_tdnn.py`) with SpeechBrain checkpoint state-dict dynamic mapping.
  - Implemented offline zero-shot speaker diarization in `diarization.py` using AHC clustering, dynamic VAD, and dynamic speaker estimation.
  - Removed dependencies on pyannote-audio and speechbrain for seamless local execution on Windows/Linux.
  - Resolved Windows platform audio saving constraints by integrating the standard soundfile library.

- **Visuals & Logic Update: 2026-04-15**
  - Resolved "out of the black box" layout issue in Manga Generator UI by implementing `minmax(0, ...)` grid constraints and `width: fit-content` background cards.
  - Implemented `calculate_relative_angle` in `bubble_processor.py` for dynamic character-aware bubble tail orientation.
  - Optimized viewport scaling for generated manga pages using `max-height` constraints for improved readability.

### Previous Status: 2026-04-14 (Unified Update)
- Successfully decoupled core logic into the root-level `modules/` directory.
- Centralized path resolution using `settings.INPUT_DIR` and `settings.OUTPUT_DIR`.
- Integrated local speaker diarization using `pyannote/speaker-diarization-3.1`.
- Upgraded "Speech Breakdown" UI with interactive timestamp jumps and speaker awareness.
- Resolved `ffmpeg` encoding issues on Windows and improved `bubble_processor.py` robustness.
