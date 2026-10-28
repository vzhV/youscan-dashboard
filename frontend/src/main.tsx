// antd v5+ ships no CSS reset; without it <body> keeps the browser default 8px margin.
import "antd/dist/reset.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import { activeDemoModes, installDemoMode } from "./shared/api/demoMode";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root is missing from index.html");
}

installDemoMode(activeDemoModes);

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
