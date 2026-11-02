import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { fontCss } from "../lib/fonts";
import { textShadow } from "../lib/anim";
import type { Brand, CaptionStyle, Safe, Word } from "../types";

type Page = { words: Word[]; start: number; end: number };

export function buildPages(words: Word[], cs: CaptionStyle): Page[] {
  const maxWords = cs.words_per_line ?? 3;
  const maxChars = cs.max_chars ?? 18;
  const pages: Page[] = [];
  let cur: Word[] = [];
  const flush = () => {
    if (cur.length) pages.push({ words: cur, start: cur[0].start, end: cur[cur.length - 1].end });
    cur = [];
  };
  for (let i = 0; i < words.length; i++) {
    const w = words[i];
    const prev = cur[cur.length - 1];
    const chars = cur.reduce((n, x) => n + x.text.length + 1, 0) + w.text.length;
    if (cur.length && (cur.length >= maxWords || chars > maxChars || (prev && w.start - prev.end > 0.6))) flush();
    cur.push(w);
    if (/[.!?…]$/.test(w.text)) flush();
  }
  flush();
  // cada página fica na tela até a próxima começar (máx. +0.6s de folga)
  for (let i = 0; i < pages.length; i++) {
    const next = pages[i + 1];
    pages[i].end = next ? Math.min(next.start, pages[i].end + 0.6) : pages[i].end + 0.4;
  }
  return pages;
}

const clean = (t: string, strip: boolean) => (strip ? t.replace(/[.,;:!?…]+$/g, "") : t);

export const Captions: React.FC<{ cs: CaptionStyle; brand: Brand; safe: Safe }> = ({ cs, brand, safe }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const t = frame / fps;
  const pages = React.useMemo(() => buildPages(cs.words || [], cs), [cs]);
  const page = pages.find((p) => t >= p.start && t < p.end);
  if (!page || cs.enabled === false) return null;

  const style = cs.style || "pop";
  const reveal = cs.reveal || (style === "typewriter" ? "word" : "page");
  const k = W / 1080;
  const fontSize = (cs.size ?? 0.075) * W;
  const color = cs.color || brand.colors.text || "#fff";
  const hl = cs.highlight_color || brand.colors.accent || "#FFD400";
  const boxColor = cs.box_color || brand.colors.accent || "#FFD400";
  const stroke = (cs.stroke ?? 6) * k;
  const strokeColor = cs.stroke_color || brand.colors.caption_stroke || "#000";
  const strip = (cs as any).strip_punctuation !== false;
  const pos = Math.min(1 - safe.bottom - 0.06, Math.max(safe.top + 0.06, cs.position ?? 0.66));
  const anim = cs.animation || "pop";
  const pf = Math.round((t - page.start) * fps);

  let enter = 1;
  let ty = 0;
  let opacity = 1;
  if (anim === "pop") enter = spring({ frame: pf, fps, config: { damping: 11, stiffness: 260, mass: 0.5 } });
  if (anim === "slide") ty = interpolate(pf, [0, 5], [30 * k, 0], { extrapolateRight: "clamp" });
  if (anim === "fade" || anim === "slide") opacity = interpolate(pf, [0, 4], [0, 1], { extrapolateRight: "clamp" });
  const scale = anim === "pop" ? 0.7 + 0.3 * enter : 1;

  const activeEmoji = page.words.find((w) => w.emoji && t >= w.start && t < w.end + 0.4)?.emoji;

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: W * safe.left,
          right: W * safe.right,
          top: H * pos,
          transform: `translateY(-50%) translateY(${ty}px) scale(${scale})`,
          opacity,
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          alignItems: "center",
          gap: `${fontSize * 0.12}px ${fontSize * 0.28}px`,
          textAlign: "center",
          lineHeight: 1.08,
          ...fontCss(brand, cs.font || "caption"),
          ...(cs.weight ? { fontWeight: cs.weight } : {}),
          ...(cs.tracking ? { letterSpacing: cs.tracking } : {}),
          fontSize,
          textTransform: cs.uppercase === false ? "none" : "uppercase",
        }}
      >
        {activeEmoji ? (
          <div
            style={{
              position: "absolute",
              bottom: "100%",
              left: 0,
              right: 0,
              textAlign: "center",
              fontSize: fontSize * 1.4,
              transform: `scale(${spring({ frame: pf, fps, config: { damping: 9 } })})`,
            }}
          >
            {activeEmoji}
          </div>
        ) : null}
        {cs.background ? (
          <div
            style={{
              position: "absolute",
              inset: `${-fontSize * 0.25}px ${-fontSize * 0.1}px`,
              background: cs.background,
              borderRadius: brand.radius * k,
              zIndex: -1,
            }}
          />
        ) : null}
        {page.words.map((w, i) => {
          const spoken = t >= w.start;
          const active = t >= w.start && t < (page.words[i + 1]?.start ?? page.end);
          if (reveal === "word" && !spoken) return null;
          let c = color;
          if (w.emphasis) c = w.color || brand.colors.accent2 || hl;
          if (style === "karaoke" && spoken) c = w.emphasis ? c : hl;
          if (style === "pop" && active) c = w.emphasis ? c : hl;
          const isBox = style === "box" && active;
          const wf = Math.round((t - w.start) * fps);
          const wordPop =
            reveal === "word" ? spring({ frame: wf, fps, config: { damping: 10, stiffness: 300, mass: 0.4 } }) : 1;
          const emph = w.emphasis ? cs.emphasis_scale ?? 1.15 : 1;
          const activeScale = style === "pop" && active ? 1.05 : 1;
          return (
            <span
              key={i}
              style={{
                display: "inline-block",
                color: isBox ? brand.colors.text_dark || "#111" : c,
                background: isBox ? boxColor : "transparent",
                fontSize: fontSize * emph,
                padding: `0 ${fontSize * 0.12}px`,
                margin: `0 ${-fontSize * 0.12}px`,
                borderRadius: isBox ? brand.radius * 0.6 * k : 0,
                textShadow: isBox ? "none" : textShadow(stroke, strokeColor, cs.shadow !== false),
                transform: `scale(${(0.6 + 0.4 * wordPop) * activeScale})`,
              }}
            >
              {clean(w.text, strip)}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
