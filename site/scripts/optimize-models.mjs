// SPDX-License-Identifier: Apache-2.0
// optimize-models.mjs — turn hardware/cad/models/thumbdeck_web_raw.glb into the
// two GLBs the browser viewer streams, plus the authored explode manifest:
//
//   public/models/thumbdeck_web.glb    interactive master (simplify + meshopt)
//   public/models/thumbdeck_proxy.glb  instant light proxy (hard simplify, no textures)
//   public/models/explode.json         per-mover offset vectors + node lists (three-space)
//
// The explode vectors are computed HERE, in the same coordinate space three.js
// sees, from the pre-compression float positions. All node coordinates are read
// in "accessor space"; the viewer applies the offsets to the same nodes, so any
// root Y-up wrapper rotation the exporter added is applied identically to
// geometry and offsets and cancels out. Thickness = smallest global extent axis.

import { NodeIO } from '@gltf-transform/core'
import { ALL_EXTENSIONS } from '@gltf-transform/extensions'
import { dedup, weld, simplify, prune, quantize } from '@gltf-transform/functions'
import { meshopt } from '@gltf-transform/functions'
import { MeshoptDecoder, MeshoptEncoder, MeshoptSimplifier } from 'meshoptimizer'
import { writeFileSync, readFileSync, mkdirSync, statSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SITE = resolve(__dirname, '..')
const REPO = resolve(SITE, '..')
const RAW = resolve(REPO, 'hardware/cad/models/thumbdeck_web_raw.glb')
const OUT_DIR = resolve(SITE, 'public/models')
const OUT_MAIN = resolve(OUT_DIR, 'thumbdeck_web.glb')
const OUT_PROXY = resolve(OUT_DIR, 'thumbdeck_proxy.glb')
const OUT_EXPLODE = resolve(OUT_DIR, 'explode.json')
const SCREEN = resolve(REPO, 'hardware/cad/assets/screen_app.jpg') // phone-screen texture

await MeshoptDecoder.ready
await MeshoptEncoder.ready
await MeshoptSimplifier.ready

const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
  'meshopt.decoder': MeshoptDecoder,
  'meshopt.encoder': MeshoptEncoder,
})

const SINGLE = new Set([
  'back_left', 'back_right', 'bridge', 'gripper_left', 'gripper_right',
  'grip_lid_left', 'grip_lid_right', 'nub_spring', 'nub_cap',
  'keymat_left', 'keymat_right', 'battery', 'flex', 'power', 'magsafe_ring',
])
function moverOf(nodeName) {
  const base = nodeName.split('__')[0]
  return base // node names are "<mover>__<key>" or "<mover>__<i>" by construction
}

// Layer along the thin (thickness) axis: back (−) → front (+); matches the
// physical z-stack (back shells → boards → face lids/keymats → phone).
const LAYER = {
  back_left: -3, back_right: -3, screws: -2, battery: -2.4, flex: -1.8, power: -1.8,
  pcb_right: -1, pcb_left: -1, bridge: -0.5,
  grip_lid_left: 1, grip_lid_right: 1, nub_spring: 1.3,
  keymat_left: 2, keymat_right: 2, gripper_left: 2.3, gripper_right: 2.3,
  nub_cap: 2.6, magsafe_ring: 3, phone: 4,
}
const LEFT = new Set(['back_left', 'grip_lid_left', 'keymat_left', 'pcb_left', 'gripper_left'])
const RIGHT = new Set(['back_right', 'grip_lid_right', 'keymat_right', 'pcb_right', 'nub_spring', 'nub_cap', 'gripper_right'])

function perNodeBounds(doc) {
  const out = {}
  for (const node of doc.getRoot().listNodes()) {
    const mesh = node.getMesh()
    if (!mesh) continue
    const name = node.getName()
    if (!name) continue
    let mn = [Infinity, Infinity, Infinity]
    let mx = [-Infinity, -Infinity, -Infinity]
    for (const prim of mesh.listPrimitives()) {
      const pos = prim.getAttribute('POSITION')
      if (!pos) continue
      const a = [0, 0, 0]
      const b = [0, 0, 0]
      pos.getMin(a)
      pos.getMax(b)
      for (let i = 0; i < 3; i++) {
        mn[i] = Math.min(mn[i], a[i])
        mx[i] = Math.max(mx[i], b[i])
      }
    }
    const t = node.getTranslation()
    for (let i = 0; i < 3; i++) {
      mn[i] += t[i]
      mx[i] += t[i]
    }
    if (Number.isFinite(mn[0])) out[name] = { min: mn, max: mx }
  }
  return out
}

function computeExplode(doc) {
  const nb = perNodeBounds(doc)
  const movers = {}
  const gmin = [Infinity, Infinity, Infinity]
  const gmax = [-Infinity, -Infinity, -Infinity]
  for (const [name, bb] of Object.entries(nb)) {
    const mv = moverOf(name)
    const m = (movers[mv] ??= { nodes: [], min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] })
    m.nodes.push(name)
    for (let i = 0; i < 3; i++) {
      m.min[i] = Math.min(m.min[i], bb.min[i])
      m.max[i] = Math.max(m.max[i], bb.max[i])
      gmin[i] = Math.min(gmin[i], bb.min[i])
      gmax[i] = Math.max(gmax[i], bb.max[i])
    }
  }
  const ext = [gmax[0] - gmin[0], gmax[1] - gmin[1], gmax[2] - gmin[2]]
  const order = [0, 1, 2].sort((a, b) => ext[a] - ext[b])
  const thick = order[0]
  const height = order[1]
  const width = order[2]
  const center = [(gmin[0] + gmax[0]) / 2, (gmin[1] + gmax[1]) / 2, (gmin[2] + gmax[2]) / 2]
  const step = Math.max(ext[thick] * 1.15, 14)
  const fan = ext[width] * 0.14

  const result = {
    axes: { thick, height, width },
    extent: ext.map((v) => +v.toFixed(3)),
    center: center.map((v) => +v.toFixed(3)),
    step: +step.toFixed(3),
    movers: {},
  }
  for (const [mv, m] of Object.entries(movers)) {
    const off = [0, 0, 0]
    off[thick] = (LAYER[mv] ?? 0) * step
    if (LEFT.has(mv)) off[width] -= fan
    else if (RIGHT.has(mv)) off[width] += fan
    result.movers[mv] = {
      offset: off.map((v) => +v.toFixed(3)),
      nodes: m.nodes.sort(),
    }
  }
  return result
}

// Replace the phone's lockscreen texture (material "display") with the
// generated writing-app image, keeping the existing UVs. The screen is a
// glowing display, so BOTH the base-colour AND emissive channels carry it —
// swap both or the old lockscreen keeps glowing through.
function swapPhoneScreen(doc) {
  const disp = doc.getRoot().listMaterials().find((m) => m.getName() === 'display')
  if (!disp) {
    console.warn('  ! phone "display" material not found — screen not swapped')
    return
  }
  const bytes = new Uint8Array(readFileSync(SCREEN))
  let swapped = 0
  for (const tex of [disp.getBaseColorTexture(), disp.getEmissiveTexture()]) {
    if (tex) {
      tex.setImage(bytes).setMimeType('image/jpeg')
      swapped++
    }
  }
  console.log(`  swapped phone screen (${swapped} channel${swapped === 1 ? '' : 's'}) →`, SCREEN.replace(REPO + '/', ''))
}

async function buildMain() {
  const doc = await io.read(RAW)
  swapPhoneScreen(doc)
  await doc.transform(
    dedup(),
    weld(),
    simplify({ simplifier: MeshoptSimplifier, ratio: 0.6, error: 0.008 }),
    prune({ keepLeaves: true }),
  )
  const explode = computeExplode(doc) // floats, before quantize/compress
  await doc.transform(
    quantize({ quantizePosition: 14, quantizeNormal: 10, quantizeColor: 8 }),
    meshopt({ encoder: MeshoptEncoder, level: 'high' }),
  )
  await io.write(OUT_MAIN, doc)
  return explode
}

async function buildProxy() {
  const doc = await io.read(RAW)
  for (const tex of doc.getRoot().listTextures()) tex.dispose() // strip textures for weight
  await doc.transform(
    dedup(),
    weld(),
    simplify({ simplifier: MeshoptSimplifier, ratio: 0.22, error: 0.02 }),
    prune({ keepLeaves: true }),
    quantize({ quantizePosition: 12, quantizeNormal: 8, quantizeColor: 8 }),
    meshopt({ encoder: MeshoptEncoder, level: 'high' }),
  )
  await io.write(OUT_PROXY, doc)
}

const mb = (f) => (statSync(f).size / 1048576).toFixed(2) + ' MB'

mkdirSync(OUT_DIR, { recursive: true })
console.log('reading', RAW)
const explode = await buildMain()
await buildProxy()
writeFileSync(OUT_EXPLODE, JSON.stringify(explode, null, 1))

console.log('—'.repeat(48))
console.log('main   ', mb(OUT_MAIN))
console.log('proxy  ', mb(OUT_PROXY))
console.log('movers ', Object.keys(explode.movers).length, '→', Object.keys(explode.movers).sort().join(', '))
console.log('axes   ', JSON.stringify(explode.axes), 'extent', JSON.stringify(explode.extent))
for (const [mv, m] of Object.entries(explode.movers)) {
  console.log(`   ${mv.padEnd(14)} off=${JSON.stringify(m.offset)}  nodes=${m.nodes.length}`)
}
