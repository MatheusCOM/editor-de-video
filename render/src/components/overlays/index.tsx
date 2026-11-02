import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { clamp, exitProgress, slideIn, textShadow } from "../../lib/anim";
import { fontCss } from "../../lib/fonts";
import type { Brand, Safe } from "../../types";

export type OverlayProps = {
  props: Record<string, any>;
  brand: Brand;
  safe: Safe;
  duration: number; // segundos
};

const asset = (src: string) => (/^(https?:|data:)/.test(src) ? src : staticFile(src));

/** "texto com *destaque*" → spans; destaque usa a cor de acento. */
export function RichText({ text, accent, style }: { text: string; accent: string; style?: React.CSSProperties }) {
  const parts = String(text).split(/(\*[^*]+\*)/g);
  return (
    <span style={style}>
      {parts.map((p, i) =>
        p.startsWith("*") && p.endsWith("*") ? (
          <span key={i} style={{ color: accent }}>
            {p.slice(1, -1)}
          </span>
        ) : (
          <React.Fragment key={i}>{p}</React.Fragment>
        ),
      )}
    </span>
  );
}

function yFor(position: any, safe: Safe, fallback: number) {
  if (typeof position === "number") return position;
  if (position === "top") return safe.top + 0.06;
  if (position === "center") return 0.45;
  if (position === "bottom") return 1 - safe.bottom - 0.08;
  return fallback;
}

// ---------------------------------------------------------------- título / gancho
export const Title: React.FC<OverlayProps & { defaults?: Record<string, any> }> = ({ props: raw, brand, safe, duration, defaults }) => {
  const props = { ...(defaults || {}), ...raw };
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const k = W / 1080;
  const size = (props.size ?? 0.085) * W;
  const y = yFor(props.position, safe, safe.top + 0.06);
  const anim = props.animation || "pop";
  const enter =
    anim === "pop" ? spring({ frame, fps, config: { damping: 12, stiffness: 200, mass: 0.6 } }) : 1;
  const tx = anim === "slide" ? slideIn(frame, fps, -W) : 0;
  const out = exitProgress(frame, fps, duration, 0.2);
  const accent = props.accent || brand.colors.accent;
  const bg = props.bg === undefined ? null : props.bg === "brand" ? brand.colors.primary : props.bg;
  const text = String(props.text ?? "");
  const shown =
    anim === "typewriter"
      ? text.slice(0, Math.floor(interpolate(frame, [0, Math.max(1, (props.type_seconds ?? 0.8) * fps)], [0, text.length], clamp)))
      : text;
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: W * safe.left,
          right: W * safe.right,
          top: H * y,
          display: "flex",
          justifyContent: "center",
          transform: `translateX(${tx}px) scale(${(0.5 + 0.5 * enter) * (1 - 0.15 * out)})`,
          opacity: 1 - out,
        }}
      >
        <div
          style={{
            ...fontCss(brand, props.font || "title"),
            ...(props.weight ? { fontWeight: props.weight } : {}),
            fontSize: size,
            lineHeight: 1.08,
            textAlign: "center",
            color: props.color || brand.colors.text,
            textTransform: props.uppercase === false ? "none" : "uppercase",
            background: bg || "transparent",
            padding: bg ? `${size * 0.22}px ${size * 0.4}px` : 0,
            borderRadius: brand.radius * k,
            textShadow: bg ? "none" : textShadow((props.stroke ?? 7) * k, brand.colors.caption_stroke || "#000"),
            transform: `rotate(${props.rotate ?? 0}deg)`,
            maxWidth: "100%",
            whiteSpace: "pre-wrap",
          }}
        >
          <RichText text={shown} accent={accent} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const TextPop: React.FC<OverlayProps> = (p) => (
  <Title {...p} defaults={{ position: "center", size: 0.12, animation: "pop" }} />
);

// ---------------------------------------------------------------- lower third
export const LowerThird: React.FC<OverlayProps> = ({ props, brand, safe, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const k = W / 1080;
  const x = slideIn(frame, fps, -W * 0.8);
  const x2 = slideIn(frame, fps, -W * 0.8, 4);
  const out = exitProgress(frame, fps, duration, 0.25);
  const y = yFor(props.position ?? "bottom", safe, 1 - safe.bottom - 0.08);
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: W * safe.left,
          top: H * y,
          transform: `translateX(${-out * W}px)`,
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          gap: 8 * k,
        }}
      >
        <div
          style={{
            transform: `translateX(${x}px)`,
            background: props.color || brand.colors.accent,
            color: brand.colors.text_dark || "#111",
            ...fontCss(brand, "title"),
            fontSize: (props.size ?? 0.055) * W,
            padding: `${10 * k}px ${22 * k}px`,
            borderRadius: brand.radius * 0.6 * k,
            textTransform: "uppercase",
          }}
        >
          {props.title}
        </div>
        {props.subtitle ? (
          <div
            style={{
              transform: `translateX(${x2}px)`,
              background: brand.colors.primary,
              color: brand.colors.secondary || "#fff",
              ...fontCss(brand, "body"),
              fontSize: (props.size ?? 0.055) * W * 0.62,
              padding: `${8 * k}px ${18 * k}px`,
              borderRadius: brand.radius * 0.5 * k,
            }}
          >
            {props.subtitle}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- CTA
export const CTA: React.FC<OverlayProps> = ({ props, brand, safe }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const k = W / 1080;
  const full = props.mode === "full";
  const bgIn = interpolate(frame, [0, 0.3 * fps], [0, 1], clamp);
  const e1 = spring({ frame, fps, config: { damping: 12, stiffness: 180 } });
  const e2 = spring({ frame: frame - 6, fps, config: { damping: 12, stiffness: 180 } });
  const e3 = spring({ frame: frame - 12, fps, config: { damping: 9, stiffness: 160 } });
  const pulse = 1 + 0.04 * Math.sin((frame / fps) * Math.PI * 2 * 1.4) * (frame > 20 ? 1 : 0);
  const logo = props.show_logo !== false && brand.logo.file ? brand.logo.file : null;
  const logoText = props.show_logo !== false && !brand.logo.file && brand.logo.text ? brand.logo.text : null;
  return (
    <AbsoluteFill
      style={{
        background: full
          ? props.bg || brand.colors.primary
          : `linear-gradient(to top, rgba(0,0,0,${0.75 * bgIn}) 0%, rgba(0,0,0,${0.35 * bgIn}) 55%, rgba(0,0,0,0) 100%)`,
        opacity: full ? bgIn : 1,
        justifyContent: full ? "center" : "flex-end",
        alignItems: "center",
        paddingBottom: full ? 0 : H * (safe.bottom + 0.04),
        paddingLeft: W * safe.left,
        paddingRight: W * safe.right,
        gap: 28 * k,
        textAlign: "center",
      }}
    >
      {logo ? (
        <Img src={asset(logo)} style={{ width: W * 0.32, transform: `scale(${e1})`, objectFit: "contain" }} />
      ) : null}
      {logoText ? (
        <div style={{ ...fontCss(brand, "mono"), fontSize: 0.026 * W, color: brand.colors.text_muted || brand.colors.text, opacity: e1 }}>
          {logoText}
        </div>
      ) : null}
      {props.title ? (
        <div
          style={{
            ...fontCss(brand, "title"),
            ...(props.weight ? { fontWeight: props.weight } : {}),
            fontSize: (props.size ?? 0.08) * W,
            color: brand.colors.text,
            lineHeight: 1.08,
            textTransform: props.uppercase === false ? "none" : "uppercase",
            transform: `translateY(${(1 - e1) * 60 * k}px)`,
            opacity: e1,
            textShadow: full ? "none" : textShadow(5 * k, "#000"),
          }}
        >
          <RichText text={props.title} accent={brand.colors.accent} />
        </div>
      ) : null}
      {props.subtitle ? (
        <div
          style={{
            ...fontCss(brand, "body"),
            fontSize: 0.042 * W,
            color: brand.colors.text,
            opacity: e2,
            transform: `translateY(${(1 - e2) * 40 * k}px)`,
          }}
        >
          {props.subtitle}
        </div>
      ) : null}
      {props.button !== false ? (
        <div
          style={{
            ...fontCss(brand, props.button_font || "title"),
            fontSize: 0.045 * W,
            background: props.button_color || brand.colors.accent,
            color: brand.colors.text_dark || "#111",
            padding: `${22 * k}px ${48 * k}px`,
            borderRadius: 999,
            transform: `scale(${e3 * pulse})`,
            boxShadow: "0 12px 40px rgba(0,0,0,0.35)",
          }}
        >
          {props.button || brand.cta_default || "Saiba mais"}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- emoji / imagem / seta
export const EmojiPop: React.FC<OverlayProps> = ({ props, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 8, stiffness: 220, mass: 0.5 } });
  const out = exitProgress(frame, fps, duration, 0.15);
  const wobble = Math.sin(frame / 4) * 6;
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: W * (props.x ?? 0.75),
          top: H * (props.y ?? 0.3),
          fontSize: (props.size ?? 0.16) * W,
          transform: `translate(-50%,-50%) scale(${s * (1 - out)}) rotate(${(props.rotate ?? 0) + wobble}deg)`,
        }}
      >
        {props.emoji || "🔥"}
      </div>
    </AbsoluteFill>
  );
};

export const ImageOverlay: React.FC<OverlayProps> = ({ props, brand, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const anim = props.animation || "pop";
  const s = anim === "pop" ? spring({ frame, fps, config: { damping: 11, stiffness: 180 } }) : 1;
  const op = anim === "fade" ? interpolate(frame, [0, 0.25 * fps], [0, 1], clamp) : 1;
  const out = exitProgress(frame, fps, duration, 0.2);
  return (
    <AbsoluteFill>
      <Img
        src={asset(props.src)}
        style={{
          position: "absolute",
          left: W * (props.x ?? 0.5),
          top: H * (props.y ?? 0.4),
          width: W * (props.width ?? 0.6),
          transform: `translate(-50%,-50%) scale(${s * (1 - out * 0.3)}) rotate(${props.rotate ?? 0}deg)`,
          opacity: op * (1 - out),
          borderRadius: props.rounded ? brand.radius * (W / 1080) : 0,
          boxShadow: props.shadow ? "0 20px 60px rgba(0,0,0,0.45)" : "none",
        }}
      />
    </AbsoluteFill>
  );
};

export const Arrow: React.FC<OverlayProps> = ({ props, brand, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const draw = interpolate(frame, [0, 0.35 * fps], [0, 1], clamp);
  const out = exitProgress(frame, fps, duration, 0.15);
  const len = (props.length ?? 0.22) * W;
  const color = props.color || brand.colors.accent;
  const sw = 16 * (W / 1080);
  return (
    <AbsoluteFill>
      <svg
        width={len + sw * 4}
        height={sw * 6}
        style={{
          position: "absolute",
          left: W * (props.x ?? 0.5),
          top: H * (props.y ?? 0.5),
          transform: `translate(-100%,-50%) rotate(${props.angle ?? 0}deg)`,
          transformOrigin: "100% 50%",
          opacity: 1 - out,
          overflow: "visible",
        }}
      >
        <line x1={0} y1={sw * 3} x2={len * draw} y2={sw * 3} stroke={color} strokeWidth={sw} strokeLinecap="round" />
        {draw > 0.95 ? (
          <polyline
            points={`${len - sw * 2.5},${sw * 0.6} ${len + sw * 0.5},${sw * 3} ${len - sw * 2.5},${sw * 5.4}`}
            fill="none"
            stroke={color}
            strokeWidth={sw}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ) : null}
      </svg>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- checklist / contador
export const Checklist: React.FC<OverlayProps> = ({ props, brand, safe, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const k = W / 1080;
  const items: string[] = props.items || [];
  const step = (props.step ?? Math.min(0.8, (duration - 0.6) / Math.max(1, items.length))) * fps;
  const out = exitProgress(frame, fps, duration, 0.2);
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: W * (safe.left + 0.02),
          right: W * (safe.right + 0.02),
          top: H * yFor(props.position ?? 0.3, safe, 0.3),
          display: "flex",
          flexDirection: "column",
          gap: 18 * k,
          opacity: 1 - out,
        }}
      >
        {props.title ? (
          <div style={{ ...fontCss(brand, "title"), fontSize: 0.06 * W, color: brand.colors.text, textTransform: "uppercase", textShadow: textShadow(5 * k, "#000") }}>
            <RichText text={props.title} accent={brand.colors.accent} />
          </div>
        ) : null}
        {items.map((it, i) => {
          const s = spring({ frame: frame - i * step - 6, fps, config: { damping: 13, stiffness: 200 } });
          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 18 * k,
                transform: `translateX(${(1 - s) * -80 * k}px)`,
                opacity: s,
                background: "rgba(0,0,0,0.55)",
                borderRadius: brand.radius * k,
                padding: `${14 * k}px ${22 * k}px`,
              }}
            >
              <div
                style={{
                  width: 54 * k,
                  height: 54 * k,
                  borderRadius: 999,
                  background: brand.colors.accent2 || brand.colors.accent,
                  color: "#111",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 34 * k,
                  fontWeight: 900,
                  flexShrink: 0,
                }}
              >
                {props.icon || "✓"}
              </div>
              <div style={{ ...fontCss(brand, "body"), fontSize: 0.045 * W, color: "#fff" }}>{it}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const Counter: React.FC<OverlayProps> = ({ props, brand, safe, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const k = W / 1080;
  const dur = (props.count_seconds ?? Math.min(1.2, duration * 0.6)) * fps;
  const v = interpolate(frame, [0, dur], [props.from ?? 0, props.to ?? 100], { ...clamp, easing: (x) => 1 - Math.pow(1 - x, 3) });
  const decimals = props.decimals ?? 0;
  const txt = v.toLocaleString("pt-BR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  const s = spring({ frame, fps, config: { damping: 12 } });
  const out = exitProgress(frame, fps, duration, 0.2);
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: H * yFor(props.position ?? "center", safe, 0.4),
          textAlign: "center",
          ...fontCss(brand, "title"),
          fontSize: (props.size ?? 0.16) * W,
          color: props.color || brand.colors.accent,
          textShadow: textShadow(7 * k, "#000"),
          transform: `scale(${s * (1 - out)})`,
        }}
      >
        {props.prefix || ""}
        {txt}
        {props.suffix || ""}
        {props.label ? (
          <div style={{ ...fontCss(brand, "body"), fontSize: 0.045 * W, color: brand.colors.text }}>{props.label}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- barra de progresso / logo / flash
export const Progress: React.FC<OverlayProps & { total: number; startAt: number }> = ({ props, brand, total, startAt }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const p = Math.min(1, (startAt + frame / fps) / total);
  const h = (props.height ?? 10) * (W / 1080);
  const top = props.position === "bottom" ? H - h : 0;
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 0, top, width: W, height: h, background: "rgba(255,255,255,0.25)" }} />
      <div style={{ position: "absolute", left: 0, top, width: W * p, height: h, background: props.color || brand.colors.accent }} />
    </AbsoluteFill>
  );
};

export const Logo: React.FC<OverlayProps> = ({ props, brand, safe }) => {
  const { width: W, height: H } = useVideoConfig();
  const file = props.src || brand.logo.file;
  const text = props.text || brand.logo.text;
  if (!file && !text) return null;
  const pos: string = props.position || brand.logo.position || "top-right";
  const w = W * (props.size ?? brand.logo.size ?? 0.14);
  const m = W * 0.05;
  const style: React.CSSProperties = { position: "absolute", width: w, opacity: props.opacity ?? brand.logo.opacity ?? 0.9 };
  if (pos.includes("top")) style.top = H * safe.top * 0.6;
  else style.bottom = H * safe.bottom * 0.8;
  if (pos.includes("left")) style.left = m;
  else if (pos.includes("right")) style.right = m;
  else {
    style.left = (W - w) / 2;
  }
  if (!file) {
    delete style.width;
    if (!pos.includes("left") && !pos.includes("right")) {
      style.left = 0;
      style.right = 0;
      style.textAlign = "center";
    }
    return (
      <AbsoluteFill>
        <div style={{ ...style, ...fontCss(brand, "mono"), fontSize: W * 0.022 * (props.scale ?? 1), color: props.color || brand.colors.text }}>
          {text}
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill>
      <Img src={asset(file)} style={style} />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- rótulo (mono, discreto)
export const Rotulo: React.FC<OverlayProps> = ({ props, brand, safe, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const op = interpolate(frame, [0, 0.3 * fps], [0, 1], clamp) * (1 - exitProgress(frame, fps, duration, 0.25));
  const align = props.align || "left";
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: W * safe.left,
          right: W * safe.right,
          top: H * yFor(props.position ?? "top", safe, safe.top + 0.02),
          textAlign: align,
          ...fontCss(brand, "mono"),
          fontSize: (props.size ?? 0.028) * W,
          color: props.color || brand.colors.accent,
          textTransform: "uppercase",
          opacity: op,
        }}
      >
        {props.text}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- assinatura do médico (nome · CRM · RQE)
export const Assinatura: React.FC<OverlayProps> = ({ props, brand, safe, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const k = W / 1080;
  const base = brand.assinatura || {
    nome: brand.medico?.nome,
    registro_tipo: "CRM",
    registro: brand.medico?.crm,
    extra: [brand.medico?.rqe ? `RQE ${brand.medico.rqe}` : "", brand.medico?.especialidade || ""].filter(Boolean).join(" · "),
  };
  const m: Record<string, any> = { ...base, ...props };
  const line = interpolate(frame, [0, 0.5 * fps], [0, 1], { ...clamp, easing: (x) => 1 - Math.pow(1 - x, 3) });
  const op = interpolate(frame, [0.15 * fps, 0.5 * fps], [0, 1], clamp) * (1 - exitProgress(frame, fps, duration, 0.3));
  const regs = [m.registro ? `${m.registro_tipo || ""} ${m.registro}`.trim() : null, m.extra || null]
    .filter(Boolean)
    .join(" · ");
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: W * safe.left,
          top: H * yFor(props.position ?? "bottom", safe, 1 - safe.bottom - 0.08),
          display: "flex",
          flexDirection: "column",
          gap: 10 * k,
          opacity: op,
        }}
      >
        <div style={{ width: W * 0.12 * line, height: Math.max(2, 3 * k), background: brand.colors.accent }} />
        <div style={{ ...fontCss(brand, "title"), fontWeight: 400, fontSize: 0.045 * W, color: brand.colors.text }}>{m.nome}</div>
        {m.cargo ? (
          <div style={{ ...fontCss(brand, "body"), fontSize: 0.03 * W, color: brand.colors.text_muted || brand.colors.text }}>
            {m.cargo}
          </div>
        ) : null}
        {regs ? (
          <div style={{ ...fontCss(brand, "mono"), fontSize: 0.024 * W, color: brand.colors.text_muted || brand.colors.text }}>{regs}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

export const Flash: React.FC<OverlayProps> = ({ props, duration }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const o = interpolate(frame, [0, duration * fps], [props.intensity ?? 0.9, 0], clamp);
  return <AbsoluteFill style={{ background: props.color || "#fff", opacity: o }} />;
};
