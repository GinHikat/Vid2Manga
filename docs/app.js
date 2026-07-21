document.addEventListener("DOMContentLoaded", () => {
  // Page Gallery Data
  const pageData = {
    1: {
      title: "Manga Page 1 (Timeline: 0.0s – 91.9s)",
      desc: "7-panel layout generated using Recursive Binary Splitting Tree. Dialogue transcribed via OpenAI Whisper base model and speaker-attributed via ECAPA-TDNN AHC clustering.",
      src: "assets/manga_page_1.png",
      panels: 7,
      overlap: "0%",
      speakers: 2
    },
    2: {
      title: "Manga Page 2 (Timeline: 91.9s – 183.9s)",
      desc: "Middle timeline section covering high-density dialogue exchanges. Dynamic bubble scaling automatically resizes close-up speech bubbles to 16pt font to prevent character face occlusion.",
      src: "assets/manga_page_2.png",
      panels: 7,
      overlap: "0%",
      speakers: 2
    },
    3: {
      title: "Manga Page 3 (Timeline: 183.9s – 275.8s)",
      desc: "Climax timeline section featuring multi-character group panels. Non-destructive solid white bubble rendering keeps dialogue bubbles 100% crisp and readable.",
      src: "assets/manga_page_3.png",
      panels: 7,
      overlap: "0%",
      speakers: 2
    }
  };

  // Tab Control Switching
  const tabBtns = document.querySelectorAll(".tab-btn");
  const pageImg = document.getElementById("manga-page-img");
  const pageTitle = document.getElementById("page-title");
  const pageDesc = document.getElementById("page-desc");

  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const pageNum = btn.getAttribute("data-page");
      const data = pageData[pageNum];

      if (data) {
        pageImg.src = data.src;
        pageTitle.textContent = data.title;
        pageDesc.textContent = data.desc;
      }
    });
  });

  // Pipeline Step Explorer Data
  const stepData = {
    1: {
      tag: "STAGE 1",
      title: "Video Partitioning & Smart Keyframe Selection",
      body: "Splits the source video file into duration-based sections. Samples candidate frames every 6.5 seconds directly in memory, bypassing temporary file disk writes for maximum processing speed."
    },
    2: {
      tag: "STAGE 2",
      title: "Mask2Former Neural Instance Segmentation",
      body: "Runs Mask2Former (finetuned ADE20K mini) on 720p HD canvas arrays to detect person instances and compute exact character binary masks."
    },
    3: {
      tag: "STAGE 3",
      title: "ECAPA-TDNN Zero-Shot Speaker Diarization",
      body: "Extracts 192-dimensional normalized speaker embeddings using offline ECAPA-TDNN and clusters speaker identities via Agglomerative Hierarchical Clustering (AHC)."
    },
    4: {
      tag: "STAGE 4",
      title: "Collision-Free Open-Space Typesetting",
      body: "Uses distance-transform mapping to find optimal background bubble centers, applies 2D rectangle collision shifting, and scales fonts adaptively for tight close-up panels."
    },
    5: {
      tag: "STAGE 5",
      title: "A4 Manga PDF Volume Compositing",
      body: "Composites stylized panels into a Recursive Binary Splitting layout tree and merges all page PNG outputs into a single downloadable PDF volume."
    }
  };

  const pipelineCards = document.querySelectorAll(".pipeline-card");
  const detailTag = document.getElementById("detail-tag");
  const detailTitle = document.getElementById("detail-title");
  const detailBody = document.getElementById("detail-body");

  pipelineCards.forEach(card => {
    card.addEventListener("click", () => {
      pipelineCards.forEach(c => c.classList.remove("active"));
      card.classList.add("active");

      const stepNum = card.getAttribute("data-step");
      const data = stepData[stepNum];

      if (data) {
        detailTag.textContent = data.tag;
        detailTitle.textContent = data.title;
        detailBody.textContent = data.body;
      }
    });
  });

  // Lightbox Zoom Modal
  const zoomBtn = document.getElementById("zoom-btn");
  const lightbox = document.getElementById("lightbox");
  const lightboxImg = document.getElementById("lightbox-img");
  const lightboxClose = document.getElementById("lightbox-close");

  function openLightbox() {
    lightboxImg.src = pageImg.src;
    lightbox.style.display = "flex";
  }

  function closeLightbox() {
    lightbox.style.display = "none";
  }

  if (zoomBtn) zoomBtn.addEventListener("click", openLightbox);
  if (pageImg) pageImg.addEventListener("click", openLightbox);
  if (lightboxClose) lightboxClose.addEventListener("click", closeLightbox);
  if (lightbox) {
    lightbox.addEventListener("click", (e) => {
      if (e.target === lightbox) closeLightbox();
    });
  }
});
