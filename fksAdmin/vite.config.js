import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const proxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:5000'
const buildOutDir =
  process.env.VITE_BUILD_OUTDIR
  || (process.platform === 'win32' ? 'dist' : '../fksapi/admin/dist')

export default defineConfig({
  plugins: [vue()],
  base: '/admin/',
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: buildOutDir,
    emptyOutDir: true,
  },
})
