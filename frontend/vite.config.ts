import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Bindet innerhalb des Containers an alle Interfaces, damit Docker den Port
    // weiterleiten kann. Der Host-seitige Zugriff wird stattdessen ausschließlich
    // über die docker-compose-Portbindung auf 127.0.0.1 beschränkt (siehe
    // infra/docker-compose.yml und docs/projektauftrag.md Abschnitt 8).
    host: true,
    port: 5173,
    strictPort: true,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
  },
})
