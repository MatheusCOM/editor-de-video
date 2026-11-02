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

export type FontRole = "title" | "caption" | "body" | "mono";

export function fontCss(brand: Brand, which: FontRole): { fontFamily: string; fontWeight: number; letterSpacing?: string } {
  const f = brand.fonts[which] || brand.fonts.body;
  const fallback = which === "mono" ? "monospace" : "sans-serif";
  const css: { fontFamily: string; fontWeight: number; letterSpacing?: string } = {
    fontFamily: `'${f.family}', ${fallback}`,
    fontWeight: f.weight,
  };
  if (f.tracking) css.letterSpacing = f.tracking;
  return css;
}
