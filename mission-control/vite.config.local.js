// Temporary config pointing at the new FastAPI server on :8788
// Usage: npx vite --config vite.config.local.js --port 5176
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const API_TARGET = 'http://localhost:8788'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5176,
    proxy: {
      '/api/mc/events': {
        target: API_TARGET,
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            proxyRes.headers['cache-control'] = 'no-cache'
            proxyRes.headers['x-accel-buffering'] = 'no'
          })
        },
      },
      '/api/mc': {
        target: API_TARGET,
        changeOrigin: true,
      },
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
      '/deliverables': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
})
