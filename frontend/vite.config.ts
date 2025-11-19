import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000, // Frontend dev server runs on port 3000
    host: true, // Allow external connections
    strictPort: true, // Fail if port 3000 is not available (ensures it always runs on 3000)
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000', // Backend API runs on port 8000
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})

