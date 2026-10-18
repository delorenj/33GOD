// Render .excalidraw scenes to PNG with Excalidraw's own exporter.
//
//   node render.mjs <in.excalidraw> <out.png> [--scale 2] [--dark] [--padding 48]
//
// Loads @excalidraw/excalidraw in headless Chromium so fonts, arrowheads and
// text measurement match what users see on excalidraw.com and draw.delo.sh.
import { chromium } from "playwright";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { homedir } from "node:os";

const VERSION = "0.18.0";
const args = process.argv.slice(2);
const flag = (name, dflt) => {
  const i = args.indexOf(name);
  if (i === -1) return dflt;
  const v = args[i + 1];
  args.splice(i, 2);
  return v;
};
const dark = args.includes("--dark");
if (dark) args.splice(args.indexOf("--dark"), 1);
const scale = Number(flag("--scale", "2"));
const padding = Number(flag("--padding", "48"));
const [input, output] = args;
if (!input || !output) {
  console.error("usage: node render.mjs <in.excalidraw> <out.png> [--scale 2] [--dark] [--padding 48]");
  process.exit(2);
}

const candidates = [
  process.env.CHROMIUM_PATH,
  `${homedir()}/.cache/ms-playwright/chromium-1243/chrome-linux/chrome`,
  `${homedir()}/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome`,
  "/usr/bin/chromium-browser",
].filter(Boolean);
const executablePath = candidates.find((p) => existsSync(p));

const scene = JSON.parse(readFileSync(input, "utf8"));
const browser = await chromium.launch({ executablePath });
const page = await browser.newPage();
page.on("console", (m) => m.type() === "error" && console.error("[page]", m.text()));
await page.setContent(`<!doctype html><html><head><meta charset="utf-8">
<script>window.EXCALIDRAW_ASSET_PATH = "https://unpkg.com/@excalidraw/excalidraw@${VERSION}/dist/prod/";</script>
<script type="importmap">{"imports":{
  "react":"https://esm.sh/react@19.0.0",
  "react/jsx-runtime":"https://esm.sh/react@19.0.0/jsx-runtime",
  "react-dom":"https://esm.sh/react-dom@19.0.0",
  "react-dom/client":"https://esm.sh/react-dom@19.0.0/client"
}}</script>
<script type="module">
  import * as X from "https://esm.sh/@excalidraw/excalidraw@${VERSION}?external=react,react-dom";
  window.X = X;
  window.ready = true;
</script></head><body></body></html>`);
await page.waitForFunction(() => window.ready === true, null, { timeout: 120000 });

const b64 = await page.evaluate(
  async ({ scene, scale, dark, padding }) => {
    const { exportToBlob, restoreElements } = window.X;
    const elements = restoreElements(scene.elements, null, { refreshDimensions: true });
    const blob = await exportToBlob({
      elements,
      appState: {
        ...(scene.appState || {}),
        exportBackground: true,
        exportWithDarkMode: dark,
        exportScale: scale,
      },
      files: scene.files || {},
      exportPadding: padding,
      getDimensions: (w, h) => ({ width: w * scale, height: h * scale, scale }),
      mimeType: "image/png",
    });
    const buf = new Uint8Array(await blob.arrayBuffer());
    let s = "";
    for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode(...buf.subarray(i, i + 0x8000));
    return btoa(s);
  },
  { scene, scale, dark, padding },
);
writeFileSync(output, Buffer.from(b64, "base64"));
await browser.close();
console.log(`wrote ${output}`);
