# Vid2Manga

Vid2Manga is an innovative application designed to bridge the gap between video content and manga-style storytelling. By leveraging advanced video processing, image stylization, AI segmentation, and layout generation, Vid2Manga extracts audio and visual components from videos and translates them into a cohesive manga reading experience.

**Key Features:**

* **Video Converter**: Automatically separates video and audio tracks from uploaded files, utilizing OpenAI's Whisper model for high-accuracy transcription of dialogue.
* **Manga Frame Generator**: Upload multiple images, choose stylization pipelines (Classic B&W, Anime Cel-shaded, or Soft Comic), and generate proportional, multi-page manga layouts dynamically.
* **AI Human Segmentation**: Apply Mask2Former instance segmentation to detect and highlight characters with high-visibility red masks on your manga panels.
* **Modern Interactive UI**: A responsive, premium React-based frontend for seamless user interactions and fast asset generation.

---

## System Architecture & Main Capabilities

The system is built as a modern full-stack application:

### 1. Technology Stack

| Technology               | Category                          |
| ------------------------ | --------------------------------- |
| **React (Vite)**   | Frontend                          |
| **FastAPI**        | Backend                           |
| **OpenCV & PIL**   | Image Processing                  |
| **Mask2Former**    | Human Segmentation                |
| **OpenAI Whisper** | Audio Processing / Speech-to-Text |
| **FFmpeg**         | Media Processing                  |

### 2. Directory Structure

```text
Vid2Manga/
├── App/                # Full-stack Web Application
│   ├── backend/        # FastAPI Server, API endpoints, Task Managers, Services
│   └── frontend/       # React Application (Pages: Home, ConverterPage, MangaGenerator)
├── Frame/              # Core Image Algorithms
│   ├── detection.py    # Human instance segmentation
│   ├── frame_processor.py # OpenCV aesthetic pipelines (B&W, Cel-shaded)
│   └── manga_layout.py # Smart, proportional layout rendering
├── Speech/             # Audio Split & Whisper STT
├── input/              # Raw uploaded files (server-side)
├── output/             # Processed assets (video clips, audios, manga pages)
├── .env
├── requirements.txt
└── README.md
```

---

## Setup & Installation

Follow these steps to set up the project locally.

### Prerequisites

* **Python 3.10+**
* **Node.js & npm**
* **FFmpeg**: Must be installed and added to your system PATH.

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Vid2Manga

pip install -r requirements.txt
```

### 2. Backend Setup

```bash
cd App/backend

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

*The API will be available at `http://localhost:8000`*

### 3. Frontend Setup

```bash
cd App/frontend

npm install

# Start the development server
npm run dev
```

*The UI will be available at `http://localhost:5173` (default Vite port)*

---

## Running Tests

The backend includes a comprehensive test suite (Unit, Ablation, and System tests).

**Using the Helper Script (Windows PowerShell):**

```powershell
cd App/backend
.\run_tests.ps1
```

**Using Pytest directly:**

```bash
cd App/backend
# Run all tests
pytest

# Run specific categories
pytest tests/unit       # Unit tests
pytest tests/ablation   # Component isolation tests
pytest tests/system     # End-to-end flow tests
```

---

## Other Notes

* **FFmpeg Requirement**: Ensure `ffmpeg` is accessible from your command line.
* **AI Models**: The first time you use Transcription or Segmentation, it will download the respective weights (OpenAI Whisper or Mask2Former) which might take a bit of time depending on your connection.
* **Storage**: Uploaded media resides in `input/` and final artifacts are in `output/`.
