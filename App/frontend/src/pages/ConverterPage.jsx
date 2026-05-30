import React, { useState } from "react";
import VideoUpload from "../components/VideoUpload";
import ResultDisplay from "../components/ResultDisplay";
import "../css/App.css";
import "../css/Nav.css";

import { Video, Home as HomeIcon, Columns, Sparkles, AlertCircle } from "lucide-react";
import { Link } from "react-router-dom";

function ConverterPage() {
  const [videoUrl, setVideoUrl] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [text, setText] = useState(null);
  const [segments, setSegments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleUploadSuccess = (video, audio, extractedText, extractedSegments) => {
    setVideoUrl(video);
    setAudioUrl(audio);
    setText(extractedText);
    setSegments(extractedSegments || []);
    setLoading(false);
  };

  const handleUploadStart = () => {
    setLoading(true);
    setError(null);
    setVideoUrl(null);
    setAudioUrl(null);
    setText(null);
    setSegments([]);
  };

  const handleClear = () => {
    setVideoUrl(null);
    setAudioUrl(null);
    setText(null);
    setSegments([]);
    setLoading(false);
    setError(null);
  };

  const handleError = (msg) => {
    setLoading(false);
    setError(msg);
  };

  return (
    <div className="converter-page app-container">
      <header className="app-header">
        <div className="logo">
          <Video className="logo-icon" size={24} />
          <h1>Vid2Manga</h1>
        </div>
        <div className="nav-container">
          <Link to="/" className="home-nav-btn">
            <HomeIcon size={16} /> Home
          </Link>
          <Link to="/manga-generator" className="home-nav-btn">
            <Columns size={16} /> Manga Generator
          </Link>
        </div>
      </header>

      <main className="app-main">
        <div className="workbench-layout">
          <div className="workbench-panel left-panel">
            <div className="panel-header">
              <div className="panel-title-wrapper">
                <span className="panel-number">01</span>
                <h2>Ingress Portal</h2>
              </div>
              { (videoUrl || audioUrl || error) && (
                <button className="clear-btn-text" onClick={handleClear}>
                  Reset Studio
                </button>
              )}
            </div>

            <div className="panel-body">
              <VideoUpload
                onUploadStart={handleUploadStart}
                onUploadSuccess={handleUploadSuccess}
                onError={handleError}
                isLoading={loading}
              />
            </div>
          </div>

          <div className="workbench-panel right-panel">
            <div className="panel-header">
              <div className="panel-title-wrapper">
                <span className="panel-number">02</span>
                <h2>Extraction output</h2>
              </div>
            </div>

            <div className="panel-body output-scroll-container">
              {loading && !videoUrl ? (
                <div className="workbench-placeholder loading">
                  <div className="loading-glitch-spinner"></div>
                  <div className="placeholder-text-group">
                    <h3>Decomposing Video...</h3>
                    <p className="mono-subtext">SPEECH PIPELINE STATUS: EXTRACTING AUDIO WAV</p>
                    <p>Executing zero-shot offline diarization AHC model on deep server tensors.</p>
                  </div>
                </div>
              ) : (videoUrl || audioUrl) ? (
                <ResultDisplay
                  videoUrl={videoUrl}
                  audioUrl={audioUrl}
                  text={text}
                  segments={segments}
                />
              ) : error ? (
                <div className="workbench-placeholder error-state">
                  <AlertCircle size={48} className="error-icon" />
                  <div className="placeholder-text-group">
                    <h3>Pipeline Interrupted</h3>
                    <p className="error-desc">{error}</p>
                    <button className="cta-button secondary" onClick={handleClear}>
                      Reinitialize Session
                    </button>
                  </div>
                </div>
              ) : (
                <div className="workbench-placeholder">
                  <Sparkles size={48} style={{ opacity: 0.15, color: "var(--accent-color)" }} />
                  <div className="placeholder-text-group">
                    <h3>Workspace Awaiting Input</h3>
                    <p>Upload a video clip in the ingress portal to start automatic frame splitting, speech-to-text diarization, and transcription synchronization.</p>
                  </div>
                  <div className="pipeline-steps-grid">
                    <div className="step-item">
                      <span className="step-num">A</span>
                      <span className="step-title">Extract WAV Monos</span>
                    </div>
                    <div className="step-item">
                      <span className="step-num">B</span>
                      <span className="step-title">Whisper Speech Synthesis</span>
                    </div>
                    <div className="step-item">
                      <span className="step-num">C</span>
                      <span className="step-title">ECAPA-TDNN Clustering</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>&copy; {new Date().getFullYear()} Vid2Manga Project. Precision speech-to-layout workbench.</p>
      </footer>
    </div>
  );
}

export default ConverterPage;
