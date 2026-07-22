import React from "react";
import { Link } from "react-router-dom";
import { Video, Star, Zap, PenTool, Columns } from "lucide-react";
import "../css/Home.css";

function Home() {
  return (
    <div className="home-container">
      <header className="app-header">
        <div className="logo">
          <Columns className="logo-icon" size={24} />
          <h1>Vid2Manga</h1>
        </div>
        <div className="nav-container">
          <Link to="/convert" className="home-nav-btn">
            <Video size={16} /> Vid2Manga Studio
          </Link>
        </div>
      </header>

      <main className="home-main">
        <section className="home-hero">
          <div className="hero-grid">
            <div className="hero-text-panel">
              <div className="status-indicator">
                <span className="dot animate-pulse"></span>
                <span className="status-label">STUDIO WORKSPACE ACTIVE</span>
              </div>
              <h1 className="hero-title">
                Video to <span className="accent">Manga</span>
              </h1>
              <p className="hero-subtitle">
                Convert videos and image sets into highly stylized manga layouts with face-protected speech bubbles and dynamic speaker-aware typesetting.
              </p>
              <div className="hero-actions">
                <Link to="/convert" className="cta-button primary">
                  Launch Studio Workbench <Video size={18} />
                </Link>
              </div>
            </div>
            
            <div className="hero-visual-panel">
              <div className="visual-frame">
                <img 
                  src="/samples/manga_hero_preview.png" 
                  alt="Manga Layout Rendering Preview" 
                  className="hero-display-image"
                />
                <div className="visual-caption">
                  <span className="caption-tag">FRAME PREVIEW</span>
                  <span className="caption-detail">PIPELINE C: COMIC EFFECT</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="features-section">
          <div className="section-header">
            <h2 className="section-title">5-Step Master Pipeline Architecture</h2>
            <p className="section-subtitle">
              Automated computer vision and speech diarization stages transforming raw video into printable manga volumes.
            </p>
          </div>
          
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem", marginTop: "1rem" }}>
            <div className="bento-cell standard-cell">
              <div className="bento-content">
                <div style={{ fontSize: "0.8rem", fontFamily: "var(--font-mono)", color: "var(--accent-color)", fontWeight: "bold", marginBottom: "0.5rem" }}>
                  STEP 01
                </div>
                <h3>Video Keyframe Capturing</h3>
                <p>
                  Extracts scene-aware keyframes using HSV histogram differences, Laplacian clarity filtering, and a 7.0s max scene gap constraint.
                </p>
                <div className="bento-mono-tag">MODULE: video_processor.py</div>
              </div>
            </div>

            <div className="bento-cell standard-cell">
              <div className="bento-content">
                <div style={{ fontSize: "0.8rem", fontFamily: "var(--font-mono)", color: "var(--accent-color)", fontWeight: "bold", marginBottom: "0.5rem" }}>
                  STEP 02
                </div>
                <h3>Mask2Former Person Masking</h3>
                <p>
                  In-memory neural instance segmentation detecting character bounding boxes and building face/head protection masks (`face_head_mask`).
                </p>
                <div className="bento-mono-tag">MODULE: human_detector.py</div>
              </div>
            </div>

            <div className="bento-cell standard-cell">
              <div className="bento-content">
                <div style={{ fontSize: "0.8rem", fontFamily: "var(--font-mono)", color: "var(--accent-color)", fontWeight: "bold", marginBottom: "0.5rem" }}>
                  STEP 03
                </div>
                <h3>ECAPA-TDNN Diarization</h3>
                <p>
                  Extracts 192-dim voice embeddings and clusters speaker identities via AHC with persistent global speaker-to-person mapping.
                </p>
                <div className="bento-mono-tag">MODULE: diarization.py</div>
              </div>
            </div>

            <div className="bento-cell standard-cell">
              <div className="bento-content">
                <div style={{ fontSize: "0.8rem", fontFamily: "var(--font-mono)", color: "var(--accent-color)", fontWeight: "bold", marginBottom: "0.5rem" }}>
                  STEP 04
                </div>
                <h3>Face-Protected Typesetting</h3>
                <p>
                  Distance-transform open-space bubble placement, zero bubble-on-bubble overlap penalty, and dynamic font size scaling.
                </p>
                <div className="bento-mono-tag">MODULE: bubble_processor.py</div>
              </div>
            </div>

            <div className="bento-cell standard-cell">
              <div className="bento-content">
                <div style={{ fontSize: "0.8rem", fontFamily: "var(--font-mono)", color: "var(--accent-color)", fontWeight: "bold", marginBottom: "0.5rem" }}>
                  STEP 05
                </div>
                <h3>A4 Manga PDF Compositing</h3>
                <p>
                  Recursive Binary Splitting layout tree compositing with 2px black inter-panel borders and multi-page Pillow PDF volume export.
                </p>
                <div className="bento-mono-tag">MODULE: end_to_end_vid2manga.py</div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="home-footer">
        <p>&copy; {new Date().getFullYear()} Vid2Manga Project. Built for premium visual production.</p>
      </footer>
    </div>
  );
}

export default Home;
