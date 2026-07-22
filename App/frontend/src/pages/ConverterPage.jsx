import React, { useState, useRef } from "react";
import axios from "axios";
import { API_BASE_URL } from "../config";
import VideoUpload from "../components/VideoUpload";
import ResultDisplay from "../components/ResultDisplay";
import "../css/App.css";
import "../css/Nav.css";
import "../css/MangaGenerator.css";

import {
  Video,
  Home as HomeIcon,
  Columns,
  Sparkles,
  AlertCircle,
  Upload,
  Settings,
  Image as ImageIcon,
  Download,
  Loader2,
  Film,
} from "lucide-react";
import { Link } from "react-router-dom";

function ConverterPage() {
  const [activeTab, setActiveTab] = useState("video"); // 'video' | 'image'

  // Video Mode State
  const [videoUrl, setVideoUrl] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [text, setText] = useState(null);
  const [segments, setSegments] = useState([]);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [mangaUrls, setMangaUrls] = useState([]);
  const [loading, setLoading] = useState(false);
  const [progressText, setProgressText] = useState(null);
  const [error, setError] = useState(null);

  // Image Mode State
  const [imgFiles, setImgFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [widthPreset, setWidthPreset] = useState("1000");
  const [width, setWidth] = useState(1000);
  const [heightPreset, setHeightPreset] = useState("1400");
  const [height, setHeight] = useState(1400);
  const [numFrames, setNumFrames] = useState(8);
  const [seed, setSeed] = useState(42);
  const [stylizeStyle, setStylizeStyle] = useState("c");
  const [segmentHuman, setSegmentHuman] = useState(false);
  const [imgResultUrls, setImgResultUrls] = useState([]);
  const [imgLoading, setImgLoading] = useState(false);

  const fileInputRef = useRef(null);

  // Video Handlers
  const handleUploadSuccess = (video, audio, extractedText, extractedSegments, pdf, mangaPages) => {
    setVideoUrl(video);
    setAudioUrl(audio);
    setText(extractedText);
    setSegments(extractedSegments || []);
    setPdfUrl(pdf || null);
    setMangaUrls(mangaPages || []);
    setLoading(false);
  };

  const handleProgressUpdate = (prog) => {
    setProgressText(prog);
  };

  const handleUploadStart = () => {
    setLoading(true);
    setError(null);
    setProgressText("[1/5] Extracting 16kHz mono WAV audio and soundless video...");
    setVideoUrl(null);
    setAudioUrl(null);
    setText(null);
    setSegments([]);
    setPdfUrl(null);
    setMangaUrls([]);
  };

  const handleClear = () => {
    setVideoUrl(null);
    setAudioUrl(null);
    setText(null);
    setSegments([]);
    setPdfUrl(null);
    setMangaUrls([]);
    setImgFiles([]);
    setPreviews([]);
    setImgResultUrls([]);
    setLoading(false);
    setImgLoading(false);
    setError(null);
  };

  const handleError = (msg) => {
    setLoading(false);
    setImgLoading(false);
    setError(msg);
  };

  // Image Handlers
  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    if (selectedFiles.length === 0) return;
    setImgFiles(selectedFiles);
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
      "b277ba4933fe126f13415cf423a665aa_8995668507856338057.jpg",
    ];

    try {
      setImgLoading(true);
      setError(null);
      const loadedFiles = [];
      const loadedPreviews = [];

      for (const name of sampleImagesList) {
        const response = await fetch(`/samples/${name}`);
        if (!response.ok) throw new Error(`Sample image ${name} not found`);
        const blob = await response.blob();
        let type = name.endsWith(".jpg") || name.endsWith(".jfif") ? "image/jpeg" : "image/png";
        const file = new File([blob], name, { type });
        loadedFiles.push(file);
        loadedPreviews.push(URL.createObjectURL(file));
      }

      setImgFiles(loadedFiles);
      setPreviews(loadedPreviews);
    } catch (err) {
      console.error(err);
      setError("Failed to load sample images.");
    } finally {
      setImgLoading(false);
    }
  };

  const handleGenerateImgLayout = async () => {
    if (imgFiles.length === 0) {
      setError("Please upload at least one image.");
      return;
    }

    setImgLoading(true);
    setError(null);
    setImgResultUrls([]);

    const formData = new FormData();
    imgFiles.forEach((file) => formData.append("files", file));
    formData.append("width", width);
    formData.append("height", height);
    formData.append("num_frames", numFrames);
    formData.append("seed", seed);
    formData.append("stylize_style", stylizeStyle);
    formData.append("segment_human", segmentHuman ? "true" : "false");
    formData.append("show_mask", segmentHuman ? "true" : "false");

    try {
      const response = await axios.post(`${API_BASE_URL}/manga-layout`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const baseUrl = API_BASE_URL.replace(/\/api$/, "");
      const urls = response.data.manga_urls.map((url) =>
        url.startsWith("http") ? url : `${baseUrl}${url}`
      );

      setImgResultUrls(urls);
    } catch (err) {
      console.error(err);
      setError("Failed to generate manga layout. Please try again.");
    } finally {
      setImgLoading(false);
    }
  };

  return (
    <div className="converter-page app-container">
      <header className="app-header">
        <div className="logo">
          <Video className="logo-icon" size={24} />
          <h1>Vid2Manga Studio</h1>
        </div>
        <div className="nav-container">
          <Link to="/" className="home-nav-btn">
            <HomeIcon size={16} /> Home
          </Link>
        </div>
      </header>

      <main className="app-main">
        {/* Mode Switcher */}
        <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", justifyContent: "center" }}>
          <button
            className={`cta-button ${activeTab === "video" ? "primary" : "secondary"}`}
            onClick={() => setActiveTab("video")}
            style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.75rem 1.5rem" }}
          >
            <Film size={18} /> Video to Manga Converter
          </button>
          <button
            className={`cta-button ${activeTab === "image" ? "primary" : "secondary"}`}
            onClick={() => setActiveTab("image")}
            style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.75rem 1.5rem" }}
          >
            <Columns size={18} /> Image Layout Studio
          </button>
        </div>

        <div className="workbench-layout">
          {/* Left Ingress Panel */}
          <div className="workbench-panel left-panel">
            <div className="panel-header">
              <div className="panel-title-wrapper">
                <span className="panel-number">01</span>
                <h2>{activeTab === "video" ? "Video Ingress" : "Image Set Ingress"}</h2>
              </div>
              {(videoUrl || audioUrl || imgResultUrls.length > 0 || error) && (
                <button className="clear-btn-text" onClick={handleClear}>
                  Reset Studio
                </button>
              )}
            </div>

            <div className="panel-body">
              {activeTab === "video" ? (
                <VideoUpload
                  onUploadStart={handleUploadStart}
                  onUploadSuccess={handleUploadSuccess}
                  onProgressUpdate={handleProgressUpdate}
                  onError={handleError}
                  isLoading={loading}
                  progressText={progressText}
                />
              ) : (
                <aside className="controls-card" style={{ background: "transparent", border: "none", padding: 0 }}>
                  <div className="control-group">
                    <label>
                      <Settings size={12} style={{ marginRight: "0.25rem", color: "var(--accent-color)" }} />
                      Page Dimensions (px)
                    </label>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
                      <select
                        className="control-input"
                        value={widthPreset}
                        onChange={(e) => {
                          setWidthPreset(e.target.value);
                          if (e.target.value !== "custom") setWidth(parseInt(e.target.value));
                        }}
                      >
                        <option value="800">Width: 800</option>
                        <option value="1000">Width: 1000</option>
                        <option value="1200">Width: 1200</option>
                        <option value="1400">Width: 1400</option>
                      </select>

                      <select
                        className="control-input"
                        value={heightPreset}
                        onChange={(e) => {
                          setHeightPreset(e.target.value);
                          if (e.target.value !== "custom") setHeight(parseInt(e.target.value));
                        }}
                      >
                        <option value="1000">Height: 1000</option>
                        <option value="1200">Height: 1200</option>
                        <option value="1400">Height: 1400</option>
                        <option value="1600">Height: 1600</option>
                      </select>
                    </div>
                  </div>

                  <div className="control-group">
                    <label>Frames per Page</label>
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
                      <option value="c">Style C (Comic Soft)</option>
                    </select>
                  </div>

                  <div className="control-group">
                    <div className="checkbox-group" onClick={() => setSegmentHuman(!segmentHuman)}>
                      <input type="checkbox" checked={segmentHuman} readOnly />
                      <span>Segment Character Masks</span>
                    </div>
                  </div>

                  <div className="upload-area" onClick={() => fileInputRef.current.click()} style={{ margin: "1rem 0" }}>
                    <Upload size={28} style={{ marginBottom: "0.5rem", color: "var(--accent-color)" }} />
                    <p>{imgFiles.length > 0 ? `${imgFiles.length} images selected` : "Click to Ingress Images"}</p>
                    <input type="file" multiple hidden ref={fileInputRef} onChange={handleFileChange} accept="image/*" />
                  </div>

                  <button
                    className="cta-button secondary"
                    onClick={handleLoadSampleImages}
                    disabled={imgLoading}
                    style={{ width: "100%", marginBottom: "1rem" }}
                  >
                    Use 8 Sample Images
                  </button>

                  {previews.length > 0 && (
                    <div className="image-preview-grid" style={{ marginBottom: "1rem" }}>
                      {previews.map((url, idx) => (
                        <div key={idx} className="preview-item">
                          <img src={url} alt={`preview ${idx}`} />
                        </div>
                      ))}
                    </div>
                  )}

                  <button
                    className="generate-button"
                    onClick={handleGenerateImgLayout}
                    disabled={imgLoading || imgFiles.length === 0}
                  >
                    {imgLoading ? <Loader2 className="animate-spin" size={18} /> : <Sparkles size={18} />}
                    {imgLoading ? "Generating layout..." : "Generate Manga Page"}
                  </button>
                </aside>
              )}
            </div>
          </div>

          {/* Right Output Panel */}
          <div className="workbench-panel right-panel">
            <div className="panel-header">
              <div className="panel-title-wrapper">
                <span className="panel-number">02</span>
                <h2>{activeTab === "video" ? "Pipeline Output" : "Custom Layout Output"}</h2>
              </div>
            </div>

            <div className="panel-body output-scroll-container">
              {activeTab === "video" ? (
                videoUrl || audioUrl ? (
                  <ResultDisplay
                    videoUrl={videoUrl}
                    audioUrl={audioUrl}
                    text={text}
                    segments={segments}
                    pdfUrl={pdfUrl}
                    mangaUrls={mangaUrls}
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
                      <p>{loading ? "Pipeline is executing... Check the ingress portal for live step status." : "Upload a video clip to run single-pass speech diarization, keyframe extraction, face-protected bubble typesetting, and PDF volume generation."}</p>
                    </div>
                  </div>
                )
              ) : (
                /* Image Mode Output */
                imgLoading ? (
                  <div className="workbench-placeholder loading">
                    <div className="loading-glitch-spinner"></div>
                    <div className="placeholder-text-group">
                      <h3>Synthesizing Manga Layout...</h3>
                      <p className="mono-subtext">PIPELINE TASK: RECURSIVE SPLITTING TREE</p>
                    </div>
                  </div>
                ) : imgResultUrls.length > 0 ? (
                  <div className="manga-result-card">
                    {imgResultUrls.map((url, idx) => (
                      <div key={idx} className="result-display-area" style={{ width: "100%", display: "flex", flexDirection: "column", alignItems: "center", marginBottom: "1.5rem" }}>
                        <img src={url} alt={`Manga Result Page ${idx + 1}`} className="manga-result-image" style={{ width: "100%", borderRadius: "8px", border: "1px solid #333" }} />
                        <a href={url} download={`manga_page_${idx + 1}.png`} className="cta-button primary" target="_blank" rel="noopener noreferrer" style={{ marginTop: "0.75rem" }}>
                          <Download size={18} /> Download Page {idx + 1}
                        </a>
                      </div>
                    ))}
                  </div>
                ) : error ? (
                  <div className="workbench-placeholder error-state">
                    <AlertCircle size={48} className="error-icon" />
                    <div className="placeholder-text-group">
                      <h3>Generation Failed</h3>
                      <p className="error-desc">{error}</p>
                    </div>
                  </div>
                ) : (
                  <div className="workbench-placeholder">
                    <ImageIcon size={48} style={{ opacity: 0.15, color: "var(--accent-color)", marginBottom: "1rem" }} />
                    <div className="placeholder-text-group">
                      <h3>Canvas Viewport Empty</h3>
                      <p>Import one or more frames and click generate to initiate layout aspect-ratio mapping and background rendering.</p>
                    </div>
                  </div>
                )
              )}
            </div>
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>&copy; {new Date().getFullYear()} Vid2Manga Project. Precision speech-to-layout studio workbench.</p>
      </footer>
    </div>
  );
}

export default ConverterPage;
