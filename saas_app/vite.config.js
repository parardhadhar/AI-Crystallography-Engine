import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: './', // Crucial for Electron to resolve paths relatively
  server: {
    hmr: {
      overlay: false, // Disables the full-screen black error overlay caused by Chrome Extensions crashing
    }
  }
})
