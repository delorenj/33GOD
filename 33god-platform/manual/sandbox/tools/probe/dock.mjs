// Real-pointer regression probe for the Factory docks (src/ui/dock.tsx): drag, double-click, button and W cycles,
// including the short 'drag it down to the bar' pull that used to leave the waterfall stuck open at its minimum.
// Needs a real GL context, so run headed under Xvfb from a dir with playwright installed:
//   xvfb-run -a -s '-screen 0 1920x1080x24' node tools/probe/dock.mjs [url]
// Every 'after … (fold)' line must read folded:true, every unfold line folded:false.
import { chromium } from 'playwright'
const url = process.argv[2] ?? 'https://manual.delo.sh/sandbox/?waybill=waybills/claude-readme.waybill.json&nofx'
const b = await chromium.launch({ headless: false, args: ['--enable-webgl', '--use-gl=angle', '--use-angle=swiftshader-webgl', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] })
const p = await b.newPage({ viewport: { width: 1600, height: 900 } })
p.on('pageerror', (e) => console.log('pageerror', e.message))
await p.goto(url)
await p.waitForSelector('.dock-grip.bottom', { timeout: 30000 })
const st = async (tag) => {
  const r = await p.evaluate(() => {
    const el = document.querySelector('.wb-bottom'), g = document.querySelector('.dock-grip.bottom')
    const gb = g.getBoundingClientRect()
    return { h: Math.round(el.getBoundingClientRect().height), folded: el.classList.contains('folded'), gripY: Math.round(gb.top + gb.height / 2), gripOn: g.classList.contains('on'), ls: localStorage.getItem('manual.dock.waterfall') }
  })
  console.log(tag.padEnd(28), JSON.stringify(r))
  return r
}
const drag = async (dy, tag) => {
  const r = await st('before ' + tag)
  await p.mouse.move(800, r.gripY)
  await p.mouse.down()
  for (let i = 1; i <= 12; i++) await p.mouse.move(800, r.gripY + (dy * i) / 12)
  await p.mouse.up()
  await p.waitForTimeout(150)
  return st('after ' + tag)
}
const dbl = async (tag) => { const r = await st('before ' + tag); await p.mouse.dblclick(800, r.gripY); await p.waitForTimeout(150); return st('after ' + tag) }

await st('start')
await drag(400, 'drag down (fold)')
await drag(-250, 'drag up (unfold)')
await drag(400, 'drag down (fold again)')
await drag(-250, 'drag up (unfold again)')
await dbl('dblclick (fold)')
await dbl('dblclick (unfold)')
await dbl('dblclick (fold again)')
await dbl('dblclick (unfold again)')
await p.click('.wb-wf-tog'); await st('button fold')
await drag(-250, 'drag up (unfold after button)')
await p.click('.wb-wf-tog'); await st('button fold again')
await p.click('.wb-wf-tog'); await st('button unfold')
await drag(400, 'drag down after button')
console.log('--- user-shaped cases (playing) ---')
await p.click('.wb-wf-tog'); await st('button unfold')
await p.click('.wb-play').catch(() => {}); await p.waitForTimeout(300)
await drag(-60, 'nudge up to 310')
await drag(220, 'drag down ~to the bottom bar')
await drag(-150, 'drag up 150 from folded')
await drag(140, 'drag down 140')
await p.keyboard.press('w'); await p.waitForTimeout(150); await st('W after drags')
await p.keyboard.press('w'); await p.waitForTimeout(150); await st('W again')
await b.close()
