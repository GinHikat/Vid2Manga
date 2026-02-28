# Vid2Manga

Vid2Manga is an innovative application designed to bridge the gap between video content and manga-style storytelling. By leveraging advanced video processing and speech-to-text technologies, Vid2Manga extracts audio and visual components from video files to create a foundation for manga generation.

**Key Features:**

* **Video Processing**: Automatically separates video and audio tracks from uploaded files.
* **Speech-to-Text**: Utilizes OpenAI's Whisper model for high-accuracy transcription of dialogue.
* **Frame Stylization & Manga Generation**: Extracts video frames, applies stylization pipelines, and arranges them into manga layouts.
* **Modern Interactive UI**: A responsive React-based frontend for seamless user interaction.

---

## System Architecture & Main Capabilities

The system is built as a modern full-stack application:

### 1. Frontend (Client)

* **Framework**: React (Vite)
* **Key Libraries**: `axios` for API communication, `lucide-react` for UI icons, `react-router-dom` for navigation.
* **Capabilities**:
  * User-friendly video upload interface.
  * Real-time status tracking of processing tasks.
  * Playback of processed video and audio.
  * Display of transcribed text.

### 2. Backend (Server)

* **Framework**: FastAPI (Python)
* **Core Components**:
  * **API Layer**: RESTful endpoints for file upload (`/convert`) and status checking (`/status/{task_id}`).
  * **Task Manager**: In-memory state management for tracking background processes (Pending -> Processing -> Completed/Failed).
  * **Service Layer**: Orchestrates video splitting (via `ffmpeg`) and transcription.
* **Processing Engine**:
  * **FFmpeg**: Robust tool for splitting video containers into raw video streams and audio (WAV) files.
  * **OpenAI Whisper**: State-of-the-art model for transcribing audio to text with timestamp alignment.
  * **Image Processing**: OpenCV and PIL for extracting frames, applying stylization pipelines, and creating manga layouts.
  * **Web Crawling**: Selenium integrated for automated data gathering.

### 3. Directory Structure

```text
Vid2Manga/
├── .env
├── .env.example
├── .gitignore
├── App/                # Full-stack Web Application
│   ├── backend/        # FastAPI Server
│   └── frontend/       # React Application
├── Frame/              # Frame extraction and manga stylization pipelines
│   └── images/
├── README.md
├── Speech/             # Core Speech Processing Modules
│   ├── input/
│   └── output/
├── input/              # Raw uploaded files (server-side)
├── output/             # Processed assets (server-side)
│   ├── audio/
│   └── video/
└── requirements.txt
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
git clone https://github.com/GinHikat/Vid2Manga.git
cd Vid2Manga

pip install -r requirements.txt

cp .env.example .env
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

* **FFmpeg Requirement**: Ensure `ffmpeg` is accessible from your command line. The backend relies on it for media processing. If you encounter "FileNotFoundError" related to `ffmpeg`, check your PATH environment variable.
* **Model Performance**: The application uses the `base` model of Whisper by default. First-time execution may take longer as it downloads the model weights.
* **Configuration**: Check `App/backend/core/config.py` for path configurations.
* **Data Storage**:
  * Uploaded videos are stored in `input/`.
  * Processed video/audio/text are stored/served from `output/`.
