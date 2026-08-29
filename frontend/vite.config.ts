import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Built assets are served by FastAPI's /static mount; the shell is returned
// for every /app route (app/routes/spa.py). In dev, API calls proxy to uvicorn.
export default defineConfig({
  base: "/static/app/",
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "../app/static/app",
    emptyOutDir: true,
    sourcemap: false,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/login": "http://localhost:8000",
      "/logout": "http://localhost:8000",
      "/settings": "http://localhost:8000",
      "/admin": "http://localhost:8000",
      "/htmx": "http://localhost:8000",
      "/static/css": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
