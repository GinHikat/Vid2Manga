import React from "react";
import { Link } from "react-router-dom";
import { Video, Star, Zap, PenTool, Columns } from "lucide-react";
import heroImage from "../manga_hero_preview.png";
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
            <Video size={16} /> Video Converter
          </Link>
          <Link to="/manga-generator" className="home-nav-btn">
            <Columns size={16} /> Manga Generator
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
                Convert videos into highly stylized manga layouts with custom visual filter pipelines and dynamic speaker-aware typesetting in seconds.
              </p>
              <div className="hero-actions">
                <Link to="/convert" className="cta-button primary">
                  Video Converter <Video size={18} />
                </Link>
                <Link to="/manga-generator" className="cta-button secondary">
                  Manga Generator <Columns size={18} />
                </Link>
              </div>
            </div>
            
            <div className="hero-visual-panel">
              <div className="visual-frame">
                <img 
                  src={heroImage} 
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
            <h2 className="section-title">Automated Production Line</h2>
            <p className="section-subtitle">
              Advanced computer vision and natural speech diarization pipelines fused into a singular design tool.
            </p>
          </div>
          
          <div className="features-bento">
            <div className="bento-cell highlight-cell">
              <div className="bento-content">
                <div className="icon-wrapper">
                  <Zap size={24} />
                </div>
                <h3>Diarized Speech Breakdown</h3>
                <p>
                  Synchronize dialogue transcription directly with characters using pyannote-audio and zero-shot ECAPA-TDNN speaker clustering.
                </p>
                <div className="bento-mono-tag">MODULE: /speech/process_audio.py</div>
              </div>
            </div>
            
            <div className="bento-cell standard-cell">
              <div className="bento-content">
                <div className="icon-wrapper">
                  <PenTool size={24} />
                </div>
                <h3>Dynamic Stylization Filters</h3>
                <p>
                  Choose between Classic Black & White (CLAHE + Adaptive Thresholding), Cel-shaded Anime colors, or Edge-Preserving Comic smoothing.
                </p>
                <div className="bento-mono-tag">MODULE: /frame/stylizer.py</div>
              </div>
            </div>
            
            <div className="bento-cell standard-cell">
              <div className="bento-content">
                <div className="icon-wrapper">
                  <Star size={24} />
                </div>
                <h3>Binary Splitting Layouts</h3>
                <p>
                  Automatically partition pages with a Recursive Binary Splitting Tree algorithm that resolves aspect ratios without frame overlapping.
                </p>
                <div className="bento-mono-tag">MODULE: /frame/layout_generator.py</div>
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
