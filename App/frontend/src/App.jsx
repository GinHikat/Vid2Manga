import React from "react";
import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import ConverterPage from "./pages/ConverterPage";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/convert" element={<ConverterPage />} />
    </Routes>
  );
}

export default App;
