// SPDX-License-Identifier: Apache-2.0
// GripsterViewer — interactive Three.js viewer for the assembled Gripster GLB.
//
// Responsibilities:
//   • progressive load: instant light proxy → swap to the full-res master
//   • orbit + auto-spin (respects prefers-reduced-motion), reset, fullscreen
//   • explode / reassemble by translating named "mover" groups along authored
//     offset vectors (public/models/explode.json — computed in model space)
//   • hotspot pins that track named nodes in 3D and open component cards
//
// Coordinate note: explode.json offsets are in the same space as the GLB node
// positions (the exporter bakes world coords into vertices, leaving node
// transforms at identity), so offsets apply directly to node.position.

import {
  ACESFilmicToneMapping,
  Box3,
  Color,
  Group,
  MathUtils,
  Object3D,
  PerspectiveCamera,
  PMREMGenerator,
  Scene,
  SRGBColorSpace,
  Sphere,
  Vector2,
  Vector3,
  WebGLRenderer,
} from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js'

export interface ExplodeManifest {
  axes: { thick: number; height: number; width: number }
  extent: number[]
  center: number[]
  step: number
  movers: Record<string, { offset: number[]; nodes: string[] }>
}

export interface Hotspot {
  id: string
  title: string
  oneLiner: string
  blurb: string
  href: string
  docLabel: string
  anchorNodes: string[]
}

interface Mover {
  offset: Vector3
  parts: { obj: Object3D; base: Vector3 }[]
}

interface Pin {
  data: Hotspot
  objs: Object3D[]
  el: HTMLButtonElement
  world: Vector3
  occluded: boolean
}

const THEME_BG: Record<'light' | 'dark', number> = {
  light: 0xeef1f4,
  dark: 0x0f1216,
}

export interface ViewerOptions {
  container: HTMLElement
  proxyUrl: string
  mainUrl: string
  explodeUrl: string
  hotspotsUrl: string
  theme?: 'light' | 'dark'
  onHotspotOpen?: (h: Hotspot | null) => void
  onReady?: () => void
}

export class GripsterViewer {
  private container: HTMLElement
  private renderer: WebGLRenderer
  private scene: Scene
  private camera: PerspectiveCamera
  private controls: OrbitControls
  private overlay: HTMLDivElement

  private model: Group | null = null
  private explode: ExplodeManifest | null = null
  private hotspots: Hotspot[] = []
  private movers: Mover[] = []
  private pins: Pin[] = []
  private activePin: Pin | null = null

  private explodeT = 0
  private hotspotsVisible = true
  private theme: 'light' | 'dark'
  private reducedMotion: boolean

  private home = { pos: new Vector3(), target: new Vector3() }
  private modelCenter = new Vector3()
  private modelRadius = 1
  private tmpBox = new Box3()
  private tmpV = new Vector3()
  private viewDir = new Vector3()
  private ndc = new Vector3()
  private opts: ViewerOptions
  private disposed = false
  private needsRender = true // render-on-demand: only draw when something changed
  private pinsDirty = true // recompute pin world anchors (explode/model changed)
  private readyFired = false
  private framed = false

  constructor(opts: ViewerOptions) {
    this.opts = opts
    this.container = opts.container
    this.theme = opts.theme ?? 'light'
    this.reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    this.renderer = new WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' })
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.outputColorSpace = SRGBColorSpace
    this.renderer.toneMapping = ACESFilmicToneMapping
    this.renderer.toneMappingExposure = 1.05
    this.renderer.domElement.classList.add('gv-canvas')
    this.container.appendChild(this.renderer.domElement)

    this.scene = new Scene()
    this.scene.background = new Color(THEME_BG[this.theme])

    const pmrem = new PMREMGenerator(this.renderer)
    this.scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
    pmrem.dispose() // env map is baked into a texture; the generator can go

    this.camera = new PerspectiveCamera(42, 1, 0.1, 20000)
    this.camera.position.set(0, 0, 500)

    this.controls = new OrbitControls(this.camera, this.renderer.domElement)
    this.controls.enableDamping = true
    this.controls.dampingFactor = 0.08
    this.controls.autoRotate = !this.reducedMotion
    this.controls.autoRotateSpeed = 0.9
    this.controls.enablePan = false
    this.controls.minDistance = 60
    this.controls.maxDistance = 2000
    // stop auto-spin as soon as the user grabs the model
    this.controls.addEventListener('start', () => {
      if (this.controls.autoRotate) {
        this.controls.autoRotate = false
        this.container.dispatchEvent(new CustomEvent('gv:spin', { detail: false }))
      }
    })
    // any camera change (drag, wheel, programmatic) → schedule a redraw
    this.controls.addEventListener('change', () => this.requestRender())

    this.overlay = document.createElement('div')
    this.overlay.className = 'gv-overlay'
    this.container.appendChild(this.overlay)

    this.resize()
    const ro = new ResizeObserver(() => this.resize())
    ro.observe(this.container)

    this.renderer.setAnimationLoop(() => this.tick())
    void this.load()
  }

  // ---- loading (progressive) -------------------------------------------------
  private makeLoader(): GLTFLoader {
    const loader = new GLTFLoader()
    loader.setMeshoptDecoder(MeshoptDecoder)
    return loader
  }

  private async load() {
    const loader = this.makeLoader()
    const [explode, hotspots] = await Promise.all([
      fetch(this.opts.explodeUrl).then((r) => r.json() as Promise<ExplodeManifest>),
      fetch(this.opts.hotspotsUrl).then((r) => r.json() as Promise<Hotspot[]>),
    ])
    if (this.disposed) return
    this.explode = explode
    this.hotspots = hotspots

    // 1) proxy first — instant
    try {
      const proxy = await loader.loadAsync(this.opts.proxyUrl)
      if (this.disposed) return
      this.setModel(proxy.scene)
    } catch (err) {
      console.error('[viewer] proxy load failed', err)
    }

    // 2) full-res master — swap in when ready
    try {
      const full = await loader.loadAsync(this.opts.mainUrl)
      if (this.disposed) return
      this.setModel(full.scene)
    } catch (err) {
      console.error('[viewer] main load failed', err)
    }
  }

  private setModel(root: Group) {
    const prev = this.model
    root.name = 'gripster-model'
    this.scene.add(root)
    this.model = root

    this.bindMovers(root)
    this.bindPins(root)
    this.applyExplode(this.explodeT)
    this.pinsDirty = true
    this.requestRender()

    // frame + signal ready on the FIRST model shown, whichever wins the race
    // (so a failed proxy but successful master still frames + dismisses loading)
    if (!this.framed) {
      this.frameCamera(root)
      this.framed = true
    }
    if (prev) {
      this.scene.remove(prev)
      prev.traverse((o: any) => {
        o.geometry?.dispose?.()
        const m = o.material
        if (Array.isArray(m)) m.forEach((mm) => mm.dispose?.())
        else m?.dispose?.()
      })
    }
    if (!this.readyFired) {
      this.readyFired = true
      this.opts.onReady?.()
    }
  }

  private bindMovers(root: Group) {
    this.movers = []
    if (!this.explode) return
    for (const key of Object.keys(this.explode.movers)) {
      const spec = this.explode.movers[key]
      const parts: Mover['parts'] = []
      for (const name of spec.nodes) {
        const obj = root.getObjectByName(name)
        if (obj) parts.push({ obj, base: obj.position.clone() })
      }
      if (parts.length) {
        this.movers.push({ offset: new Vector3().fromArray(spec.offset), parts })
      }
    }
  }

  private applyExplode(t: number) {
    for (const mv of this.movers) {
      for (const p of mv.parts) {
        p.obj.position.copy(p.base).addScaledVector(mv.offset, t)
      }
    }
  }

  // ---- camera framing --------------------------------------------------------
  private frameCamera(root: Object3D) {
    this.tmpBox.setFromObject(root)
    const sphere = this.tmpBox.getBoundingSphere(new Sphere())
    const center = sphere.center
    const r = sphere.radius
    this.modelCenter.copy(center)
    this.modelRadius = r
    const fov = MathUtils.degToRad(this.camera.fov)
    const dist = (r / Math.sin(fov / 2)) * 1.18
    // 3/4 hero angle: mostly along +Z (face normal), a little up and to the right
    const dir = new Vector3(0.32, 0.16, 1).normalize()
    this.camera.position.copy(center).addScaledVector(dir, dist)
    this.camera.near = Math.max(r / 100, 0.1)
    this.camera.far = r * 20
    this.camera.updateProjectionMatrix()
    this.controls.target.copy(center)
    this.controls.minDistance = r * 0.6
    this.controls.maxDistance = r * 6
    this.controls.update()
    this.home.pos.copy(this.camera.position)
    this.home.target.copy(center)
  }

  // ---- hotspots --------------------------------------------------------------
  private bindPins(root: Group) {
    const activeId = this.activePin?.data.id // survive the proxy→master swap
    for (const p of this.pins) p.el.remove()
    this.pins = []
    this.activePin = null
    for (const data of this.hotspots) {
      const objs = data.anchorNodes.map((n) => root.getObjectByName(n)).filter(Boolean) as Object3D[]
      if (!objs.length) continue
      // the anchor's own meshes — excluded from the occlusion test so a deep
      // part (e.g. the phone) never dims its own pin.
      const el = document.createElement('button')
      el.className = 'gv-pin'
      el.type = 'button'
      el.setAttribute('aria-label', data.title)
      el.innerHTML = '<span class="gv-pin-dot"></span>'
      el.addEventListener('click', (e) => {
        e.stopPropagation()
        this.openPin(this.pins.find((pp) => pp.el === el) ?? null)
      })
      this.overlay.appendChild(el)
      this.pins.push({ data, objs, el, world: new Vector3(), occluded: false })
    }
    if (activeId) {
      const restored = this.pins.find((p) => p.data.id === activeId) ?? null
      if (restored) {
        this.activePin = restored
        restored.el.classList.add('is-active')
      }
    }
    this.applyPinVisibility()
  }

  private openPin(pin: Pin | null) {
    this.activePin = pin
    for (const p of this.pins) p.el.classList.toggle('is-active', p === pin)
    this.opts.onHotspotOpen?.(pin?.data ?? null)
    this.requestRender()
  }

  closeHotspot() {
    this.openPin(null)
  }

  private updatePins() {
    if (!this.pins.length) return
    const w = this.container.clientWidth
    const h = this.container.clientHeight

    // Recompute anchor world centres only when the model or explode changed —
    // not every frame. Camera orbit doesn't move the anchors, just re-projects.
    if (this.pinsDirty) {
      this.scene.updateMatrixWorld(true) // parts just moved (explode/load)
      for (const pin of this.pins) {
        this.tmpBox.makeEmpty()
        for (const o of pin.objs) this.tmpBox.expandByObject(o)
        this.tmpBox.getCenter(pin.world)
      }
      this.pinsDirty = false
    }

    this.camera.updateMatrixWorld()
    // Cheap occlusion (no raycast): dim pins on the far hemisphere of the model.
    // Disabled once exploded, since the explode separates parts along the view
    // axis and every pin is then plainly visible.
    const occlusionOn = this.explodeT < 0.06
    this.viewDir.copy(this.modelCenter).sub(this.camera.position).normalize()
    const backThresh = this.modelRadius * 0.12

    for (const pin of this.pins) {
      this.ndc.copy(pin.world).project(this.camera)
      const behind = this.ndc.z > 1
      const x = (this.ndc.x * 0.5 + 0.5) * w
      const y = (-this.ndc.y * 0.5 + 0.5) * h
      const onScreen = !behind && this.ndc.x >= -1.05 && this.ndc.x <= 1.05 && this.ndc.y >= -1.05 && this.ndc.y <= 1.05

      pin.occluded =
        occlusionOn && this.tmpV.copy(pin.world).sub(this.modelCenter).dot(this.viewDir) > backThresh

      const show = this.hotspotsVisible && onScreen
      pin.el.style.display = show ? 'block' : 'none'
      if (show) {
        pin.el.style.transform = `translate(-50%, -50%) translate(${x}px, ${y}px)`
        pin.el.classList.toggle('is-occluded', pin.occluded && pin !== this.activePin)
        pin.el.style.zIndex = String(1000 - Math.round((this.ndc.z + 1) * 400))
      }
    }
  }

  private applyPinVisibility() {
    this.overlay.classList.toggle('gv-overlay--hidden', !this.hotspotsVisible)
  }

  /** Ask for a single redraw on the next frame (render-on-demand). */
  private requestRender() {
    this.needsRender = true
  }

  // ---- public controls -------------------------------------------------------
  setExplode(t: number) {
    this.explodeT = MathUtils.clamp(t, 0, 1)
    this.applyExplode(this.explodeT)
    this.pinsDirty = true // anchors moved
    this.requestRender()
  }

  setSpin(on: boolean) {
    this.controls.autoRotate = on && !this.reducedMotion
    this.requestRender()
  }

  isSpinning() {
    return this.controls.autoRotate
  }

  prefersReducedMotion() {
    return this.reducedMotion
  }

  setHotspotsVisible(on: boolean) {
    this.hotspotsVisible = on
    this.applyPinVisibility()
    if (!on) this.closeHotspot()
    this.requestRender()
  }

  setTheme(theme: 'light' | 'dark') {
    this.theme = theme
    ;(this.scene.background as Color).setHex(THEME_BG[theme])
    this.requestRender()
  }

  resetView() {
    // quick eased return to the hero framing
    const fromP = this.camera.position.clone()
    const fromT = this.controls.target.clone()
    const start = performance.now()
    const dur = 520
    const ease = (x: number) => 1 - Math.pow(1 - x, 3)
    const step = () => {
      if (this.disposed) return
      const k = ease(Math.min((performance.now() - start) / dur, 1))
      this.camera.position.lerpVectors(fromP, this.home.pos, k)
      this.controls.target.lerpVectors(fromT, this.home.target, k)
      this.controls.update()
      this.requestRender()
      if (k < 1) requestAnimationFrame(step)
    }
    step()
  }

  toggleFullscreen() {
    if (document.fullscreenElement) document.exitFullscreen()
    else this.container.requestFullscreen?.()
  }

  // ---- loop ------------------------------------------------------------------
  private resize() {
    const w = this.container.clientWidth || 1
    const h = this.container.clientHeight || 1
    this.renderer.setSize(w, h, false)
    this.camera.aspect = w / h
    this.camera.updateProjectionMatrix()
    this.applyFramingOffset(w, h)
    this.requestRender()
  }

  // On a wide (side-by-side) layout the hero copy sits over the left of the
  // canvas; push the model into the empty space on the right with a frustum
  // offset (doesn't move the orbit pivot, so it stays put while spinning).
  private applyFramingOffset(w: number, h: number) {
    const leftPanel = Math.min(w * 0.5, 592) // hero-copy column width (max-width 34rem + pad)
    const shift = w >= 860 ? Math.min(leftPanel * 0.5, w * 0.2) : 0
    if (shift > 1) this.camera.setViewOffset(w, h, -shift, 0, w, h)
    else this.camera.clearViewOffset()
  }

  // Render-on-demand: OrbitControls.update() returns true while the camera is
  // moving (drag, damping, auto-rotate); otherwise we only draw when something
  // asked for it. Idle frames cost nothing — matching glb-viewer-core.
  private tick() {
    if (this.disposed) return
    const moved = this.controls.update()
    if (moved || this.needsRender) {
      this.needsRender = false
      this.updatePins()
      this.renderer.render(this.scene, this.camera)
    }
  }

  dispose() {
    this.disposed = true
    this.renderer.setAnimationLoop(null)
    this.controls.dispose()
    this.renderer.dispose()
    this.renderer.domElement.remove()
    this.overlay.remove()
  }
}
