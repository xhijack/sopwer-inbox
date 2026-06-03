import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

const FRAPPE_PORT = process.env.FRAPPE_PORT || "8000";
const target = `http://localhost:${FRAPPE_PORT}`;

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: "/assets/sopwer_inbox/frontend/",
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: "../sopwer_inbox/public/frontend",
    emptyOutDir: true,
    manifest: true,
    target: "es2018",
    sourcemap: false,
  },
  server: {
    port: 8080,
    proxy: {
      "^/(api|files|private|assets)": {
        target,
        changeOrigin: true,
      },
      "/socket.io": {
        target: `http://localhost:9000`,
        ws: true,
      },
    },
  },
});
