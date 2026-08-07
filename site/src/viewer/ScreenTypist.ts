// SPDX-License-Identifier: Apache-2.0
// ScreenTypist — a live canvas texture for the phone's screen in the 3D viewer.
//
// Draws a terminal-style writing app that types out the opening of "Why I built
// this", holds, erases, and loops — so the render reads as somebody actually
// thumb-typing on the deck instead of showing a frozen screenshot.
//
// Orientation: the phone GLB is portrait (its screen texture is 1080x2400) but
// it is CLAMPED LANDSCAPE in the product, so the source JPEG has its content
// rotated a quarter turn — reading bottom-to-top up the portrait image. We draw
// into a landscape design space and apply the same quarter turn, which keeps the
// existing UVs valid (texture.flipY = false, matching glTF convention).
//
// Cost control: the viewer only redraws when something changed, so update()
// returns true ONLY when the visible character count or the cursor blink state
// actually flipped — roughly 15-25 texture uploads a second while typing, and
// none at all once the model is idle off-loop.

import { CanvasTexture, LinearFilter, SRGBColorSpace } from 'three'

// ---- design space (LANDSCAPE — as the user sees it holding the deck) --------
// The canvas itself is portrait at this aspect; 900x2000 is 9:20, matching the
// S25U screen texture it replaces, at a resolution that stays crisp when the
// viewer is zoomed into the screen but is cheap enough to re-upload per frame.
const TEX_W = 900
const TEX_H = 2000
const W = TEX_H // landscape width  (2000)
const H = TEX_W // landscape height (900)

const PAD_X = 112
// Chrome (title bar / status line) keeps the same inset as the body text: the
// screen's outer few percent is eaten by the rounded corners and the clamp's
// capture lip, so anything closer to the edge gets cropped in the render.
const CHROME_X = PAD_X
const HEADER_H = 96
const FOOTER_H = 82
const FONT_PX = 52
const LINE_H = 70
const BODY_TOP = HEADER_H + 54
const BODY_BOTTOM = H - FOOTER_H - 34

const MONO = `${FONT_PX}px "JetBrains Mono", "SF Mono", "Fira Code", Menlo, Consolas, "DejaVu Sans Mono", monospace`
const CHROME_FONT = `30px "JetBrains Mono", "SF Mono", Menlo, Consolas, "DejaVu Sans Mono", monospace`

const COLOR = {
  bg: '#070b09',
  chromeBg: '#0d1310',
  chromeRule: '#1d2a23',
  dim: '#4d6b5b',
  text: '#8affc1',
  accent: '#39e08a',
  cursor: '#8affc1',
}

// ---- typing rhythm (ms) ----------------------------------------------------
const BASE_KEY = 44 // mean per-character interval (~60wpm — a good thumb typist)
const JITTER = 46 // uniform +/- spread, so it never feels metronomic
const AFTER_WORD = 34 // extra beat after a space
const AFTER_COMMA = 190
const AFTER_STOP = 460 // end of a sentence
const THINK_EVERY = 0.014 // chance a keystroke turns into a pause
const THINK_MS = 620
const HOLD_MS = 2600 // sit and read the finished text
const ERASE_MS = 900 // fast backspace-erase of the whole buffer
const GAP_MS = 900 // blank screen before the next take
const BLINK_MS = 1060 // full on/off cycle

/** Deterministic PRNG so the animation (and the OG-card render) is stable. */
function lcg(seed: number) {
  let s = seed >>> 0
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296)
}

export interface ScreenTypistOptions {
  /** Prose to type. Trimmed to whole sentences that fit the screen. */
  text: string
  /** Filename shown in the title bar. */
  filename?: string
  /** false = draw one representative frame and never animate (reduced motion / shot mode). */
  animate?: boolean
}

export class ScreenTypist {
  readonly texture: CanvasTexture

  private canvas: HTMLCanvasElement
  private ctx: CanvasRenderingContext2D
  private lines: string[] = [] // pre-wrapped, so nothing reflows mid-word
  private lineStart: number[] = [] // char index at which each line begins
  private charTime: number[] = [] // charTime[i] = ms at which char i has been typed
  private total = 0
  private cols = 40
  private visibleRows = 8

  private animate: boolean
  private filename: string
  private cycleMs = 1
  private typeEnd = 0
  private holdEnd = 0
  private eraseEnd = 0
  private start = 0
  private lastChars = -1
  private lastCursor = false

  constructor(opts: ScreenTypistOptions) {
    this.animate = opts.animate !== false
    this.filename = opts.filename ?? 'why-i-built-this.md'

    this.canvas = document.createElement('canvas')
    this.canvas.width = TEX_W
    this.canvas.height = TEX_H
    const ctx = this.canvas.getContext('2d')
    if (!ctx) throw new Error('ScreenTypist: 2D canvas unavailable')
    this.ctx = ctx

    this.layout(opts.text)
    this.schedule()

    this.texture = new CanvasTexture(this.canvas)
    this.texture.flipY = false // glTF convention — the UVs on phone__10 assume it
    this.texture.colorSpace = SRGBColorSpace
    this.texture.generateMipmaps = false // re-uploaded constantly; mips aren't worth it
    this.texture.minFilter = LinearFilter
    this.texture.magFilter = LinearFilter

    this.start = performance.now()
    // Static modes park on a mostly-typed frame — a blank or half-empty screen
    // makes a poor social card.
    this.draw(this.animate ? 0 : Math.floor(this.total * 0.82), true)
  }

  /** Wrap `text` to the terminal's column width, keeping only what fits. */
  private layout(text: string) {
    this.ctx.font = MONO
    const chW = this.ctx.measureText('M').width || FONT_PX * 0.6
    this.cols = Math.max(16, Math.floor((W - PAD_X * 2) / chW))
    this.visibleRows = Math.max(3, Math.floor((BODY_BOTTOM - BODY_TOP) / LINE_H))

    const words = text.replace(/\s+/g, ' ').trim().split(' ')
    const lines: string[] = ['']
    for (const word of words) {
      const line = lines[lines.length - 1]
      if (!line) lines[lines.length - 1] = word
      else if (line.length + 1 + word.length <= this.cols) lines[lines.length - 1] = `${line} ${word}`
      else lines.push(word)
    }

    // "The first few lines" — a couple of sentences, so a full type-erase-repeat
    // cycle runs ~20s rather than the ~40s the whole paragraph would take.
    const maxLines = Math.min(this.visibleRows, 7)
    if (lines.length > maxLines) lines.length = maxLines
    let joined = lines.join(' ')
    // End on a sentence boundary if there is one to end on.
    const stop = Math.max(joined.lastIndexOf('. '), joined.lastIndexOf('? '), joined.lastIndexOf('! '))
    if (stop > joined.length * 0.45) joined = joined.slice(0, stop + 1)

    // Re-wrap the trimmed text so the last line isn't a truncation artefact.
    this.lines = ['']
    for (const word of joined.split(' ')) {
      const line = this.lines[this.lines.length - 1]
      if (!line) this.lines[this.lines.length - 1] = word
      else if (line.length + 1 + word.length <= this.cols) this.lines[this.lines.length - 1] = `${line} ${word}`
      else this.lines.push(word)
    }

    this.lineStart = []
    let n = 0
    for (const line of this.lines) {
      this.lineStart.push(n)
      n += line.length + 1 // +1 for the newline the wrap stands in for
    }
    this.total = Math.max(0, n - 1)
  }

  /** Precompute when each character lands, so the loop is time-driven, not frame-driven. */
  private schedule() {
    const rnd = lcg(0x9e3779b9)
    const flat = this.lines.join('\n')
    let t = 0
    this.charTime = new Array(this.total)
    for (let i = 0; i < this.total; i++) {
      const ch = flat[i]
      let dt = BASE_KEY + (rnd() - 0.5) * 2 * JITTER
      if (ch === ' ' || ch === '\n') dt += AFTER_WORD
      const prev = flat[i - 1]
      if (prev === ',' || prev === ';' || prev === '—') dt += AFTER_COMMA
      if (prev === '.' || prev === '?' || prev === '!') dt += AFTER_STOP
      if (rnd() < THINK_EVERY) dt += THINK_MS
      t += Math.max(18, dt)
      this.charTime[i] = t
    }
    this.typeEnd = t
    this.holdEnd = this.typeEnd + HOLD_MS
    this.eraseEnd = this.holdEnd + ERASE_MS
    this.cycleMs = this.eraseEnd + GAP_MS
  }

  /**
   * Advance the animation. Returns true when the canvas was repainted, which is
   * the viewer's cue to schedule a WebGL frame.
   */
  update(now: number): boolean {
    if (!this.animate) return false
    const phase = (now - this.start) % this.cycleMs

    let chars: number
    let cursor: boolean
    if (phase < this.typeEnd) {
      chars = this.charsAt(phase)
      cursor = true // solid while keys are going down, like a real editor
    } else if (phase < this.holdEnd) {
      chars = this.total
      cursor = (phase - this.typeEnd) % BLINK_MS < BLINK_MS * 0.55
    } else if (phase < this.eraseEnd) {
      const k = (phase - this.holdEnd) / ERASE_MS
      chars = Math.round(this.total * (1 - k * k)) // eases into the wipe
      cursor = true
    } else {
      chars = 0
      cursor = (phase - this.eraseEnd) % BLINK_MS < BLINK_MS * 0.55
    }

    if (chars === this.lastChars && cursor === this.lastCursor) return false
    this.draw(chars, cursor)
    return true
  }

  /** How many characters have been typed by `t` ms into the cycle (binary search). */
  private charsAt(t: number): number {
    let lo = 0
    let hi = this.total
    while (lo < hi) {
      const mid = (lo + hi) >> 1
      if (this.charTime[mid] <= t) lo = mid + 1
      else hi = mid
    }
    return lo
  }

  private draw(chars: number, cursor: boolean) {
    this.lastChars = chars
    this.lastCursor = cursor
    const ctx = this.ctx

    ctx.setTransform(1, 0, 0, 1, 0, 0)
    ctx.clearRect(0, 0, TEX_W, TEX_H)
    // Quarter turn into the landscape design space: the deck is held sideways,
    // so "up the portrait texture" is the reading direction.
    ctx.translate(0, TEX_H)
    ctx.rotate(-Math.PI / 2)

    ctx.fillStyle = COLOR.bg
    ctx.fillRect(0, 0, W, H)

    this.drawHeader(ctx)
    const caret = this.drawBody(ctx, chars)
    if (cursor) this.drawCaret(ctx, caret.x, caret.y)
    this.drawFooter(ctx, chars, caret.row, caret.col)

    this.texture.needsUpdate = true
  }

  private drawHeader(ctx: CanvasRenderingContext2D) {
    ctx.fillStyle = COLOR.chromeBg
    ctx.fillRect(0, 0, W, HEADER_H)
    ctx.fillStyle = COLOR.chromeRule
    ctx.fillRect(0, HEADER_H - 2, W, 2)

    // three window dots, dimmed to keep the focus on the text
    const dots = ['#3b4a41', '#3b4a41', '#3b4a41']
    dots.forEach((c, i) => {
      ctx.beginPath()
      ctx.arc(CHROME_X + i * 46, HEADER_H / 2, 13, 0, Math.PI * 2)
      ctx.fillStyle = c
      ctx.fill()
    })

    ctx.font = CHROME_FONT
    ctx.textBaseline = 'middle'
    ctx.textAlign = 'center'
    ctx.fillStyle = COLOR.dim
    ctx.fillText(this.filename, W / 2, HEADER_H / 2 + 2)
    ctx.textAlign = 'left'
  }

  /** Draws the typed prefix; returns the caret cell so the cursor can follow it. */
  private drawBody(ctx: CanvasRenderingContext2D, chars: number) {
    ctx.font = MONO
    ctx.textBaseline = 'top'
    const chW = ctx.measureText('M').width

    // which line the caret is on
    let row = 0
    while (row + 1 < this.lines.length && this.lineStart[row + 1] <= chars) row++
    const col = Math.min(chars - this.lineStart[row], this.lines[row].length)

    // scroll so the caret line is always on screen
    const firstRow = Math.max(0, row - (this.visibleRows - 1))

    ctx.fillStyle = COLOR.text
    for (let r = firstRow; r < Math.min(this.lines.length, firstRow + this.visibleRows); r++) {
      const shown = Math.max(0, Math.min(this.lines[r].length, chars - this.lineStart[r]))
      if (!shown) continue
      const y = BODY_TOP + (r - firstRow) * LINE_H
      ctx.fillText(this.lines[r].slice(0, shown), PAD_X, y)
    }

    return {
      row,
      col,
      x: PAD_X + col * chW,
      y: BODY_TOP + (row - firstRow) * LINE_H,
    }
  }

  private drawCaret(ctx: CanvasRenderingContext2D, x: number, y: number) {
    ctx.font = MONO
    const chW = ctx.measureText('M').width
    ctx.fillStyle = COLOR.cursor
    ctx.fillRect(x, y - 4, chW * 0.92, FONT_PX + 12)
  }

  private drawFooter(ctx: CanvasRenderingContext2D, chars: number, row: number, col: number) {
    ctx.fillStyle = COLOR.chromeBg
    ctx.fillRect(0, H - FOOTER_H, W, FOOTER_H)
    ctx.fillStyle = COLOR.chromeRule
    ctx.fillRect(0, H - FOOTER_H, W, 2)

    ctx.font = CHROME_FONT
    ctx.textBaseline = 'middle'
    const y = H - FOOTER_H / 2 + 2

    ctx.fillStyle = COLOR.accent
    ctx.textAlign = 'left'
    ctx.fillText('-- INSERT --', CHROME_X, y)

    const words = chars === 0 ? 0 : this.lines.join('\n').slice(0, chars).trim().split(/\s+/).filter(Boolean).length
    ctx.fillStyle = COLOR.dim
    ctx.textAlign = 'right'
    ctx.fillText(`${words} words    ${row + 1}:${col + 1}`, W - CHROME_X, y)
    ctx.textAlign = 'left'
  }

  dispose() {
    this.texture.dispose()
  }
}
