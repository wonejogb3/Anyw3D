import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// El frontend corre en 5173 y habla con el backend en 8000.
// Proxy opcional: cualquier /api o /files se reenvía al backend, así el
// navegador no tiene problemas de CORS en desarrollo.
export default defineConfig({
  plugins: [react()],
  // "npm run build" deja la web compilada en backend/web: el backend la sirve
  // en "/" y el .exe portable la incluye (sin necesidad de Node en el usuario).
  build: {
    outDir: "../backend/web",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/files": "http://127.0.0.1:8000",
    },
  },
});
