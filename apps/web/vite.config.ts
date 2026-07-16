import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          "react-vendor": ["react", "react-dom", "react-router-dom"],
          "supabase-vendor": ["@supabase/supabase-js"],
          "icon-vendor": ["lucide-react"]
        }
      }
    }
  },
  server: {
    port: 4173
  },
  preview: {
    port: 4173
  }
});
