import React, { useState } from "react";
import VideoUpload from "../components/VideoUpload";
import ResultDisplay from "../components/ResultDisplay";
import "../css/App.css";
import "../css/Nav.css";

import { Video, Home as HomeIcon } from "lucide-react";
import { Link } from "react-router-dom";

function ConverterPage() {
  const [videoUrl, setVideoUrl] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [text, setText] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleUploadSuccess = (video, audio, extractedText) => {
    setVideoUrl(video);
    setAudioUrl(audio);
    setText(extractedText);
    setLoading(false);
  };

  const handleUploadStart = () => {
    setLoading(true);
    setError(null);
    setVideoUrl(null);
    setAudioUrl(null);
    setText(null);
  };

  const handleError = (msg) => {
    setLoading(false);
    setError(msg);
  };

  return (
    <div className="converter-page app-container">
      <header className="app-header">
        <Link to="/" className="home-nav-btn">
          <HomeIcon size={20} /> Home
        </Link>
        <div className="logo">
          <Video className="logo-icon" size={32} />
          <h1>Vid2Manga</h1>
        </div>
        <p className="subtitle">
          Transform your videos into manga-style creations
        </p>
      </header>
      <main className="app-main">
        <div className="content-wrapper">
          <section className="upload-section">
            <VideoUpload
              onUploadStart={handleUploadStart}
              onUploadSuccess={handleUploadSuccess}
              onError={handleError}
              isLoading={loading}
            />
          </section>

          {(videoUrl || audioUrl) && (
            <section className="result-section">
              <ResultDisplay
                videoUrl={videoUrl}
                audioUrl={audioUrl}
                text={text}
              />
            </section>
          )}

          {error && (
            <div className="error-message">
              <p>{error}</p>
            </div>
          )}
        </div>
      </main>
      <footer className="app-footer">
        <p>&copy; {new Date().getFullYear()} Vid2Manga Project</p>
      </footer>
    </div>
  );
}

export default ConverterPage;
