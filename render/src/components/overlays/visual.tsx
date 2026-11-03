// Vocabulário visual "representativo": ilustra a ideia da fala em vez de repetir o texto.
// Todos neutros de marca (só papéis de cor/fonte da marca).
import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { clamp, exitProgress } from "../../lib/anim";
import { fontCss } from "../../lib/fonts";
import ICONS from "../../lib/icons.generated.json";
import type { Brand } from "../../types";
import type { OverlayProps } from "./index";

const ICON_MAP = ICONS as Record<string, string>;
const easeOut = Easing.out(Easing.cubic);

function cor(brand: Brand, c?: string) {
  if (!c || c === "accent") return brand.colors.accent;
  if (c === "text") return brand.colors.text;
  if (c === "muted") return brand.colors.text_muted || brand.colors.text;
  if (c === "warning" || c === "success") return brand.colors[c] || brand.colors.accent;
  return c;
}

// ---------------------------------------------------------------- ícone desenhado (traço → pronto)
export const IconSvg: React.FC<{ nome: string; size: number; color: string; draw: number; stroke?: number; glow?: boolean }> = ({
  nome,
  size,
  color,
  draw,
  stroke = 1.6,
  glow,
}) => {
  const inner = ICON_MAP[nome] || ICON_MAP["circle-help"] || "";
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{
        overflow: "visible",
        filter: glow ? `drop-shadow(0 0 ${size * 0.08}px ${color}88)` : "drop-shadow(0 6px 14px rgba(0,0,0,0.45))",
        ["--d" as any]: String(1 - draw),
      }}
    >
      <style>{`*{stroke-dasharray:1;stroke-dashoffset:var(--d)}`}</style>
      <g dangerouslySetInnerHTML={{ __html: inner }} />
    </svg>
  );
};

// props: nome (lucide), x, y (centro, 0..1), size (fração da largura, 0.18), cor, rotulo, fundo (bool: disco escuro),
//        desenhar (s, 0.6), pulso (bool)
export const Icone: React.FC<OverlayProps> = ({ props, brand, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const k = W / 1080;
  const s = (props.size ?? 0.18) * W;
  const draw = interpolate(frame, [0, (props.desenhar ?? 0.6) * fps], [0, 1], { ...clamp, easing: easeOut });
  const pop = spring({ frame, fps, config: { damping: 12, stiffness: 160, mass: 0.6 } });
  const out = exitProgress(frame, fps, duration, 0.25);
  const pulse = props.pulso ? 1 + 0.04 * Math.sin((frame / fps) * Math.PI * 2) : 1;
  const float = Math.sin((frame / fps) * Math.PI * 0.7) * 6 * k;
  const c = cor(brand, props.cor);
  return (
    <AbsoluteFill style={{ opacity: 1 - out }}>
      <div
        style={{
          position: "absolute",
          left: W * (props.x ?? 0.5),
          top: H * (props.y ?? 0.5) + float,
          transform: `translate(-50%,-50%) scale(${(0.7 + 0.3 * pop) * pulse * (1 - out * 0.2)})`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 12 * k,
        }}
      >
        <div
          style={{
            width: s * (props.fundo === false ? 1 : 1.5),
            height: s * (props.fundo === false ? 1 : 1.5),
            borderRadius: 999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: props.fundo === false ? "transparent" : `${brand.colors.background || "#000"}cc`,
            border: props.fundo === false ? "none" : `${Math.max(1.5, 2 * k)}px solid ${c}55`,
          }}
        >
          <IconSvg nome={props.nome} size={s} color={c} draw={draw} glow={props.brilho} />
        </div>
        {props.rotulo ? (
          <div
            style={{
              ...fontCss(brand, "mono"),
              fontSize: 0.024 * W,
              color: brand.colors.text,
              textTransform: "uppercase",
              background: `${brand.colors.background || "#000"}b3`,
              padding: `${5 * k}px ${12 * k}px`,
              borderRadius: 8 * k,
              opacity: interpolate(frame, [0.35 * fps, 0.6 * fps], [0, 1], clamp),
            }}
          >
            {props.rotulo}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- diagrama: fatores em volta de um centro
// props: itens [{icone, rotulo, em}], centro {icone, texto}, x, y (centro, 0..1), raio (fração da largura, 0.3),
//        convergir_em (s: os itens viajam até o centro e o centro "pulsa"), arco ("cheio" | "superior" | "inferior")
export const Diagrama: React.FC<OverlayProps> = ({ props, brand, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const k = W / 1080;
  const itens: any[] = props.itens || [];
  const cx = W * (props.x ?? 0.5);
  const cy = H * (props.y ?? 0.5);
  const R = W * (props.raio ?? 0.3);
  const out = exitProgress(frame, fps, duration, 0.3);
  const conv = props.convergir_em !== undefined
    ? interpolate(frame, [props.convergir_em * fps, (props.convergir_em + 0.7) * fps], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) })
    : 0;
  const arco = props.arco || "cheio";
  const [a0, a1] = arco === "superior" ? [Math.PI * 1.05, Math.PI * 1.95] : arco === "inferior" ? [Math.PI * 0.05, Math.PI * 0.95] : [-Math.PI / 2, Math.PI * 1.5];
  const n = itens.length;
  const ang = (i: number) => (arco === "cheio" ? a0 + ((a1 - a0) * i) / n : a0 + ((a1 - a0) * i) / Math.max(1, n - 1));
  const centroPop = spring({ frame: frame - (props.centro_em ?? 0) * fps, fps, config: { damping: 11, stiffness: 150 } });
  const pulse = conv > 0.95 ? 1 + 0.08 * Math.sin(((frame - (props.convergir_em + 0.7) * fps) / fps) * Math.PI * 3) * Math.exp(-((frame / fps - props.convergir_em - 0.7) * 2)) : 1;
  const iconS = (props.icon_size ?? 0.09) * W;
  const ac = brand.colors.accent;
  return (
    <AbsoluteFill style={{ opacity: 1 - out }}>
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
        {itens.map((it, i) => {
          const t0 = (it.em ?? i * 0.5) * fps;
          const d = interpolate(frame - t0, [0, 0.45 * fps], [0, 1], { ...clamp, easing: easeOut });
          const x = cx + Math.cos(ang(i)) * R;
          const y = cy + Math.sin(ang(i)) * R;
          return (
            <line
              key={i}
              x1={cx}
              y1={cy}
              x2={cx + (x - cx) * d * (1 - conv)}
              y2={cy + (y - cy) * d * (1 - conv)}
              stroke={`${ac}88`}
              strokeWidth={Math.max(1.5, 2.5 * k)}
              strokeDasharray={`${6 * k} ${8 * k}`}
            />
          );
        })}
      </svg>
      {props.centro ? (
        <div
          style={{
            position: "absolute",
            left: cx,
            top: cy,
            transform: `translate(-50%,-50%) scale(${centroPop * pulse})`,
            width: iconS * 2.1,
            height: iconS * 2.1,
            borderRadius: 999,
            background: conv > 0.5 ? ac : `${brand.colors.background || "#000"}e6`,
            border: `${Math.max(2, 3 * k)}px solid ${ac}`,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 4 * k,
            boxShadow: `0 0 ${40 * k * conv}px ${ac}88`,
          }}
        >
          {props.centro.icone ? (
            <IconSvg nome={props.centro.icone} size={iconS} color={conv > 0.5 ? brand.colors.text_dark || "#111" : ac} draw={centroPop} />
          ) : null}
          {props.centro.texto ? (
            <div style={{ ...fontCss(brand, "mono"), fontSize: 0.022 * W, textTransform: "uppercase", color: conv > 0.5 ? brand.colors.text_dark || "#111" : brand.colors.text }}>
              {props.centro.texto}
            </div>
          ) : null}
        </div>
      ) : null}
      {itens.map((it, i) => {
        const t0 = (it.em ?? i * 0.5) * fps;
        if (frame < t0) return null;
        const p = spring({ frame: frame - t0, fps, config: { damping: 12, stiffness: 170, mass: 0.6 } });
        const draw = interpolate(frame - t0, [0, 0.5 * fps], [0, 1], { ...clamp, easing: easeOut });
        const x = cx + Math.cos(ang(i)) * R * (1 - conv);
        const y = cy + Math.sin(ang(i)) * R * (1 - conv);
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x,
              top: y,
              transform: `translate(-50%,-50%) scale(${(0.6 + 0.4 * p) * (1 - conv * 0.6)})`,
              opacity: 1 - conv * 0.9,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 8 * k,
            }}
          >
            <div
              style={{
                width: iconS * 1.45,
                height: iconS * 1.45,
                borderRadius: 999,
                background: `${brand.colors.background || "#000"}d9`,
                border: `${Math.max(1.5, 2 * k)}px solid ${ac}66`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <IconSvg nome={it.icone} size={iconS} color={brand.colors.text} draw={draw} />
            </div>
            {it.rotulo ? (
              <div
                style={{
                  ...fontCss(brand, "mono"),
                  fontSize: 0.021 * W,
                  color: brand.colors.text,
                  textTransform: "uppercase",
                  background: `${brand.colors.background || "#000"}b3`,
                  padding: `${4 * k}px ${10 * k}px`,
                  borderRadius: 6 * k,
                  whiteSpace: "nowrap",
                }}
              >
                {it.rotulo}
              </div>
            ) : null}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- balança (comparação que pesa)
// props: esquerda {rotulo, icone}, direita {rotulo, icone}, inclinar_para "esquerda"|"direita", inclinar_em (s),
//        x, y (pivô, 0..1), largura (fração, 0.7), titulo (mono acima), riscar ("esquerda"|"direita", riscar_em)
export const Balanca: React.FC<OverlayProps> = ({ props, brand, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const k = W / 1080;
  const ac = brand.colors.accent;
  const out = exitProgress(frame, fps, duration, 0.3);
  const L = W * (props.largura ?? 0.7);
  const px = W * (props.x ?? 0.5);
  const py = H * (props.y ?? 0.72);
  const build = interpolate(frame, [0, 0.5 * fps], [0, 1], { ...clamp, easing: easeOut });
  const dir = props.inclinar_para === "esquerda" ? -1 : props.inclinar_para === "direita" ? 1 : 0;
  const tilt = props.inclinar_em !== undefined
    ? spring({ frame: frame - props.inclinar_em * fps, fps, config: { damping: 7, stiffness: 60, mass: 1.2 } }) * 14 * dir
    : 0;
  const rad = (tilt * Math.PI) / 180;
  const arm = L / 2;
  const prato = (lado: -1 | 1) => ({ x: px + Math.cos(rad) * arm * lado, y: py + Math.sin(rad) * arm * lado });
  const riscar = props.riscar_em !== undefined ? interpolate(frame, [props.riscar_em * fps, (props.riscar_em + 0.3) * fps], [0, 1], clamp) : 0;
  const lado = (side: "esquerda" | "direita", s: -1 | 1, d: number) => {
    const conf = props[side] || {};
    const p = prato(s);
    const pop = spring({ frame: frame - d * fps, fps, config: { damping: 12, stiffness: 160 } });
    const isRisc = props.riscar === side;
    const panW = 0.24 * W;
    return (
      <div
        key={side}
        style={{
          position: "absolute",
          left: p.x,
          top: p.y + 0.055 * W,
          transform: `translate(-50%,0) scale(${pop})`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 8 * k,
          opacity: isRisc ? 1 - riscar * 0.5 : 1,
        }}
      >
        <div style={{ width: panW, height: 6 * k, borderRadius: 6 * k, background: ac }} />
        <div
          style={{
            marginTop: -2,
            padding: `${12 * k}px ${16 * k}px`,
            borderRadius: brand.radius * k,
            background: `${brand.colors.background || "#000"}d9`,
            border: `${Math.max(1.5, 2 * k)}px solid ${ac}55`,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 8 * k,
            minWidth: panW * 0.8,
            position: "relative",
          }}
        >
          {conf.icone ? <IconSvg nome={conf.icone} size={0.07 * W} color={brand.colors.text} draw={pop} /> : null}
          <div style={{ ...fontCss(brand, "body"), fontWeight: 700, fontSize: 0.034 * W, color: brand.colors.text, textAlign: "center" }}>{conf.rotulo}</div>
          {isRisc && riscar > 0 ? (
            <div style={{ position: "absolute", left: "8%", top: "50%", width: `${84 * riscar}%`, height: 5 * k, background: brand.colors.warning || ac, transform: "rotate(-12deg)", borderRadius: 4 }} />
          ) : null}
        </div>
      </div>
    );
  };
  return (
    <AbsoluteFill style={{ opacity: 1 - out }}>
      {props.titulo ? (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: py - 0.09 * W,
            textAlign: "center",
            opacity: build,
          }}
        >
          <span style={{ ...fontCss(brand, "mono"), fontSize: 0.024 * W, color: brand.colors.text, textTransform: "uppercase", background: `${brand.colors.background || "#000"}b3`, padding: `${5 * k}px ${12 * k}px`, borderRadius: 8 * k }}>
            {props.titulo}
          </span>
        </div>
      ) : null}
      <svg width={W} height={H} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
        <line x1={px} y1={py} x2={px} y2={py + 0.13 * W} stroke={ac} strokeWidth={6 * k} strokeLinecap="round" opacity={build} />
        <circle cx={px} cy={py} r={9 * k * build} fill={ac} />
        <line
          x1={px - Math.cos(rad) * arm * build}
          y1={py - Math.sin(rad) * arm * build}
          x2={px + Math.cos(rad) * arm * build}
          y2={py + Math.sin(rad) * arm * build}
          stroke={ac}
          strokeWidth={6 * k}
          strokeLinecap="round"
        />
        {(([-1, 1] as const)).map((s) => {
          const p = prato(s);
          return <line key={s} x1={p.x} y1={p.y} x2={p.x} y2={p.y + 0.055 * W} stroke={`${ac}aa`} strokeWidth={3 * k} opacity={build} />;
        })}
      </svg>
      {lado("esquerda", -1, props.esquerda?.em ?? 0.3)}
      {lado("direita", 1, props.direita?.em ?? 0.6)}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- gráfico animado
// props: tipo "barras" | "rosca", dados [{rotulo, valor, destaque}], sufixo ("%"), titulo, x, y (centro), largura (0.7)
export const Grafico: React.FC<OverlayProps> = ({ props, brand, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const k = W / 1080;
  const ac = brand.colors.accent;
  const out = exitProgress(frame, fps, duration, 0.3);
  const dados: any[] = props.dados || [];
  const max = props.max ?? Math.max(...dados.map((d) => d.valor), 1);
  const largura = W * (props.largura ?? 0.7);
  const cx = W * (props.x ?? 0.5);
  const cy = H * (props.y ?? 0.5);
  const suf = props.sufixo ?? "";
  const titulo = props.titulo ? (
    <div style={{ ...fontCss(brand, "mono"), fontSize: 0.024 * W, color: brand.colors.text, textTransform: "uppercase", marginBottom: 16 * k, textAlign: "center" }}>
      <span style={{ background: `${brand.colors.background || "#000"}b3`, padding: `${5 * k}px ${12 * k}px`, borderRadius: 8 * k }}>{props.titulo}</span>
    </div>
  ) : null;
  if (props.tipo === "rosca") {
    const r = largura * 0.28;
    const C = 2 * Math.PI * r;
    let acc = 0;
    const total = dados.reduce((s, d) => s + d.valor, 0) || 1;
    const grow = interpolate(frame, [0.1 * fps, 1.1 * fps], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
    return (
      <AbsoluteFill style={{ opacity: 1 - out }}>
        <div style={{ position: "absolute", left: cx, top: cy, transform: "translate(-50%,-50%)", display: "flex", flexDirection: "column", alignItems: "center" }}>
          {titulo}
          <div style={{ position: "relative", width: r * 2.6, height: r * 2.6 }}>
            <svg width={r * 2.6} height={r * 2.6} style={{ transform: "rotate(-90deg)" }}>
              <circle cx={r * 1.3} cy={r * 1.3} r={r} fill={`${brand.colors.background || "#000"}cc`} stroke={`${brand.colors.text}22`} strokeWidth={r * 0.32} />
              {dados.map((d, i) => {
                const frac = d.valor / total;
                const seg = (
                  <circle
                    key={i}
                    cx={r * 1.3}
                    cy={r * 1.3}
                    r={r}
                    fill="none"
                    stroke={d.destaque ? ac : i % 2 ? `${brand.colors.text}cc` : `${ac}66`}
                    strokeWidth={r * 0.32}
                    strokeDasharray={`${C * frac * grow} ${C}`}
                    strokeDashoffset={-C * acc * grow}
                  />
                );
                acc += frac;
                return seg;
              })}
            </svg>
          </div>
          <div style={{ display: "flex", gap: 22 * k, marginTop: 14 * k }}>
            {dados.map((d, i) => (
              <div key={i} style={{ ...fontCss(brand, "body"), fontSize: 0.03 * W, color: brand.colors.text, background: `${brand.colors.background || "#000"}b3`, padding: `${6 * k}px ${14 * k}px`, borderRadius: 10 * k, opacity: grow }}>
                <b style={{ color: d.destaque ? ac : brand.colors.text }}>{Math.round(d.valor * grow)}{suf}</b> {d.rotulo}
              </div>
            ))}
          </div>
        </div>
      </AbsoluteFill>
    );
  }
  // barras horizontais
  return (
    <AbsoluteFill style={{ opacity: 1 - out }}>
      <div style={{ position: "absolute", left: cx - largura / 2, width: largura, top: cy, transform: "translateY(-50%)" }}>
        {titulo}
        {dados.map((d, i) => {
          const t0 = (d.em ?? 0.15 + i * 0.25) * fps;
          const g = interpolate(frame - t0, [0, 0.8 * fps], [0, 1], { ...clamp, easing: easeOut });
          return (
            <div key={i} style={{ marginBottom: 14 * k, background: `${brand.colors.background || "#000"}b3`, borderRadius: 12 * k, padding: `${10 * k}px ${14 * k}px` }}>
              <div style={{ display: "flex", justifyContent: "space-between", ...fontCss(brand, "body"), fontSize: 0.03 * W, color: brand.colors.text, marginBottom: 8 * k }}>
                <span>{d.rotulo}</span>
                <b style={{ color: d.destaque ? ac : brand.colors.text }}>{Math.round(d.valor * g)}{suf}</b>
              </div>
              <div style={{ height: 14 * k, borderRadius: 8 * k, background: `${brand.colors.text}22`, overflow: "hidden" }}>
                <div style={{ width: `${(d.valor / max) * 100 * g}%`, height: "100%", borderRadius: 8 * k, background: d.destaque ? ac : `${brand.colors.text}bb` }} />
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- marcador à mão (círculo, sublinhado, seta, x)
// props: tipo "circulo" | "sublinhado" | "seta" | "x" | "check", x, y (0..1), largura, altura (frações), angulo (seta), cor
export const Marcador: React.FC<OverlayProps> = ({ props, brand, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const k = W / 1080;
  const out = exitProgress(frame, fps, duration, 0.2);
  const d = interpolate(frame, [0, (props.desenhar ?? 0.5) * fps], [0, 1], { ...clamp, easing: easeOut });
  const w = W * (props.largura ?? 0.3);
  const h = H * (props.altura ?? 0.08);
  const x = W * (props.x ?? 0.5);
  const y = H * (props.y ?? 0.5);
  const c = cor(brand, props.cor);
  const sw = (props.espessura ?? 7) * k;
  // traços com leve irregularidade (parecem feitos à mão)
  let path = "";
  if (props.tipo === "sublinhado") {
    path = `M ${-w / 2} 0 C ${-w / 6} ${h * 0.12}, ${w / 6} ${-h * 0.1}, ${w / 2} ${h * 0.05}`;
  } else if (props.tipo === "x") {
    path = `M ${-w / 2} ${-h / 2} L ${w / 2} ${h / 2} M ${w / 2} ${-h / 2} L ${-w / 2} ${h / 2}`;
  } else if (props.tipo === "check") {
    path = `M ${-w / 2} 0 L ${-w / 8} ${h / 2} L ${w / 2} ${-h / 2}`;
  } else if (props.tipo === "seta") {
    path = `M ${-w / 2} ${h * 0.3} C ${-w / 6} ${-h * 0.4}, ${w / 6} ${-h * 0.2}, ${w / 2} 0 M ${w / 2 - 34 * k} ${-24 * k} L ${w / 2} 0 L ${w / 2 - 30 * k} ${26 * k}`;
  } else {
    // círculo/elipse aberta, passa um pouco do ponto inicial
    const rx = w / 2;
    const ry = h / 2;
    path = `M ${rx * 0.95} ${-ry * 0.15} C ${rx * 1.05} ${ry * 0.9}, ${-rx * 1.05} ${ry * 1.05}, ${-rx} 0 C ${-rx * 1.0} ${-ry * 1.1}, ${rx * 0.9} ${-ry * 1.15}, ${rx * 1.02} ${ry * 0.15}`;
  }
  return (
    <AbsoluteFill style={{ opacity: 1 - out }}>
      <svg width={W} height={H} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
        <g transform={`translate(${x} ${y}) rotate(${props.angulo ?? 0})`}>
          <path d={path} fill="none" stroke={c} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - d} style={{ filter: "drop-shadow(0 3px 8px rgba(0,0,0,0.5))" }} />
        </g>
      </svg>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- texto atrás da pessoa (precisa do recorte)
// O render coloca a pessoa recortada por cima deste overlay. props: texto, y (centro 0..1), size (fração), cor,
// peso, entrada ("subir" | "escala" | "revelar")
export const TextoFundo: React.FC<OverlayProps> = ({ props, brand, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const out = exitProgress(frame, fps, duration, 0.3);
  const p = spring({ frame, fps, config: { damping: 15, stiffness: 120, mass: 0.8 } });
  const ent = props.entrada || "subir";
  const size = (props.size ?? 0.26) * W;
  const tr =
    ent === "escala" ? `scale(${0.6 + 0.4 * p})` : ent === "revelar" ? "none" : `translateY(${(1 - p) * size * 0.6}px)`;
  const clip = ent === "revelar" ? `inset(0 ${100 - 100 * interpolate(frame, [0, 0.6 * fps], [0, 1], clamp)}% 0 0)` : "none";
  return (
    <AbsoluteFill style={{ opacity: 1 - out }}>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: H * (props.y ?? 0.3),
          transform: `translateY(-50%) ${tr}`,
          textAlign: "center",
          ...fontCss(brand, "title"),
          fontWeight: props.peso ?? 800,
          fontSize: size,
          lineHeight: 0.9,
          letterSpacing: "-0.04em",
          color: cor(brand, props.cor || "accent"),
          textTransform: props.uppercase === false ? "none" : "uppercase",
          opacity: Math.min(1, p * 1.5),
          clipPath: clip,
        }}
      >
        {props.texto}
      </div>
    </AbsoluteFill>
  );
};
