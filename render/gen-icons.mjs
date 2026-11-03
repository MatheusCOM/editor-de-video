// Gera src/lib/icons.generated.json a partir do lucide-static: { nome: "<path pathLength=1 .../>..." }.
// Cada elemento ganha pathLength=1 para permitir a animação de "desenho" do traço.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const dir = path.join(here, "node_modules", "lucide-static", "icons");
const out = path.join(here, "src", "lib", "icons.generated.json");
const map = {};
for (const f of fs.readdirSync(dir)) {
  if (!f.endsWith(".svg")) continue;
  const svg = fs.readFileSync(path.join(dir, f), "utf8");
  const inner = svg.replace(/^[\s\S]*?<svg[^>]*>/, "").replace(/<\/svg>[\s\S]*$/, "").trim();
  map[f.replace(/\.svg$/, "")] = inner
    .replace(/<(path|circle|line|rect|polyline|polygon|ellipse)\b/g, '<$1 pathLength="1"')
    .replace(/\s+/g, " ");
}
fs.writeFileSync(out, JSON.stringify(map));
console.error(`[icones] ${Object.keys(map).length} ícones → ${path.relative(here, out)}`);
