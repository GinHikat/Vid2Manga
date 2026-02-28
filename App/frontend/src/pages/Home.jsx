import React from "react";
import { Link } from "react-router-dom";
import { Video, Star, Zap, PenTool } from "lucide-react";
import "../css/Home.css"; // We'll create this CSS file next

function Home() {
  return (
    <div className="home-container">
      <header className="home-hero">
        <div className="hero-content">
          <h1>
            Vid2<span className="accent">Manga</span>
          </h1>
          <p className="hero-subtitle">
            Turn your favorite video clips into stunning manga panels.
          </p>
          <div className="hero-actions">
            <Link to="/convert" className="cta-button primary">
              Start Creating <Video size={20} />
            </Link>
            <a href="#features" className="cta-button secondary">
              Learn More
            </a>
          </div>
        </div>
      </header>

      <section id="features" className="features-section">
        <h2>Why Vid2Manga?</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="icon-wrapper">
              <Zap size={32} />
            </div>
            <h3>Fast Processing</h3>
            <p>Convert videos in seconds with our optimized pipeline.</p>
          </div>
          <div className="feature-card">
            <div className="icon-wrapper">
              <PenTool size={32} />
            </div>
            <h3>Manga Style</h3>
            <p>Automatically extract frames and apply manga aesthetics.</p>
          </div>
          <div className="feature-card">
            <div className="icon-wrapper">
              <Star size={32} />
            </div>
            <h3>High Quality</h3>
            <p>Get high-resolution output suitable for printing or sharing.</p>
          </div>
        </div>
      </section>

      <footer className="home-footer">
        <p>&copy; {new Date().getFullYear()} Vid2Manga Project</p>
      </footer>
    </div>
  );
}

export default Home;
