import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { tasksApiMiddleware } from './server/tasks-api.js'
import { beingsApiMiddleware } from './server/beings-api.js'
import { chatApiMiddleware } from './server/chat-api.js'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: 'mission-control-api',
      configureServer(server) {
        tasksApiMiddleware(server)
        beingsApiMiddleware(server)
        chatApiMiddleware(server)
      }
    }
  ],
  server: {
    port: 5173,
  }
})
