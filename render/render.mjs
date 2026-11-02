// Renderizador Remotion chamado pelo engine/render.py.
// Uso: node render/render.mjs job.json
// job.json = { publicDir, jobs: [{ props, out, stills?: [segundos] }], concurrency?, browserExecutable? }
import { bundle } from "@remotion/bundler";
import { renderMedia, renderStill, selectComposition } from "@remotion/renderer";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const job = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));

function findChrome() {
  if (job.browserExecutable) return job.browserExecutable;
  if (process.env.REMOTION_BROWSER) return process.env.REMOTION_BROWSER;
  const candidates = ["/opt/pw-browsers"];
  for (const root of candidates) {
    if (!fs.existsSync(root)) continue;
    for (const d of fs.readdirSync(root)) {
      if (!d.startsWith("chromium_headless_shell")) continue;
      const p = path.join(root, d, "chrome-headless-shell-linux64", "chrome-headless-shell");
      if (fs.existsSync(p)) return p;
    }
  }
  return null; // Remotion baixa o próprio headless shell
}

const log = (...a) => console.error("[render]", ...a);

const serveUrl = await bundle({
  entryPoint: path.join(here, "src", "index.ts"),
  publicDir: job.publicDir,
  onProgress: () => {},
});
const browserExecutable = findChrome();
const chromiumOptions = { gl: "swangle" };

for (const j of job.jobs) {
  const composition = await selectComposition({
    serveUrl,
    id: "Main",
    inputProps: j.props,
    browserExecutable,
    chromiumOptions,
  });
  if (j.stills && j.stills.length) {
    fs.mkdirSync(j.out, { recursive: true });
    for (const t of j.stills) {
      const frame = Math.min(composition.durationInFrames - 1, Math.max(0, Math.round(t * composition.fps)));
      const output = path.join(j.out, `${j.props.format}_${t.toFixed(2).padStart(6, "0")}s.jpg`);
      await renderStill({ composition, serveUrl, output, frame, inputProps: j.props, browserExecutable, chromiumOptions, imageFormat: "jpeg", jpegQuality: 85 });
      log("prévia", output);
    }
    continue;
  }
  let last = -1;
  await renderMedia({
    composition,
    serveUrl,
    codec: "h264",
    crf: 18,
    muted: true,
    outputLocation: j.out,
    inputProps: j.props,
    browserExecutable,
    chromiumOptions,
    concurrency: job.concurrency || null,
    onProgress: ({ progress }) => {
      const pct = Math.floor(progress * 10) * 10;
      if (pct !== last) {
        last = pct;
        log(`${j.props.format}: ${pct}%`);
      }
    },
  });
  log("ok", j.out);
}
