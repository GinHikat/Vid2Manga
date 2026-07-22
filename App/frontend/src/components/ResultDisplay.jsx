import React, { useRef } from "react";
import { Download, Film, Music, FileText, BookOpen, ExternalLink } from "lucide-react";
import "../css/ResultDisplay.css";
import "../css/TextResult.css";

const ResultDisplay = ({ videoUrl, audioUrl, text, segments, pdfUrl, mangaUrls }) => {
  const videoRef = useRef(null);
  const audioRef = useRef(null);

  const handleJump = (startTime) => {
    if (videoRef.current) {
      videoRef.current.currentTime = startTime;
      videoRef.current.play().catch(() => {});
    }
    if (audioRef.current) {
      audioRef.current.currentTime = startTime;
      audioRef.current.play().catch(() => {});
    }
  };

  return (
    <div className="result-display-container">
      <h2>Conversion Results</h2>

      {pdfUrl && (
        <div className="manga-volume-card result-card" style={{ marginBottom: "1.5rem", border: "1px solid var(--accent-color)" }}>
          <div className="card-header">
            <BookOpen size={24} style={{ color: "var(--accent-color)" }} />
            <h3>Generated Manga Volume PDF</h3>
          </div>
          <div style={{ padding: "1rem 0" }}>
            <p style={{ margin: "0 0 1rem 0", color: "#aaa" }}>
              Your video has been transformed into a stylized multi-page manga volume with face-protected speech bubbles.
            </p>
            <a href={pdfUrl} target="_blank" rel="noreferrer" download className="download-btn primary-btn" style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem", width: "auto", padding: "0.75rem 1.5rem" }}>
              <Download size={18} /> Download Full Manga PDF Volume
            </a>
          </div>

          {mangaUrls && mangaUrls.length > 0 && (
            <div className="manga-gallery" style={{ marginTop: "1rem" }}>
              <h4 style={{ marginBottom: "0.75rem", fontSize: "0.95rem", color: "#ddd" }}>Manga Pages ({mangaUrls.length})</h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: "1rem" }}>
                {mangaUrls.map((url, idx) => (
                  <div key={idx} style={{ background: "#111", borderRadius: "8px", padding: "0.5rem", border: "1px solid #333" }}>
                    <img src={url} alt={`Manga Page ${idx + 1}`} style={{ width: "100%", borderRadius: "4px", display: "block", marginBottom: "0.5rem" }} />
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: "0.8rem", color: "#aaa" }}>Page {idx + 1}</span>
                      <a href={url} target="_blank" rel="noreferrer" style={{ color: "var(--accent-color)", display: "flex", alignItems: "center", gap: "0.25rem", fontSize: "0.8rem", textDecoration: "none" }}>
                        View <ExternalLink size={12} />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

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
