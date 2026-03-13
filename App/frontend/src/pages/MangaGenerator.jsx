import React, { useState, useRef } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  Upload,
  Settings,
  Image as ImageIcon,
  Home as HomeIcon,
  Sparkles,
  User,
  Eye,
  Download,
  Loader2,
  Columns,
  Video,
} from "lucide-react";
import "../css/MangaGenerator.css";
import "../css/App.css";

const MangaGenerator = () => {
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [widthPreset, setWidthPreset] = useState("1000");
  const [width, setWidth] = useState(1000);
  const [heightPreset, setHeightPreset] = useState("1400");
  const [height, setHeight] = useState(1400);
  const [numFrames, setNumFrames] = useState(8);
  const [seed, setSeed] = useState(42);
  const [stylizeStyle, setStylizeStyle] = useState("c");
  const [segmentHuman, setSegmentHuman] = useState(false);

  const [loading, setLoading] = useState(false);
  const [resultUrls, setResultUrls] = useState([]);
  const [error, setError] = useState(null);

  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    if (selectedFiles.length === 0) return;

    setFiles(selectedFiles);

    // Create previews
    const newPreviews = selectedFiles.map((file) => URL.createObjectURL(file));
    setPreviews(newPreviews);
  };

  const handleGenerate = async () => {
    if (files.length === 0) {
      setError("Please upload at least one image.");
      return;
    }

    setLoading(true);
    setError(null);
    setResultUrls([]);

    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    formData.append("width", width);
    formData.append("height", height);
    formData.append("num_frames", numFrames);
    formData.append("seed", seed);
    formData.append("stylize_style", stylizeStyle);
    formData.append("segment_human", segmentHuman ? "true" : "false");
    formData.append("show_mask", segmentHuman ? "true" : "false");

    try {
      const response = await axios.post(
        "http://localhost:8000/manga-layout",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        },
      );

      const baseUrl = "http://localhost:8000";
      const mangaUrls = response.data.manga_urls.map((url) =>
        url.startsWith("http") ? url : `${baseUrl}${url}`,
      );

      setResultUrls(mangaUrls);
    } catch (err) {
      console.error(err);
      setError("Failed to generate manga layout. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="manga-generator-page app-container">
      <header className="app-header">
        <div className="nav-container">
          <Link to="/" className="home-nav-btn">
            <HomeIcon size={20} /> Home
          </Link>
          <Link to="/convert" className="home-nav-btn">
            <Video size={20} /> Video Converter
          </Link>
        </div>
        <div className="logo">
          <Columns className="logo-icon" size={32} />
          <h1>Manga Frame Generator</h1>
        </div>
        <p className="subtitle">
          Transform your images into professional manga layouts
        </p>
      </header>

      <main className="app-main manga-generator-container">
        <div className="generator-grid">
          <aside className="controls-card">
            <div className="control-group">
              <label>
                <Settings size={14} /> Page Dimensions (px)
              </label>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "0.5rem",
                }}
              >
                <select
                  className="control-input"
                  value={widthPreset}
                  onChange={(e) => {
                    setWidthPreset(e.target.value);
                    if (e.target.value !== "custom")
                      setWidth(parseInt(e.target.value));
                  }}
                >
                  <option value="800">Width: 800</option>
                  <option value="1000">Width: 1000</option>
                  <option value="1200">Width: 1200</option>
                  <option value="1400">Width: 1400</option>
                  <option value="1600">Width: 1600</option>
                  <option value="custom">Custom Width</option>
                </select>

                <select
                  className="control-input"
                  value={heightPreset}
                  onChange={(e) => {
                    setHeightPreset(e.target.value);
                    if (e.target.value !== "custom")
                      setHeight(parseInt(e.target.value));
                  }}
                >
                  <option value="1000">Height: 1000</option>
                  <option value="1200">Height: 1200</option>
                  <option value="1400">Height: 1400</option>
                  <option value="1600">Height: 1600</option>
                  <option value="1800">Height: 1800</option>
                  <option value="custom">Custom Height</option>
                </select>

                {(widthPreset === "custom" || heightPreset === "custom") && (
                  <>
                    {widthPreset === "custom" ? (
                      <input
                        type="number"
                        className="control-input"
                        placeholder="Custom Width"
                        value={width}
                        onChange={(e) =>
                          setWidth(parseInt(e.target.value) || 0)
                        }
                      />
                    ) : (
                      <div />
                    )}
                    {heightPreset === "custom" ? (
                      <input
                        type="number"
                        className="control-input"
                        placeholder="Custom Height"
                        value={height}
                        onChange={(e) =>
                          setHeight(parseInt(e.target.value) || 0)
                        }
                      />
                    ) : (
                      <div />
                    )}
                  </>
                )}
              </div>
            </div>

            <div className="control-group">
              <label>Number of Frames per Page</label>
              <input
                type="number"
                className="control-input"
                value={numFrames}
                onChange={(e) => setNumFrames(parseInt(e.target.value) || 0)}
              />
            </div>

            <div className="control-group">
              <label>Stylization Pipeline</label>
              <select
                className="control-input"
                value={stylizeStyle}
                onChange={(e) => setStylizeStyle(e.target.value)}
              >
                <option value="a">Style A (Classic Black & White)</option>
                <option value="b">Style B (Anime Cel-shaded)</option>
                <option value="c">Style C (Comic/Soft)</option>
              </select>
            </div>

            <div className="control-group checkboxes-flex">
              <div
                className="checkbox-group"
                onClick={() => setSegmentHuman(!segmentHuman)}
              >
                <input type="checkbox" checked={segmentHuman} readOnly />
                <label>
                  <User size={14} /> Segment Human
                </label>
              </div>
            </div>

            <div
              className="upload-area"
              onClick={() => fileInputRef.current.click()}
            >
              <Upload
                size={32}
                style={{ marginBottom: "0.5rem", color: "#6366f1" }}
              />
              <p>
                {files.length > 0
                  ? `${files.length} images selected`
                  : "Click to Upload Images"}
              </p>
              <input
                type="file"
                multiple
                hidden
                ref={fileInputRef}
                onChange={handleFileChange}
                accept="image/*"
              />
            </div>

            {previews.length > 0 && (
              <div className="image-preview-grid">
                {previews.map((url, idx) => (
                  <div key={idx} className="preview-item">
                    <img src={url} alt={`preview ${idx}`} />
                  </div>
                ))}
              </div>
            )}

            <button
              className="generate-button"
              onClick={handleGenerate}
              disabled={loading || files.length === 0}
            >
              {loading ? (
                <Loader2 className="animate-spin" size={20} />
              ) : (
                <Sparkles size={20} />
              )}
              {loading ? "Generating Layout..." : "Generate Manga Page"}
            </button>

            {error && (
              <p
                className="error-text"
                style={{
                  color: "#ef4444",
                  marginTop: "1rem",
                  fontSize: "0.9rem",
                  textAlign: "center",
                }}
              >
                {error}
              </p>
            )}
          </aside>

          <section className="result-card" style={{ gap: "2rem" }}>
            {resultUrls && resultUrls.length > 0 ? (
              resultUrls.map((url, idx) => (
                <div
                  key={idx}
                  className="result-display-area"
                  style={{
                    width: "100%",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                  }}
                >
                  <img
                    src={url}
                    alt={`Manga Result Page ${idx + 1}`}
                    className="manga-result-image"
                  />
                  <div
                    className="result-actions"
                    style={{
                      marginTop: "1.5rem",
                      display: "flex",
                      gap: "1rem",
                    }}
                  >
                    <a
                      href={url}
                      download={`manga_page_${idx + 1}.png`}
                      className="cta-button primary"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Download size={20} /> Download Page {idx + 1}
                    </a>
                  </div>
                </div>
              ))
            ) : (
              <div className="placeholder-state">
                {loading ? (
                  <div className="loading-state">
                    <div className="loading-spinner"></div>
                    <p style={{ marginTop: "1rem" }}>
                      Creating your manga layout...
                    </p>
                  </div>
                ) : (
                  <>
                    <ImageIcon
                      size={64}
                      style={{ opacity: 0.1, marginBottom: "1rem" }}
                    />
                    <p>Your generated manga page will appear here</p>
                  </>
                )}
              </div>
            )}
          </section>
        </div>
      </main>

      <footer className="app-footer">
        <p>&copy; {new Date().getFullYear()} Vid2Manga Project</p>
      </footer>
    </div>
  );
};

export default MangaGenerator;
