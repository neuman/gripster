import { defineConfig } from 'vite'

// Relative base so the same build works at the user's github.io/<repo> subpath
// and when served from root locally (vite dev / preview). All asset refs in the
// app are relative (./models/..., ./renders/...), so './' is safe for a SPA.
export default defineConfig({
  base: './',
  build: {
    target: 'es2022',
    assetsInlineLimit: 0, // never inline the GLBs
  },
})
