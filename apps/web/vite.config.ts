import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vite.dev/config/
// En dev, el frontend (5173) habla con el backend (8000) a través de un PROXY same-origin:
// el navegador ve todo bajo http://localhost:5173, así las cookies httpOnly de sesión + CSRF
// (SameSite=Lax) viajan sin problemas y no hay CORS. En prod se sirve el build same-origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
