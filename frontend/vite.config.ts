import { realpathSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dùng đường dẫn thật (D:\gold-bot có thể là junction) để Rollup không thấy hai đường dẫn cho cùng một file.
const root = realpathSync.native(fileURLToPath(new URL(".", import.meta.url)));

// Build ra web/static/dist để FastAPI phục vụ; khi dev, /api được proxy tới server Python.
export default defineConfig({
  root,
  plugins: [react()],
  base: "/static/dist/",
  build: { outDir: resolve(root, "../web/static/dist"), emptyOutDir: true, chunkSizeWarningLimit: 2000 },
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
});
