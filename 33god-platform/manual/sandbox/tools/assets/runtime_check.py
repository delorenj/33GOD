"""Browser check for the Factory asset runtime (Playwright, chromium). Proves the pipeline end to end on a served build.

    python3 tools/assets/runtime_check.py http://localhost:4801/sandbox/ /tmp/factory-runtime [--id fixture]

With --id fixture (the default) it opens ?at=fixture&forge&fixture, waits for window.__factoryForge.ready, prints
info(), poses each clip, injects a visit and screenshots the cycle, then shoots the plain floor. Exit 1 on any
console error or a failed step. Serve a temp build first: npx vite build --outDir /tmp/x && npx vite preview --outDir /tmp/x
"""
import argparse
import asyncio
import json
import os
import sys

from playwright.async_api import async_playwright

GL_ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
NOISE = ('THREE.Clock: This module has been deprecated', 'PCFSoftShadowMap has been removed', 'GPU stall due to ReadPixels', 'Automatic fallback to software WebGL')


async def run(base: str, out: str, aid: str, extra: str) -> int:
    os.makedirs(out, exist_ok=True)
    problems: list[str] = []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=GL_ARGS)

        async def page():
            pg = await b.new_page(viewport={'width': 1280, 'height': 800})
            log: list[str] = []
            pg.on('console', lambda m: log.append(f'{m.type}: {m.text}') if m.type in ('error', 'warning') and not any(n in m.text for n in NOISE) else None)
            pg.on('pageerror', lambda e: log.append(f'pageerror: {e}'))
            return pg, log

        fixture = '&fixture' if aid == 'fixture' else ''
        pg, log = await page()
        await pg.goto(f'{base}?at={aid}&forge{fixture}&spin=0&angle=0{extra}')
        try:
            await pg.evaluate('() => window.__factoryForge.ready', )
        except Exception as e:  # noqa: BLE001
            problems.append(f'ready rejected: {e}')
        info = await pg.evaluate(f'() => window.__factoryForge && window.__factoryForge.info({json.dumps(aid)})')
        print('info', json.dumps(info))
        if not info or len(info.get('clips', [])) < 4 or len(info.get('sockets', [])) < 3:
            problems.append(f'info incomplete: {info}')
        for clip, t in (('idle', 0.0), ('accept', 0.5), ('work', 0.35), ('emit', 0.35)):
            await pg.evaluate(f'() => window.__factoryForge.pose({json.dumps(aid)}, {json.dumps(clip)}, {t})')
            await pg.wait_for_timeout(400)
            await pg.screenshot(path=f'{out}/pose-{clip}.png')
        await pg.evaluate('() => window.__factoryForge.release()')
        await pg.evaluate(f'() => window.__factoryForge.visit({json.dumps(aid)})')
        t0 = 0
        for t in (150, 600, 1300, 2200, 3000, 3600, 4600):
            await pg.wait_for_timeout(t - t0)
            t0 = t
            await pg.screenshot(path=f'{out}/cycle-{t:04d}ms.png')
        # a queue: four visits at once never skip Accept, and the queue drains
        for _ in range(4):
            await pg.evaluate(f'() => window.__factoryForge.visit({json.dumps(aid)})')
        await pg.wait_for_timeout(5000)
        await pg.screenshot(path=f'{out}/queue-after-5s.png')
        print('stage console:', json.dumps(log, indent=1))
        problems += [f'stage: {m}' for m in log if m.startswith(('error', 'pageerror'))]
        await pg.close()

        pg, log = await page()
        await pg.goto(f'{base}?walk&nofx{extra}')
        await pg.wait_for_timeout(9000)
        await pg.screenshot(path=f'{out}/floor-overview.png')
        print('floor console:', json.dumps(log, indent=1))
        problems += [f'floor: {m}' for m in log if m.startswith(('error', 'pageerror'))]
        await pg.close()
        await b.close()
    for pr in problems:
        print('PROBLEM', pr)
    return 1 if problems else 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('base')
    ap.add_argument('out')
    ap.add_argument('--id', default='fixture')
    ap.add_argument('--extra', default='', help='more query, e.g. "&nofx"')
    a = ap.parse_args()
    sys.exit(asyncio.run(run(a.base, a.out, a.id, a.extra)))
