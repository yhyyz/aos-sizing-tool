import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/v2': 'http://localhost:9989',
      '/provisioned/log_analytics_sizing': 'http://localhost:9989',
      '/provisioned/es_ec2_sizing': 'http://localhost:9989',
      '/provisioned/region_list': 'http://localhost:9989',
    },
  },
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  },
})
