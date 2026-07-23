import React, { useState, useRef } from "react";
import axios from "axios";
import { API_BASE_URL } from "../config";

import { UploadCloud, FileVideo, Loader2, CheckCircle } from "lucide-react";
import "../css/VideoUpload.css";
import "../css/LanguageSelector.css";

const VideoUpload = ({
  onUploadStart,
  onUploadSuccess,
  onProgressUpdate,
  onError,
  isLoading,
  progressText,
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
      const response = await axios.post(
        `${API_BASE_URL}/convert`,
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
      console.error("Upload error:", err);
      const detail = err.response?.data?.detail || err.message || "Network / CORS connection error";
      onError(`Failed to upload video: ${detail}`);
    }
  };

  const pollTaskStatus = async (taskId, filename) => {
    let consecutiveErrors = 0;
    const interval = setInterval(async () => {
      try {
        const statusRes = await axios.get(
          `${API_BASE_URL}/status/${taskId}`,
        );
        const task = statusRes.data;
        consecutiveErrors = 0; // Reset error counter on successful response

        if (task.progress && onProgressUpdate) {
          onProgressUpdate(task.progress);
        }

        if (task.status === "completed") {
          clearInterval(interval);
          const result = task.result || {};

          const baseUrl = API_BASE_URL.replace(/\/api$/, "");
          const video = result.video_url
            ? (result.video_url.startsWith("http") ? result.video_url : `${baseUrl}${result.video_url}`)
            : "";
          const audio = result.audio_url
            ? (result.audio_url.startsWith("http") ? result.audio_url : `${baseUrl}${result.audio_url}`)
            : "";

          const pdf = result.pdf_url
            ? (result.pdf_url.startsWith("http") ? result.pdf_url : `${baseUrl}${result.pdf_url}`)
            : null;
          const mangaPages = (result.manga_urls || []).map((u) =>
            u.startsWith("http") ? u : `${baseUrl}${u}`
          );

          onUploadSuccess(video, audio, result.text, result.segments, pdf, mangaPages);
        } else if (task.status === "failed") {
          clearInterval(interval);
          onError(`Processing failed: ${task.error}`);
        }
      } catch (err) {
        consecutiveErrors += 1;
        console.warn(`Polling task status attempt ${consecutiveErrors} failed:`, err);
        if (consecutiveErrors >= 5) {
          clearInterval(interval);
          onError("Error checking task status after multiple retries.");
        }
      }
    }, 1500); // Poll every 1.5 seconds
  };

  const onButtonClick = () => {
    inputRef.current.click();
  };

  const handleLoadSample = async (sampleName = "sample_vid.mp4") => {
    try {
      const response = await fetch(`/samples/${sampleName}`);
      if (!response.ok) throw new Error("Sample file not found");
      const blob = await response.blob();
      const file = new File([blob], sampleName, { type: "video/mp4" });
      handleFiles(file);
    } catch (err) {
      console.error(err);
      onError("Failed to load sample video file.");
    }
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
              <p className="mono-subtext" style={{ color: "var(--accent-color)", fontWeight: "bold", marginTop: "0.5rem", fontSize: "0.9rem" }}>
                {progressText || "[1/5] Initializing speech & visual pipeline..."}
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
                  <div className="action-buttons" style={{ flexDirection: "column", gap: "0.5rem", width: "100%", maxWidth: "280px" }}>
                    <button className="upload-btn primary-btn" style={{ width: "100%" }} onClick={onButtonClick}>
                      Browse Files
                    </button>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", width: "100%" }}>
                      <button 
                        className="upload-btn secondary-btn" 
                        style={{ fontSize: "0.78rem", padding: "0.55rem 0.25rem", width: "100%", justifyContent: "center", textAlign: "center" }}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleLoadSample("sample_vid.mp4");
                        }}
                      >
                        Sample 1 (Long)
                      </button>
                      <button 
                        className="upload-btn secondary-btn" 
                        style={{ fontSize: "0.78rem", padding: "0.55rem 0.25rem", width: "100%", justifyContent: "center", textAlign: "center" }}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleLoadSample("vid1.mp4");
                        }}
                      >
                        Sample 2 (Short)
                      </button>
                    </div>
                  </div>
                  <p className="hint" style={{ marginTop: "0.5rem" }}>Supports MP4, MOV, AVI</p>
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
