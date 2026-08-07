// SPDX-License-Identifier: Apache-2.0
// main.ts — builds the Gripster homepage from the doc-grounded content and wires
// the interactive viewer (spin · explode · hotspots) to the on-page controls.

import './styles.css'
import content from './content.json'
import { GripsterViewer, type Hotspot } from './viewer/GripsterViewer'

const REPO = 'https://github.com/neuman/gripster'
// Substack publication the signup forms subscribe to (no trailing slash).
const SUBSTACK_URL = 'https://ericneuman.substack.com'
const LINKS = {
  github: REPO,
  buildGuide: `${REPO}/blob/main/README.md#build-guide`,
  bom: `${REPO}/blob/main/docs/bill-of-materials.md`,
  firmware: `${REPO}/tree/main/firmware`,
  license: `${REPO}/blob/main/LICENSE`,
}

type Theme = 'light' | 'dark'

// ---------------------------------------------------------------------------
// tiny DOM helper
function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Record<string, string> = {},
  ...kids: (Node | string)[]
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag)
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') node.className = v
    else if (k === 'html') node.innerHTML = v
    else node.setAttribute(k, v)
  }
  for (const kid of kids) node.append(kid)
  return node
}

function icon(path: string): SVGSVGElement {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  svg.setAttribute('viewBox', '0 0 24 24')
  svg.setAttribute('aria-hidden', 'true')
  svg.innerHTML = path
  return svg
}
const ICONS = {
  spin: '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M20 12a8 8 0 1 1-2.3-5.6M20 4v3.5h-3.5"/>',
  hotspot: '<circle cx="12" cy="12" r="3.2" fill="currentColor"/><circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="1.6" opacity=".5"/>',
  reset: '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M3 9a9 9 0 1 1-1 5M3 4v5h5"/>',
  full: '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
  theme: '<path fill="currentColor" d="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9z"/>',
  close: '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M6 6l12 12M18 6L6 18"/>',
}

// ---------------------------------------------------------------------------
// theme
function initialTheme(): Theme {
  const saved = localStorage.getItem('gv-theme')
  if (saved === 'light' || saved === 'dark') return saved
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}
let theme: Theme = initialTheme()
function applyTheme(t: Theme) {
  theme = t
  document.documentElement.dataset.theme = t
  localStorage.setItem('gv-theme', t)
}
applyTheme(theme)

// Thumbnail-capture mode (?shot): dark, centred, static — used by the headless
// social-card renderer (scripts/render-thumbnail.mjs).
const SHOT = new URLSearchParams(location.search).has('shot')
if (SHOT) document.documentElement.classList.add('shot-mode')

// ---------------------------------------------------------------------------
// build the page
const app = document.getElementById('app')!

// -- newsletter signup -------------------------------------------------------
// Substack has no CORS-friendly subscribe API, so we hand the address to its own
// subscribe page (which pre-fills from ?email=) and let it finish the opt-in.
// `place` only distinguishes the two instances for ids/analytics.
function signup(place: 'top' | 'bottom'): HTMLElement {
  const input = el('input', {
    class: 'signup-input',
    id: `signup-email-${place}`,
    type: 'email',
    name: 'email',
    required: '',
    placeholder: 'you@example.com',
    autocomplete: 'email',
    'aria-label': 'Email address',
  })
  const form = el(
    'form',
    { class: 'signup-form', novalidate: '' },
    input,
    el('button', { class: 'btn btn-primary', type: 'submit' }, 'Subscribe'),
  )
  form.addEventListener('submit', (e) => {
    e.preventDefault()
    if (!input.checkValidity()) return input.reportValidity()
    window.open(
      `${SUBSTACK_URL}/subscribe?email=${encodeURIComponent(input.value)}`,
      '_blank',
      'noopener',
    )
  })

  return el(
    'section',
    { class: `signup signup--${place}`, 'aria-labelledby': `signup-h-${place}` },
    el('div', { class: 'signup-inner' },
      el('p', { class: 'eyebrow' }, 'Newsletter'),
      el('h2', { id: `signup-h-${place}` }, 'Get the build news by email'),
      el(
        'p',
        { class: 'signup-dek' },
        'Design updates, fabrication notes, and firmware progress on the Gripster — posted to my Substack as the build moves.',
      ),
      form,
      el(
        'p',
        { class: 'signup-note' },
        'Free. Unsubscribe anytime. ',
        el('a', { href: SUBSTACK_URL, target: '_blank', rel: 'noopener' }, 'Read past issues →'),
      ),
    ),
  )
}

// -- hero + viewer -----------------------------------------------------------
const viewerEl = el('div', { class: 'viewer', id: 'viewer' })
const loading = el('div', { class: 'viewer-loading' }, el('span', { class: 'spinner' }), 'loading model…')
viewerEl.append(loading)

const badges = el('ul', { class: 'badges' })
for (const b of content.hero.badges) badges.append(el('li', {}, b))

const heroCopy = el(
  'div',
  { class: 'hero-copy' },
  el('p', { class: 'eyebrow' }, 'Open-hardware project · rev-A'),
  el('h1', {}, content.hero.title),
  el('p', { class: 'tagline' }, content.hero.tagline),
  el('p', { class: 'subtag' }, content.hero.subtag),
  badges,
  el(
    'div',
    { class: 'hero-cta' },
    el('a', { class: 'btn btn-primary', href: '#why' }, content.hero.primaryCtaLabel),
    el('a', { class: 'btn btn-ghost', href: LINKS.github, target: '_blank', rel: 'noopener' }, 'View on GitHub'),
  ),
)

// control bar
function ctrlButton(label: string, iconPath: string, pressed = false): HTMLButtonElement {
  const b = el('button', { class: 'ctrl', type: 'button', 'aria-pressed': String(pressed), title: label })
  b.append(icon(iconPath))
  b.append(el('span', { class: 'ctrl-label' }, label))
  return b
}
const explodeInput = el('input', {
  class: 'explode-slider',
  type: 'range',
  min: '0',
  max: '100',
  value: '0',
  'aria-label': 'Explode / reassemble',
})
const spinBtn = ctrlButton('Spin', ICONS.spin)
const hotspotBtn = ctrlButton('Info', ICONS.hotspot, true)
const resetBtn = ctrlButton('Reset', ICONS.reset)
const fullBtn = ctrlButton('Fullscreen', ICONS.full)
const themeBtn = ctrlButton('Theme', ICONS.theme)

const controlBar = el(
  'div',
  { class: 'control-bar', role: 'toolbar', 'aria-label': 'Viewer controls' },
  el(
    'label',
    { class: 'explode' },
    el('span', { class: 'explode-cap' }, 'Assembled'),
    explodeInput,
    el('span', { class: 'explode-cap' }, 'Exploded'),
  ),
  el('div', { class: 'control-group' }, spinBtn, hotspotBtn, resetBtn, fullBtn, themeBtn),
)

// hotspot card
const card = el('aside', { class: 'hotspot-card', 'aria-live': 'polite' })

const hero = el(
  'header',
  { class: 'hero' },
  viewerEl,
  el('div', { class: 'hero-overlay' }, heroCopy),
  controlBar,
  card,
)
app.append(hero)
app.append(signup('top'))

// -- story sections ----------------------------------------------------------
type StoryFigure = { images: { src: string; alt: string }[]; caption: string }

// one or two reference images plus a caption, rendered inline between paragraphs
function storyFigure(f: StoryFigure): HTMLElement {
  const fig = el('figure', { class: `story-figure story-figure--${f.images.length}` })
  const frame = el('div', { class: 'story-figure-imgs' })
  for (const im of f.images) frame.append(el('img', { src: im.src, alt: im.alt, loading: 'lazy' }))
  fig.append(frame, el('figcaption', {}, f.caption))
  return fig
}

const story = el('main', { class: 'story', id: 'story' })
const byKey = new Map(content.sections.map((s: any) => [s.key, s]))
for (const key of content.sectionOrder) {
  const s: any = byKey.get(key)
  if (!s) continue
  // id = the section key, so anything can deep-link to a specific section
  // (the hero CTA points at #why). Keys are already unique — they index byKey above.
  const sec = el('section', { class: 'section', id: key })
  sec.append(el('h2', {}, s.heading))
  sec.append(el('p', { class: 'dek' }, s.dek))
  // a section body is prose, with figure blocks ({images, caption}) interleaved
  for (const p of s.paragraphs) {
    if (typeof p === 'string') sec.append(el('p', {}, p))
    else sec.append(storyFigure(p))
  }
  if (s.links?.length) {
    const ul = el('ul', { class: 'section-links' })
    for (const l of s.links) {
      ul.append(el('li', {}, el('a', { href: l.href, target: '_blank', rel: 'noopener' }, l.label)))
    }
    sec.append(ul)
  }
  story.append(sec)
}

// renders strip
const gallery = el(
  'section',
  { class: 'section gallery' },
  el('h2', {}, 'A closer look'),
  el('p', { class: 'dek' }, 'Straight from the model and the KiCad layout.'),
)
const grid = el('div', { class: 'render-grid' })
for (const [src, cap] of [
  ['./renders/assembly3d.png', 'Assembled deck'],
  ['./renders/assembly3d_exploded.png', 'Exploded layers'],
  ['./renders/fab_view.png', 'Fabrication view'],
  ['./renders/iter_22.png', 'Generated layout'],
] as const) {
  grid.append(
    el('figure', {}, el('img', { src, alt: cap, loading: 'lazy' }), el('figcaption', {}, cap)),
  )
}
gallery.append(grid)
story.append(gallery)
app.append(story)
app.append(signup('bottom'))

// -- footer ------------------------------------------------------------------
const footer = el(
  'footer',
  { class: 'footer' },
  el(
    'div',
    { class: 'footer-links' },
    el('a', { href: LINKS.github, target: '_blank', rel: 'noopener' }, 'GitHub'),
    el('a', { href: LINKS.buildGuide, target: '_blank', rel: 'noopener' }, 'Build guide'),
    el('a', { href: LINKS.bom, target: '_blank', rel: 'noopener' }, 'Bill of materials'),
    el('a', { href: LINKS.firmware, target: '_blank', rel: 'noopener' }, 'Firmware'),
  ),
  el(
    'p',
    { class: 'footer-note' },
    'Open hardware under Apache-2.0. ',
    el('a', { href: LINKS.license, target: '_blank', rel: 'noopener' }, 'License'),
  ),
)
app.append(footer)

// ---------------------------------------------------------------------------
// wire the viewer
function renderCard(h: Hotspot | null) {
  card.classList.toggle('is-open', !!h)
  if (!h) return
  card.replaceChildren(
    el(
      'button',
      { class: 'card-close', type: 'button', 'aria-label': 'Close' },
      icon(ICONS.close),
    ),
    el('p', { class: 'card-kicker' }, 'Component'),
    el('h3', {}, h.title),
    el('p', { class: 'card-one' }, h.oneLiner),
    el('p', { class: 'card-blurb' }, h.blurb),
    el('a', { class: 'card-more', href: h.href, target: '_blank', rel: 'noopener' }, `Read more in ${h.docLabel} →`),
  )
  card.querySelector('.card-close')!.addEventListener('click', () => viewer.closeHotspot())
}

// The phone in the 3D model types out the opening of "Why I built this", so the
// screen copy and the story copy can never drift apart.
const whySection: any = byKey.get('why')

const viewer = new GripsterViewer({
  container: viewerEl,
  proxyUrl: './models/thumbdeck_proxy.glb',
  mainUrl: './models/thumbdeck_web.glb',
  explodeUrl: './models/explode.json',
  hotspotsUrl: './models/hotspots.json',
  theme: SHOT ? 'dark' : theme,
  framingOffset: !SHOT, // centre the model for the thumbnail
  frameMargin: SHOT ? 0.72 : undefined, // tighter fill for the social card
  screenText: whySection?.paragraphs?.find((p: any) => typeof p === 'string') ?? '',
  screenAnimate: !SHOT, // the OG card needs one deterministic frame, not a loop
  onReady: () => loading.remove(),
  onFullLoaded: SHOT ? () => ((window as any).__thumbReady = true) : undefined,
  onHotspotOpen: (h) => renderCard(h),
})
if (SHOT) {
  viewer.setSpin(false)
  viewer.setHotspotsVisible(false) // clean product shot, no pins
}

// explode slider
explodeInput.addEventListener('input', () => {
  viewer.setExplode(Number(explodeInput.value) / 100)
})

// spin toggle (reflect reduced-motion + user-drag auto-stop)
function syncSpin(on: boolean) {
  spinBtn.setAttribute('aria-pressed', String(on))
}
syncSpin(viewer.isSpinning())
if (viewer.prefersReducedMotion()) spinBtn.title = 'Spin (reduced-motion is on)'
spinBtn.addEventListener('click', () => {
  const next = spinBtn.getAttribute('aria-pressed') !== 'true'
  viewer.setSpin(next)
  syncSpin(viewer.isSpinning())
})
viewerEl.addEventListener('gv:spin', (e) => syncSpin((e as CustomEvent).detail))

// hotspot toggle
hotspotBtn.addEventListener('click', () => {
  const next = hotspotBtn.getAttribute('aria-pressed') !== 'true'
  hotspotBtn.setAttribute('aria-pressed', String(next))
  viewer.setHotspotsVisible(next)
})

// reset + fullscreen
resetBtn.addEventListener('click', () => {
  viewer.resetView()
  explodeInput.value = '0'
  viewer.setExplode(0)
})
fullBtn.addEventListener('click', () => viewer.toggleFullscreen())
document.addEventListener('fullscreenchange', () => {
  // reflect fullscreen state, including exits via Esc / browser chrome
  fullBtn.setAttribute('aria-pressed', String(!!document.fullscreenElement))
})

// theme toggle
themeBtn.setAttribute('aria-pressed', String(theme === 'dark'))
themeBtn.addEventListener('click', () => {
  const next: Theme = theme === 'dark' ? 'light' : 'dark'
  applyTheme(next)
  viewer.setTheme(next)
  themeBtn.setAttribute('aria-pressed', String(next === 'dark'))
})

// close the card when clicking/dragging empty viewer space
viewerEl.addEventListener('pointerdown', (e) => {
  if (!(e.target as HTMLElement).closest('.gv-pin')) viewer.closeHotspot()
})
