import * as THREE from 'three'

const cache = new Map<string, THREE.CanvasTexture>()

function make(key: string, w: number, h: number, draw: (c: CanvasRenderingContext2D) => void) {
  const hit = cache.get(key)
  if (hit) return hit
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const c = canvas.getContext('2d')!
  draw(c)
  const tex = new THREE.CanvasTexture(canvas)
  tex.colorSpace = THREE.SRGBColorSpace
  tex.anisotropy = 8
  cache.set(key, tex)
  return tex
}

const INK = '#2a2418'
const HAND = '"Fredoka", "Nunito", system-ui, sans-serif'

function wrap(c: CanvasRenderingContext2D, text: string, x: number, y: number, maxW: number, lh: number) {
  const words = text.split(' ')
  let line = ''
  for (const w of words) {
    const test = line ? `${line} ${w}` : w
    if (c.measureText(test).width > maxW && line) {
      c.fillText(line, x, y)
      line = w
      y += lh
    } else line = test
  }
  c.fillText(line, x, y)
}

/** Face of a post-it: past-tense headline, and the small "from" corner when the note came through the dock. */
export function postItFace(headline: string, from: string | null) {
  return make(`post:${headline}:${from}`, 256, 256, (c) => {
    c.fillStyle = '#FFD84D'
    c.fillRect(0, 0, 256, 256)
    c.fillStyle = 'rgba(0,0,0,0.06)'
    c.fillRect(0, 0, 256, 34) // the gummed strip
    c.fillStyle = INK
    c.font = `600 44px ${HAND}`
    c.textBaseline = 'top'
    wrap(c, headline, 22, 62, 212, 50)
    if (from) {
      c.strokeStyle = 'rgba(42,36,24,0.55)'
      c.lineWidth = 3
      c.beginPath()
      c.moveTo(150, 256)
      c.lineTo(150, 206)
      c.lineTo(256, 206)
      c.stroke()
      c.font = `600 26px ${HAND}`
      c.fillText(from, 160, 218)
    } else {
      c.font = `500 22px ${HAND}`
      c.fillStyle = 'rgba(42,36,24,0.55)'
      c.fillText('no “from” corner', 22, 214)
    }
  })
}

/** Face of an envelope: an imperative, addressed to one kind of worker. Grey when no hatch takes it. */
export function envelopeFace(headline: string, orphan: boolean) {
  return make(`env:${headline}:${orphan}`, 320, 220, (c) => {
    c.fillStyle = orphan ? '#B9B4AA' : '#D8B07A'
    c.fillRect(0, 0, 320, 220)
    c.strokeStyle = 'rgba(42,36,24,0.35)'
    c.lineWidth = 4
    c.beginPath()
    c.moveTo(0, 0)
    c.lineTo(160, 110)
    c.lineTo(320, 0)
    c.stroke()
    c.fillStyle = 'rgba(255,255,255,0.75)'
    c.fillRect(70, 128, 180, 64)
    c.fillStyle = INK
    c.font = `600 26px ${HAND}`
    c.textAlign = 'center'
    c.textBaseline = 'middle'
    wrap(c, headline, 160, 148, 170, 28)
    c.strokeStyle = 'rgba(42,36,24,0.5)'
    c.lineWidth = 2
    c.strokeRect(268, 160, 40, 40) // signature box
  })
}

/** Big stencil letters painted on the floor of a domain: its real name, and what it is for. */
export function floorSign(text: string, sub: string, color = '#2563EB') {
  return make(`floor:${text}:${sub}:${color}`, 1024, 200, (c) => {
    c.clearRect(0, 0, 1024, 200)
    c.globalAlpha = 0.8
    c.fillStyle = color
    c.font = `700 96px ${HAND}`
    c.textBaseline = 'middle'
    c.fillText(text.toUpperCase(), 16, 70)
    c.globalAlpha = 0.6
    c.font = `600 50px ${HAND}`
    c.fillText(sub, 20, 160)
  })
}

/** An enamel sign with the warehouse word for a station: part of the world, never part of the UX. */
export function placeSign(text: string, color: string) {
  return make(`place:${text}:${color}`, 512, 128, (c) => {
    c.fillStyle = '#FBF5E6'
    c.fillRect(0, 0, 512, 128)
    c.fillStyle = color
    c.fillRect(0, 0, 512, 16)
    c.strokeStyle = '#2A2418'
    c.lineWidth = 6
    c.strokeRect(3, 3, 506, 122)
    c.fillStyle = '#2A2418'
    c.font = `700 56px ${HAND}`
    c.textAlign = 'center'
    c.textBaseline = 'middle'
    c.fillText(text.toUpperCase(), 256, 72, 480)
  })
}

export function clockFace() {
  return make('clockface', 256, 256, (c) => {
    c.fillStyle = '#FFF8EA'
    c.beginPath()
    c.arc(128, 128, 124, 0, Math.PI * 2)
    c.fill()
    c.fillStyle = INK
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2
      c.beginPath()
      c.arc(128 + Math.sin(a) * 100, 128 - Math.cos(a) * 100, i % 3 === 0 ? 9 : 5, 0, Math.PI * 2)
      c.fill()
    }
  })
}

export function clearTextureCache() {
  cache.forEach((t) => t.dispose())
  cache.clear()
}
