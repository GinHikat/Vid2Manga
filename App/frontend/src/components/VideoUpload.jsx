import React, { useState, useRef } from "react";
import axios from "axios";
import { UploadCloud, FileVideo, Loader2, CheckCircle } from "lucide-react";
import "../css/VideoUpload.css";
import "../css/LanguageSelector.css";

const VideoUpload = ({
  onUploadStart,
  onUploadSuccess,
  onError,
  isLoading,
}) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [language, setLanguage] = useState("en");
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files[0]);
    }
  };

  const handleLanguageChange = (e) => {
    setLanguage(e.target.value);
  };

  const handleFiles = (file) => {
    if (!file.type.startsWith("video/")) {
      onError("Please upload a valid video file.");
      return;
    }
    setSelectedFile(file);
    onError(null); // Clear previous errors
  };

  const handleProcess = async () => {
    if (!selectedFile) return;

    onUploadStart();

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("language", language);

    try {
      // Assuming backend is running on localhost:8000
      const response = await axios.post(
        "http://localhost:8000/convert",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        },
      );

      if (response.data && response.data.task_id) {
        const taskId = response.data.task_id;
        pollTaskStatus(taskId, selectedFile.name);
      }
    } catch (err) {
      console.error(err);
      onError("Failed to upload and process video. Please try again.");
    }
  };

  const pollTaskStatus = async (taskId, filename) => {
    const interval = setInterval(async () => {
      try {
        const statusRes = await axios.get(
          `http://localhost:8000/status/${taskId}`,
        );
        const task = statusRes.data;

        if (task.status === "completed") {
          clearInterval(interval);
          const result = task.result;

          // Construct full URLs if backend returns relative paths
          const baseUrl = "http://localhost:8000";
          const video = result.video_url.startsWith("http")
            ? result.video_url
            : `${baseUrl}${result.video_url}`;
          const audio = result.audio_url.startsWith("http")
            ? result.audio_url
            : `${baseUrl}${result.audio_url}`;

          // Pass text result as well
          onUploadSuccess(video, audio, result.text);
        } else if (task.status === "failed") {
          clearInterval(interval);
          onError(`Processing failed: ${task.error}`);
        }
        // If pending or processing, continue polling
      } catch (err) {
        clearInterval(interval);
        console.error(err);
        onError("Error checking task status.");
      }
    }, 2000); // Poll every 2 seconds
  };

  const onButtonClick = () => {
    inputRef.current.click();
  };

  return (
    <div className="video-upload-container">
      <div
        className={`drop-zone ${dragActive ? "active" : ""} ${isLoading ? "loading" : ""}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          type="file"
          className="file-input"
          accept="video/*"
          onChange={handleChange}
          disabled={isLoading}
        />

        <div className="upload-content">
          {isLoading ? (
            <div className="loading-state">
              <Loader2 className="animate-spin icon-large" size={64} />
              <h3>Processing Video...</h3>
              <p>
                This process extracts audio and video frames for manga
                conversion.
              </p>
            </div>
          ) : (
            <>
              {selectedFile ? (
                <div className="selected-file-view">
                  <div className="icon-wrapper success">
                    <FileVideo className="icon-large" size={48} />
                  </div>
                  <h3>{selectedFile.name}</h3>
                  <p className="file-size">
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                  </p>

                  <div className="language-selector">
                    <label htmlFor="language-select">Spoken Language: </label>
                    <select
                      id="language-select"
                      value={language}
                      onChange={handleLanguageChange}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <option value="en">English (en)</option>
                      <option value="vi">Vietnamese (vi)</option>
                    </select>
                  </div>

                  <div className="action-buttons">
                    <button
                      className="upload-btn primary-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleProcess();
                      }}
                    >
                      Start Processing
                    </button>
                    <button
                      className="upload-btn secondary-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedFile(null);
                      }}
                    >
                      Change File
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="icon-wrapper">
                    <UploadCloud className="icon-large" size={64} />
                  </div>
                  <h3>Drag & Drop your video here</h3>
                  <p>or</p>
                  <button className="upload-btn" onClick={onButtonClick}>
                    Browse Files
                  </button>
                  <p className="hint">Supports MP4, MOV, AVI</p>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default VideoUpload;
