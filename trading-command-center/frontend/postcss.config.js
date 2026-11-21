import { fileURLToPath } from 'node:url'

// Tailwind mencari config di cwd; npm script berjalan dari root proyek, jadi tunjuk file ini secara eksplisit.
export default {
  plugins: {
    tailwindcss: { config: fileURLToPath(new URL('./tailwind.config.js', import.meta.url)) },
    autoprefixer: {},
  },
}
