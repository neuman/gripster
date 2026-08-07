// SPDX-License-Identifier: Apache-2.0
// render-thumbnail.mjs — render a candidate social card straight from the live
// Three.js viewer so it always matches the current model. Spins up a headless
// Vite dev server, loads the site in ?shot mode (dark, centred, static) in
// headless Chromium, waits for the full-res GLB to load, and screenshots the
// canvas. Run as the last step of `npm run models`.
//
// ⚠ It writes og-card-auto.png, NOT og-card.png. The card the meta tags actually
// publish (public/renders/og-card.png) is hand-picked — currently the 3/4 hero
// shot from renders/collapsed.png — and this script must not clobber it. If you
// want the auto-rendered one to go live, copy it over og-card.png deliberately
// and update og:image:width/height in index.html to match.
//
// Requires Chromium: `npx playwright install chromium` (one time).

import { createServer } from 'vite'
import { chromium } from 'playwright'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SITE = resolve(__dirname, '..')
const OUT = resolve(SITE, 'public/renders/og-card-auto.png')
const PORT = 4189
// 1200x630 is the canonical OG size; render at 2x for crisp retina previews.
const WIDTH = 1200
const HEIGHT = 630
const SCALE = 2

const server = await createServer({
  root: SITE,
  logLevel: 'warn',
  server: { port: PORT, strictPort: true },
})
await server.listen()

const browser = await chromium.launch({
  // ensure WebGL works in headless via SwiftShader
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
})
let failed = false
try {
  const page = await browser.newPage({
    viewport: { width: WIDTH, height: HEIGHT },
    deviceScaleFactor: SCALE,
  })
  page.on('pageerror', (e) => console.error('[page error]', e.message))
  await page.goto(`http://localhost:${PORT}/?shot`, { waitUntil: 'load' })
  // wait for the full-res model to be in the scene
  await page.waitForFunction('window.__thumbReady === true', { timeout: 45000 })
  // let a couple of frames render + damping settle
  await page.waitForTimeout(700)

  const canvas = page.locator('canvas.gv-canvas')
  await canvas.screenshot({ path: OUT })
  console.log(`wrote ${OUT}  (${WIDTH * SCALE}x${HEIGHT * SCALE})`)
} catch (err) {
  failed = true
  const msg = err?.message || String(err)
  console.error('thumbnail render failed:', msg)
  if (/Executable doesn't exist|playwright install|browserType.launch/i.test(msg)) {
    console.error('  → install the browser once with:  npx playwright install chromium')
  }
} finally {
  await browser.close()
  await server.close()
}
process.exit(failed ? 1 : 0)
