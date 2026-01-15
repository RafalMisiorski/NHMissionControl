import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3200,
    proxy: {
      '/api/v1/nh': {
        target: 'http://localhost:8100',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/v1\/nh/, '/api'),
      },
      '/api': {
        target: 'http://localhost:8200',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8200',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8200',
        ws: true,
      },
    },
  },
})
