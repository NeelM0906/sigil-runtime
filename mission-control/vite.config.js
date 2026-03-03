import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { tasksApiMiddleware } from './server/tasks-api.js'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: 'tasks-api',
      configureServer(server) {
        tasksApiMiddleware(server)
      }
    }
  ],
  server: {
    port: 5173,
  }
})
