import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In `npm run dev`, proxy /api to the Dockerized backend (Caddy on :8080) so the
// SPA and API share an origin and httpOnly cookies work without CORS. In the
// production build, Caddy serves the static bundle and proxies /api itself.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY ?? "http://localhost:8080",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
