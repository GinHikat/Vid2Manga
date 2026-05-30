import React, { useState, useRef } from "react";
import axios from "axios";
import { API_BASE_URL } from "../config";
import { Link } from "react-router-dom";
import {
  Upload,
  Settings,
  Image as ImageIcon,
  Home as HomeIcon,
  Sparkles,
  User,
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

  const handleLoadSampleImages = async () => {
    const sampleImagesList = [
      "342375242_245331094648423_7404527358037104979_n.png",
      "365711745_686517320175796_1531261400117098977_n.jpg",
      "368623532_24004931352438669_6751496886235696436_n.png",
      "7064856a94ff75f226c851aa854a471a_1229983858974666441.jpg",
      "F0q65O8aQAEZlDs.jfif",
      "F0q65PDaIAEZe5t.jfif",
      "F0q65PyaEAkKx7p.jfif",
      "b277ba4933fe126f13415cf423a665aa_8995668507856338057.jpg"
    ];

    try {
      setLoading(true);
      setError(null);
      const loadedFiles = [];
      const loadedPreviews = [];
      
      for (const name of sampleImagesList) {
        const response = await fetch(`/samples/${name}`);
        if (!response.ok) throw new Error(`Sample image ${name} not found`);
        const blob = await response.blob();
        
        let type = "image/png";
        if (name.endsWith(".jpg") || name.endsWith(".jfif")) {
          type = "image/jpeg";
        }
        
        const file = new File([blob], name, { type });
        loadedFiles.push(file);
        loadedPreviews.push(URL.createObjectURL(file));
      }
      
      setFiles(loadedFiles);
      setPreviews(loadedPreviews);
    } catch (err) {
      console.error(err);
      setError("Failed to load sample images.");
    } finally {
      setLoading(false);
    }
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
        `${API_BASE_URL}/manga-layout`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        },
      );

      const baseUrl = API_BASE_URL.replace(/\/api$/, "");

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
        <div className="logo">
          <Columns className="logo-icon" size={24} />
          <h1>Vid2Manga</h1>
        </div>
        <div className="nav-container">
          <Link to="/" className="home-nav-btn">
            <HomeIcon size={16} /> Home
          </Link>
          <Link to="/convert" className="home-nav-btn">
            <Video size={16} /> Video Converter
          </Link>
        </div>
      </header>

      <main className="app-main manga-generator-container">
        <div className="generator-grid">
          <aside className="controls-card">
            <div className="control-group">
              <label>
                <Settings size={12} style={{ marginRight: "0.25rem", color: "var(--accent-color)" }} /> 
                Page Dimensions (px)
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

            <div className="control-group">
              <div
                className="checkbox-group"
                onClick={() => setSegmentHuman(!segmentHuman)}
              >
                <input type="checkbox" checked={segmentHuman} readOnly />
                <span>Segment Character Masks</span>
              </div>
            </div>

            <div
              className="upload-area"
              onClick={() => fileInputRef.current.click()}
            >
              <Upload
                size={28}
                style={{ marginBottom: "0.5rem", color: "var(--accent-color)" }}
              />
              <p>
                {files.length > 0
                  ? `${files.length} images selected`
                  : "Click to Ingress Images"}
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

            <button
              className="cta-button secondary"
              onClick={handleLoadSampleImages}
              disabled={loading}
              style={{ width: "100%", marginBottom: "1rem" }}
            >
              Use 8 Sample Images
            </button>

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
                <Loader2 className="animate-spin" size={18} />
              ) : (
                <Sparkles size={18} />
              )}
              {loading ? "Generating layout..." : "Generate Manga Page"}
            </button>

            {error && (
              <p
                className="error-text"
                style={{
                  color: "#ef4444",
                  marginTop: "1rem",
                  fontSize: "0.9rem",
                  fontFamily: "var(--font-mono)",
                  textAlign: "center",
                }}
              >
                {error}
              </p>
            )}
          </aside>

          <section className="manga-result-card">
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
                  <div className="manga-result-actions">
                    <a
                      href={url}
                      download={`manga_page_${idx + 1}.png`}
                      className="cta-button primary"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Download size={18} /> Download Page {idx + 1}
                    </a>
                  </div>
                </div>
              ))
            ) : (
              <div className="workbench-placeholder" style={{ padding: 0 }}>
                {loading ? (
                  <div className="loading-state">
                    <div className="loading-spinner"></div>
                    <div className="placeholder-text-group" style={{ marginTop: "1.5rem" }}>
                      <h3>Synthesizing Manga Layout...</h3>
                      <p className="mono-subtext">PIPELINE TASK: RECURSIVE SPLITTING TREE</p>
                    </div>
                  </div>
                ) : (
                  <>
                    <ImageIcon
                      size={48}
                      style={{ opacity: 0.15, color: "var(--accent-color)", marginBottom: "1rem" }}
                    />
                    <div className="placeholder-text-group">
                      <h3>Canvas Viewport Empty</h3>
                      <p>Import one or more frames and click generate to initiate layout aspect-ratio mapping and background rendering.</p>
                    </div>
                  </>
                )}
              </div>
            )}
          </section>
        </div>
      </main>

      <footer className="app-footer">
        <p>&copy; {new Date().getFullYear()} Vid2Manga Project. Precision visual-to-page production.</p>
      </footer>
    </div>
  );
};

export default MangaGenerator;
