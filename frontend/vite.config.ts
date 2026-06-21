import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api wird an das Backend weitergereicht (Dev). Ziel via VITE_API_TARGET
// überschreibbar (z. B. http://backend:8000 in docker-compose).
const target = process.env.VITE_API_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target, changeOrigin: true } },
  },
});
