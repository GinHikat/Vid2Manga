FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV PYTHONPATH="/workspace:/workspace/App/backend"

# Install system dependencies (FFmpeg, OpenCV libGL, libsndfile, git, build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libgl1 \
    libglib2.0-0 \
    git \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy and install python dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy codebase
COPY . .

# Pre-bake quantized ONNX INT8 models during container build
RUN python modules/mlops/quantize_models.py

# Create input and output data directories
RUN mkdir -p data/input data/output

EXPOSE 8000
CMD ["sh", "-c", "celery -A modules.mlops.celery_app worker --loglevel=info --pool=solo & uvicorn App.backend.main:app --host 0.0.0.0 --port $PORT"]
