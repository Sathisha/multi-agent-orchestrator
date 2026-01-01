import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
        secure: false,
        // Don't rewrite path - Kong expects /api prefix
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})