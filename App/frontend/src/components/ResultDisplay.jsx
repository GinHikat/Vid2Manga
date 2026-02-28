import React from "react";
import { Download, Film, Music, FileText } from "lucide-react";
import "../css/ResultDisplay.css";
import "../css/TextResult.css";

const ResultDisplay = ({ videoUrl, audioUrl, text }) => {
  return (
    <div className="result-display-container">
      <h2>Conversion Results</h2>
      <div className="results-grid">
        <div className="result-card video-card">
          <div className="card-header">
            <Film size={24} />
            <h3>Soundless Video</h3>
          </div>
          <div className="media-wrapper">
            <video controls src={videoUrl} className="result-video" />
          </div>
          <a href={videoUrl} download className="download-btn">
            <Download size={16} /> Download Video
          </a>
        </div>

        <div className="result-card audio-card">
          <div className="card-header">
            <Music size={24} />
            <h3>Extracted Audio</h3>
          </div>
          <div className="media-wrapper audio-wrapper">
            <audio controls src={audioUrl} className="result-audio" />
            <div className="audio-visualizer-mock">
              <span></span>
              <span></span>
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
          <a href={audioUrl} download className="download-btn">
            <Download size={16} /> Download Audio
          </a>
        </div>
      </div>

      {text && (
        <div className="text-result-container">
          <div className="result-card text-card">
            <div className="card-header">
              <FileText size={24} />
              <h3>Extracted Text</h3>
            </div>
            <div className="text-content">
              <p>{text}</p>
            </div>
            <button
              className="copy-btn"
              onClick={() => navigator.clipboard.writeText(text)}
            >
              Copy Text
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ResultDisplay;
