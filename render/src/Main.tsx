import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { BRollClip } from "./components/BRoll";
import { Captions } from "./components/Captions";
import { customRegistry } from "./components/custom";
import {
  Arrow,
  Checklist,
  Counter,
  CTA,
  EmojiPop,
  Flash,
  ImageOverlay,
  LowerThird,
  Logo,
  type OverlayProps,
  Progress,
  TextPop,
  Title,
} from "./components/overlays";
import { VideoLayer } from "./components/VideoLayer";
import { loadBrandFonts } from "./lib/fonts";
import type { MainProps, Overlay } from "./types";

const registry: Record<string, React.FC<OverlayProps>> = {
  title: Title,
  text_pop: TextPop,
  lower_third: LowerThird,
  cta: CTA,
  emoji: EmojiPop,
  image: ImageOverlay,
  arrow: Arrow,
  checklist: Checklist,
  counter: Counter,
  logo: Logo,
  flash: Flash,
  ...customRegistry,
};

// ordem de empilhamento: o que vem depois fica por cima
const LAYER: Record<string, number> = { flash: 90, cta: 80, progress: 70, logo: 60 };

export const Main: React.FC<MainProps> = (p) => {
  loadBrandFonts(p.brand);
  const { edl, brand, safe } = p;
  const fps = edl.fps;
  const f = (s: number) => Math.round(s * fps);
  const overlays = [...(edl.overlays || [])]
    .filter((o) => o.end > o.start && !(o.props?.formats && !o.props.formats.includes(p.format)))
    .sort((a, b) => (LAYER[a.type] ?? 50) - (LAYER[b.type] ?? 50));
  // legendas saem de cena quando o CTA entra (a menos que o CTA peça keep_captions)
  const ctaFull = overlays.find((o) => o.type === "cta" && !o.props?.keep_captions);

  const renderOverlay = (o: Overlay, i: number) => {
    const from = f(o.start);
    const dur = Math.max(1, f(o.end) - from);
    const common = { props: o.props || {}, brand, safe, duration: dur / fps };
    let el: React.ReactNode = null;
    if (o.type === "progress") {
      el = <Progress {...common} total={edl.duration} startAt={o.start} />;
    } else {
      const name = o.type === "custom" ? o.props?.component : o.type;
      const C = registry[name];
      if (!C) {
        console.warn(`overlay desconhecido: ${name}`);
        return null;
      }
      el = <C {...common} />;
    }
    return (
      <Sequence key={`ov${i}`} from={from} durationInFrames={dur} layout="none">
        {el}
      </Sequence>
    );
  };

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <VideoLayer p={p} />
      {(edl.broll || []).map((b, i) => (
        <Sequence key={`br${i}`} from={f(b.start)} durationInFrames={Math.max(1, f(b.end) - f(b.start))}>
          <BRollClip b={b} brand={brand} />
        </Sequence>
      ))}
      {overlays.filter((o) => (LAYER[o.type] ?? 50) < 60).map(renderOverlay)}
      {edl.captions?.enabled !== false ? (
        <Sequence durationInFrames={ctaFull ? Math.max(1, f(ctaFull.start)) : undefined} layout="none">
          <Captions cs={edl.captions} brand={brand} safe={safe} />
        </Sequence>
      ) : null}
      {overlays.filter((o) => (LAYER[o.type] ?? 50) >= 60).map(renderOverlay)}
    </AbsoluteFill>
  );
};
