import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api/mc': {
        target: 'http://localhost:8787',
        changeOrigin: true,
        // All SSE endpoints need no buffering (events, code sessions)
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
              proxyRes.headers['cache-control'] = 'no-cache'
              proxyRes.headers['x-accel-buffering'] = 'no'
            }
          })
        },
      },
      '/api': {
        target: 'http://localhost:8787',
        changeOrigin: true,
      },
      '/deliverables': {
        target: 'http://localhost:8787',
        changeOrigin: true,
      },
    },
  },
})
