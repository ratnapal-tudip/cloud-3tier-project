import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())

  return {
    plugins: [
      react(),
      {
        name: 'log-backend',
        configureServer(server) {
          server.httpServer?.once('listening', () => {
            console.log(`\n  ➜  Backend: ${env.VITE_API_BASE_URL}\n`)
          })
        },
      },
    ],
  }
})
