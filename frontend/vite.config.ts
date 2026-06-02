import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    // En bind-mounts de Windows/OneDrive no llegan eventos inotify → HMR no
    // se dispara solo. El polling fuerza a Vite a detectar los cambios.
    watch: {
      usePolling: true,
      interval: 300,
    },
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
