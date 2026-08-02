// SPDX-License-Identifier: Apache-2.0
// build-content.mjs — turn the doc-grounded copy (src/content.json) + the
// explode manifest (public/models/explode.json) into public/models/hotspots.json:
// each hotspot resolved to the exact GLB node(s) its pin should track, plus a
// GitHub "read more" deep link derived from its source doc heading.
//
// The viewer computes a pin's world position from the union bbox of anchorNodes,
// so it follows the explode automatically (those nodes ARE the ones that move).

import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SITE = resolve(__dirname, '..')
const CONTENT = resolve(SITE, 'src/content.json')
const EXPLODE = resolve(SITE, 'public/models/explode.json')
const OUT = resolve(SITE, 'public/models/hotspots.json')

const BLOB = 'https://github.com/neuman/custom-thumb-keyboard/blob/main'

// hotspot id -> explicit component node(s) (else fall back to a whole mover)
const NODE_ANCHOR = {
  module: ['pcb_right__U1'],
  'nub-sensor': ['pcb_right__U2'],
  usb: ['pcb_right__J1'],
}
// hotspot id -> mover whose nodes the pin tracks (for part-level hotspots)
const MOVER_ANCHOR = {
  phone: 'phone',
  'nub-cap': 'nub_cap',
  clamp: 'back_right',
  battery: 'battery',
  bridge: 'flex',
  domes: 'keymat_right',
}

// GitHub heading slug (matches GitHub's anchor generation for these headings)
function slug(h) {
  return h.toLowerCase().replace(/[^\w\s-]/g, '').trim().replace(/\s/g, '-')
}

const content = JSON.parse(readFileSync(CONTENT, 'utf8'))
const explode = JSON.parse(readFileSync(EXPLODE, 'utf8'))

const missing = []
const known = new Set(Object.values(explode.movers).flatMap((m) => m.nodes))
const hotspots = content.hotspots.map((h) => {
  let anchorNodes = NODE_ANCHOR[h.id]
  if (!anchorNodes) {
    const mv = MOVER_ANCHOR[h.id]
    if (mv && !explode.movers[mv]) missing.push(`${h.id} → mover "${mv}" not in explode.json`)
    anchorNodes = explode.movers[mv]?.nodes ?? []
  }
  // an unmapped or empty-resolving hotspot would ship a pin with nowhere to anchor
  if (!anchorNodes.length) missing.push(`${h.id} → no anchor nodes resolved`)
  // verify every anchor node actually exists in the shipped model
  for (const n of anchorNodes) if (!known.has(n)) missing.push(`${h.id} → ${n} (not in model)`)

  const href = h.docHeading
    ? `${BLOB}/${h.docPath}#${slug(h.docHeading)}`
    : `${BLOB}/${h.docPath}`
  return {
    id: h.id,
    title: h.title,
    oneLiner: h.oneLiner,
    blurb: h.blurb,
    href,
    docLabel: h.docPath.replace(/^.*\//, ''),
    anchorNodes,
  }
})

if (missing.length) {
  console.error('ERROR: unresolved hotspot anchors — fix NODE_ANCHOR/MOVER_ANCHOR or the model:\n  ' + missing.join('\n  '))
  process.exit(1)
}

writeFileSync(OUT, JSON.stringify(hotspots, null, 1))
console.log(`wrote ${OUT}  (${hotspots.length} hotspots)`)
for (const h of hotspots) console.log(`   ${h.id.padEnd(12)} ${h.anchorNodes.length} node(s)  ${h.href}`)
