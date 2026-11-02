import { continueRender, delayRender, staticFile } from "remotion";
import type { Brand } from "../types";

const loaded = new Set<string>();

export function loadBrandFonts(brand: Brand) {
  const files = brand.fonts.files || [];
  const pending = files.filter((f) => !loaded.has(f.file));
  if (pending.length === 0 || typeof document === "undefined") return;
  const handle = delayRender("carregando fontes da marca");
  Promise.all(
    pending.map(async (f) => {
      loaded.add(f.file);
      const face = new FontFace(f.family, `url(${staticFile(f.file)})`, {
        weight: String(f.weight),
        style: f.style || "normal",
      });
      await face.load();
      (document.fonts as any).add(face);
    }),
  )
    .catch((e) => console.error("falha ao carregar fonte", e))
    .finally(() => continueRender(handle));
}

export function fontCss(brand: Brand, which: "title" | "caption" | "body") {
  const f = brand.fonts[which] || brand.fonts.body;
  return { fontFamily: `'${f.family}', 'Montserrat', 'Inter', sans-serif`, fontWeight: f.weight };
}
