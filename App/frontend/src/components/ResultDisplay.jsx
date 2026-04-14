import React, { useRef } from "react";
import { Download, Film, Music, FileText } from "lucide-react";
import "../css/ResultDisplay.css";
import "../css/TextResult.css";

const ResultDisplay = ({ videoUrl, audioUrl, text, segments }) => {
  const videoRef = useRef(null);
  const audioRef = useRef(null);

  const handleJump = (startTime) => {
    if (videoRef.current) {
      videoRef.current.currentTime = startTime;
      videoRef.current.play().catch(() => {}); // Play might fail if not interacted with
    }
    if (audioRef.current) {
      audioRef.current.currentTime = startTime;
      audioRef.current.play().catch(() => {});
    }
  };

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
            <video ref={videoRef} controls src={videoUrl} className="result-video" />
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
            <audio ref={audioRef} controls src={audioUrl} className="result-audio" />
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

      <div className="text-result-container">
        <div className="result-card text-card">
          <div className="card-header">
            <FileText size={24} />
            <h3>Speech Breakdown</h3>
          </div>
          
          <div className="speech-timeline">
            {segments && segments.length > 0 ? (
              <div className="segments-list">
                {segments.map((segment, idx) => (
                  <div 
                    key={idx} 
                    className="segment-item clickable" 
                    title={`Click to play from ${segment.start.toFixed(1)}s`}
                    onClick={() => handleJump(segment.start)}
                  >
                    <div className="segment-speaker">{segment.speaker}</div>
                    <div className="segment-text">{segment.text}</div>
                    <div className="segment-time">{segment.start.toFixed(1)}s</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-content">
                <p>{text || "No speech detected or processed."}</p>
              </div>
            )}
          </div>

          {text && (
            <button
              className="copy-btn"
              onClick={() => navigator.clipboard.writeText(text)}
            >
              Copy Full Transcript
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ResultDisplay;
