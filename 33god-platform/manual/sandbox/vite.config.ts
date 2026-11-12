import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Built into ../books/sandbox so the existing manual.delo.sh nginx bind mount
// serves it at /sandbox/ with no compose change. That folder is gitignored.
export default defineConfig({
  base: '/sandbox/',
  plugins: [react()],
  build: { outDir: '../books/sandbox', emptyOutDir: true, chunkSizeWarningLimit: 2000 },
})
