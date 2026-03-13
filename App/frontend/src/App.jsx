import React from "react";
import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import ConverterPage from "./pages/ConverterPage";
import MangaGenerator from "./pages/MangaGenerator";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/convert" element={<ConverterPage />} />
      <Route path="/manga-generator" element={<MangaGenerator />} />
    </Routes>
  );
}

export default App;
