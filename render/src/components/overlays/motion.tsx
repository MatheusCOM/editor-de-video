// Componentes dos modelos capa-fala e lista-motion. Neutros: cores/fontes só pelos papéis da marca.
import React from "react";
import { AbsoluteFill, Img, interpolate, OffthreadVideo, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { clamp, exitProgress, textShadow } from "../../lib/anim";
import { fontCss } from "../../lib/fonts";
import type { OverlayProps } from "./index";

const asset = (src: string) => (/^(https?:|data:)/.test(src) ? src : staticFile(src));
const isVideo = (src: string) => /\.(mp4|mov|webm|m4v)$/i.test(src);

/** "texto com *destaque*": destaque vira caixa na cor de acento (estilo capa) ou só cor. */
function Destaques({ text, accent, onAccent, box }: { text: string; accent: string; onAccent: string; box: boolean }) {
  const parts = String(text).split(/(\*[^*]+\*)/g);
  return (
    <>
      {parts.map((p, i) =>
        p.startsWith("*") && p.endsWith("*") ? (
          <span
            key={i}
            style={
              box
                ? { background: accent, color: onAccent, padding: "0 0.18em", borderRadius: "0.12em", boxDecorationBreak: "clone", WebkitBoxDecorationBreak: "clone" }
                : { color: accent }
            }
          >
            {p.slice(1, -1)}
          </span>
        ) : (
          <React.Fragment key={i}>{p}</React.Fragment>
        ),
      )}
    </>
  );
}

// ---------------------------------------------------------------- capa (faixa fixa no topo)
// props: titulo (com *destaques*), subtitulo, imagem (fundo), altura (fração, padrão 0.42),
//        estilo_destaque: "caixa" | "cor", uppercase (padrão true), alinhamento: "left" | "center"
export const Capa: React.FC<OverlayProps> = ({ props, brand, safe }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const k = W / 1080;
  const h = H * (props.altura ?? 0.42);
  const c = brand.colors;
  const enter = spring({ frame, fps, config: { damping: 16, stiffness: 140 } });
  const align = props.alinhamento || "left";
  const titleSize = (props.size ?? 0.095) * W;
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 0,
          height: h,
          overflow: "hidden",
          background: c.background || c.primary,
        }}
      >
        {props.imagem ? (
          isVideo(props.imagem) ? (
            <OffthreadVideo src={asset(props.imagem)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          ) : (
            <Img src={asset(props.imagem)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          )
        ) : null}
        {props.imagem && props.titulo ? (
          <div style={{ position: "absolute", inset: 0, background: `linear-gradient(to bottom, ${c.background || "#000"}cc 0%, ${c.background || "#000"}55 60%, transparent 100%)` }} />
        ) : null}
        {props.titulo ? (
          <div
            style={{
              position: "absolute",
              left: W * safe.left,
              right: W * safe.right,
              top: Math.max(H * safe.top * 0.7, 40 * k),
              textAlign: align,
              ...fontCss(brand, "title"),
              ...(props.weight ? { fontWeight: props.weight } : {}),
              fontSize: titleSize,
              lineHeight: 1.08,
              color: c.text,
              textTransform: props.uppercase === false ? "none" : "uppercase",
              textShadow: props.imagem ? textShadow(0, "#000", true) : "none",
              opacity: interpolate(frame, [0, 0.25 * fps], [0, 1], clamp),
              transform: `translateY(${(1 - enter) * 30 * k}px)`,
            }}
          >
            <Destaques text={props.titulo} accent={c.accent} onAccent={c.text_dark || "#111"} box={props.estilo_destaque !== "cor"} />
            {props.subtitulo ? (
              <div style={{ ...fontCss(brand, "body"), fontSize: titleSize * 0.36, marginTop: 14 * k, color: c.text_muted || c.text, textTransform: "none" }}>
                {props.subtitulo}
              </div>
            ) : null}
          </div>
        ) : null}
        {/* linha de separação discreta entre capa e vídeo */}
        <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: Math.max(2, 3 * k), background: props.linha === false ? "transparent" : c.accent, opacity: 0.9 }} />
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- cena (fundo da marca em tela cheia)
// Esconde o apresentador; use com item_numerado/cartao por cima. props: estilo "gradiente" | "solido", entrada (s)
export const Cena: React.FC<OverlayProps> = ({ props, brand, duration }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const c = brand.colors;
  const inS = props.entrada ?? 0.12;
  const op = interpolate(frame, [0, inS * fps, duration * fps - inS * fps, duration * fps], [0, 1, 1, 0], clamp);
  const bg =
    props.estilo === "solido"
      ? c.background || c.primary
      : `radial-gradient(120% 80% at 50% 35%, ${c.primary} 0%, ${c.background || c.primary} 75%)`;
  return <AbsoluteFill style={{ background: bg, opacity: op }} />;
};

// ---------------------------------------------------------------- item numerado ("#3  Título")
// props: numero, titulo, subtitulo (rótulo mono), icone (imagem opcional), position (0..1, padrão 0.2)
export const ItemNumerado: React.FC<OverlayProps> = ({ props, brand, safe, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const k = W / 1080;
  const c = brand.colors;
  const blurIn = (delay: number) => {
    const p = interpolate(frame - delay, [0, 0.4 * fps], [0, 1], { ...clamp, easing: (x) => 1 - Math.pow(1 - x, 3) });
    return { opacity: p, filter: `blur(${(1 - p) * 18 * k}px)`, transform: `translateY(${(1 - p) * 20 * k}px)` };
  };
  const pop = spring({ frame, fps, config: { damping: 11, stiffness: 180, mass: 0.6 } });
  const out = exitProgress(frame, fps, duration, 0.2);
  const y = props.position ?? 0.2;
  return (
    <AbsoluteFill style={{ opacity: 1 - out }}>
      <div
        style={{
          position: "absolute",
          left: W * safe.left,
          right: W * safe.right,
          top: H * y,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 14 * k,
          textAlign: "center",
        }}
      >
        {props.numero !== undefined ? (
          <div style={{ ...fontCss(brand, "mono"), fontSize: 0.034 * W, color: c.accent, ...blurIn(0) }}>#{props.numero}</div>
        ) : null}
        {props.icone ? (
          <Img
            src={asset(props.icone)}
            style={{ width: 0.16 * W, height: 0.16 * W, objectFit: "cover", borderRadius: brand.radius * 1.4 * k, transform: `scale(${pop})`, boxShadow: "0 16px 40px rgba(0,0,0,0.45)" }}
          />
        ) : null}
        <div style={{ ...fontCss(brand, "title"), fontWeight: props.weight ?? 700, fontSize: (props.size ?? 0.085) * W, lineHeight: 1.05, color: c.text, ...blurIn(3) }}>
          {props.titulo}
        </div>
        {props.subtitulo ? (
          <div style={{ ...fontCss(brand, "mono"), fontSize: 0.024 * W, color: c.text_muted || c.text, ...blurIn(7) }}>{props.subtitulo}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- cartão (imagem/vídeo/print ou texto)
// props: src (imagem/vídeo) OU titulo+texto; posicao "topo" | "centro" | número; largura (fração, 0.62);
//        proporcao (largura/altura, padrão: da mídia ou 0.75); rotulo (chip opcional embaixo)
export const Cartao: React.FC<OverlayProps> = ({ props, brand, safe, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const k = W / 1080;
  const c = brand.colors;
  const p = spring({ frame, fps, config: { damping: 14, stiffness: 150, mass: 0.7 } });
  const blur = interpolate(frame, [0, 0.3 * fps], [16 * k, 0], clamp);
  const out = exitProgress(frame, fps, duration, 0.2);
  const float = Math.sin((frame / fps) * Math.PI * 0.8) * 6 * k;
  const ratio = props.proporcao ?? (props.src ? 0.75 : 1.25);
  const pos = props.posicao ?? "topo";
  let w = W * (props.largura ?? 0.62);
  let hgt = w / ratio;
  let top: number;
  if (typeof pos === "number") {
    top = H * pos;
  } else if (pos === "centro") {
    // centrado acima da legenda (que fica por volta de 60% da altura)
    const limite = H * (props.limite ?? 0.54) - H * (safe.top + 0.02);
    if (hgt > limite) {
      hgt = limite;
      w = hgt * ratio;
    }
    top = Math.max(H * (safe.top + 0.02), H * 0.36 - hgt / 2);
  } else {
    // topo: não desce além de 36% da altura, para não cobrir o rosto de quem fala
    top = H * (safe.top + 0.02);
    const limite = H * (props.limite ?? 0.36) - top;
    if (hgt > limite) {
      hgt = limite;
      w = hgt * ratio;
    }
  }
  const radius = brand.radius * 1.6 * k;
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: (W - w) / 2,
          top: top + float,
          width: w,
          height: hgt,
          borderRadius: radius,
          overflow: "hidden",
          background: props.src ? "#000" : c.primary,
          border: `${Math.max(1, 2 * k)}px solid ${c.border || "rgba(255,255,255,0.12)"}`,
          boxShadow: "0 30px 80px rgba(0,0,0,0.55)",
          transform: `scale(${0.85 + 0.15 * p}) translateY(${(1 - p) * 60 * k}px) rotate(${(props.rotacao ?? 0) * p}deg)`,
          filter: `blur(${blur + out * 10 * k}px)`,
          opacity: Math.min(1, p * 1.4) * (1 - out),
        }}
      >
        {props.src ? (
          isVideo(props.src) ? (
            <OffthreadVideo src={asset(props.src)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          ) : (
            <Img src={asset(props.src)} style={{ width: "100%", height: "100%", objectFit: props.ajuste || "cover" }} />
          )
        ) : (
          <div style={{ padding: 44 * k, display: "flex", flexDirection: "column", gap: 18 * k, height: "100%", justifyContent: "center" }}>
            {props.rotulo_topo ? (
              <div style={{ ...fontCss(brand, "mono"), fontSize: 0.022 * W, color: c.accent, textTransform: "uppercase" }}>{props.rotulo_topo}</div>
            ) : null}
            <div style={{ ...fontCss(brand, "title"), fontSize: (props.size ?? 0.06) * W, lineHeight: 1.1, color: c.text }}>
              <Destaques text={props.titulo || ""} accent={c.accent} onAccent={c.text_dark || "#111"} box={false} />
            </div>
            {props.texto ? (
              <div style={{ ...fontCss(brand, "body"), fontSize: 0.034 * W, lineHeight: 1.35, color: c.text_muted || c.text }}>{props.texto}</div>
            ) : null}
          </div>
        )}
      </div>
      {props.rotulo ? (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: top + hgt + 22 * k + float,
            textAlign: "center",
            opacity: interpolate(frame, [6, 14], [0, 1], clamp) * (1 - out),
          }}
        >
          <span
            style={{
              ...fontCss(brand, "mono"),
              fontSize: 0.024 * W,
              color: c.text_dark || "#111",
              background: c.accent,
              padding: `${8 * k}px ${18 * k}px`,
              borderRadius: 999,
              textTransform: "uppercase",
            }}
          >
            {props.rotulo}
          </span>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
