// Componentes do formato "Yap" (fala corrida com cabeçalho de contexto no topo).
import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { clamp } from "../../lib/anim";
import { fontCss } from "../../lib/fonts";
import { RichText, type OverlayProps } from "./index";

type Linha = {
  texto: string;
  estilo?: "titulo" | "sub" | "citacao" | "item" | "numero";
  icone?: string; // "x", "check" ou um emoji
  em?: number; // segundos depois do início do cabeçalho (padrão 0)
  maquina?: boolean; // efeito de digitação (padrão: só em citação)
  dur_maquina?: number; // segundos para digitar a linha inteira (padrão: ~20 caracteres/s)
};

const TAM: Record<string, number> = { titulo: 0.06, numero: 0.078, item: 0.052, citacao: 0.046, sub: 0.04 };

function Icone({ nome, size }: { nome: string; size: number }) {
  if (nome === "x")
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" style={{ flex: "none" }}>
        <path d="M5 5 L19 19 M19 5 L5 19" stroke="#E5322D" strokeWidth={4.2} strokeLinecap="round" />
      </svg>
    );
  if (nome === "check")
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" style={{ flex: "none" }}>
        <path d="M4 12.5 L9.5 18 L20 6" stroke="#2DBE60" strokeWidth={4.2} strokeLinecap="round" strokeLinejoin="round" fill="none" />
      </svg>
    );
  return <span style={{ fontSize: size * 0.95, lineHeight: 1, flex: "none" }}>{nome}</span>;
}

/** Cabeçalho de contexto no topo da tela. Troca a cada ideia da fala; as linhas podem entrar em tempos
 *  diferentes (lista que cresce) e as citações aparecem digitando. Sem caixa: texto branco com sombra suave. */
export const Cabecalho: React.FC<OverlayProps> = ({ props, brand, safe, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const t = frame / fps;
  const k = W / 1080;
  const linhas: Linha[] = (props.linhas || (props.texto ? [{ texto: props.texto }] : [])).map((l: any) =>
    typeof l === "string" ? { texto: l } : l,
  );
  const italico = props.italico ?? true;
  const cor = props.cor || brand.colors.text || "#fff";
  const acento = props.acento || brand.colors.accent || "#FFD400";
  const sombra = "0 2px 10px rgba(0,0,0,0.45), 0 1px 2px rgba(0,0,0,0.35)";
  const top = H * (props.y ?? safe.top + 0.015);
  const sai = interpolate(t, [duration - 0.12, duration], [1, 0], clamp);
  const fonte = fontCss(brand, props.fonte || "body");

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          top,
          left: W * 0.08,
          right: W * 0.08,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 6 * k,
          opacity: sai,
          textAlign: "center",
        }}
      >
        {linhas.map((l, i) => {
          const est = l.estilo || (i === 0 ? "titulo" : "sub");
          const t0 = l.em ?? 0;
          if (t < t0) return null;
          const lt = t - t0;
          const size = W * (props.tamanho ?? 1) * (TAM[est] ?? 0.05);
          const maquina = l.maquina ?? est === "citacao";
          const plano = l.texto.replace(/\*/g, "");
          let texto: React.ReactNode = <RichText text={l.texto} accent={acento} />;
          let op = 1;
          if (maquina) {
            const durM = l.dur_maquina ?? Math.max(0.4, plano.length / 20);
            const n = Math.round(interpolate(lt, [0, durM], [0, plano.length], clamp));
            // reserva o espaço do texto todo (invisível) para a linha não "pular" enquanto digita
            texto = (
              <span style={{ position: "relative", display: "inline-block" }}>
                <span style={{ visibility: "hidden" }}>{plano}</span>
                <span style={{ position: "absolute", left: 0, right: 0, top: 0, textAlign: "center" }}>
                  <span>{plano.slice(0, n)}</span>
                  <span style={{ visibility: "hidden" }}>{plano.slice(n)}</span>
                </span>
              </span>
            );
          } else {
            op = interpolate(lt, [0, 0.08], [0, 1], clamp);
          }
          const pop = maquina ? 1 : 0.9 + 0.1 * spring({ frame: Math.round(lt * fps), fps, config: { damping: 14, stiffness: 320 } });
          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: size * 0.22,
                ...fonte,
                fontWeight: est === "sub" || est === "citacao" ? 600 : 800,
                fontStyle: italico ? "italic" : "normal",
                fontSize: size,
                lineHeight: 1.12,
                color: cor,
                textShadow: sombra,
                opacity: op,
                transform: `scale(${pop})`,
                maxWidth: "100%",
              }}
            >
              {l.icone ? <Icone nome={l.icone} size={size * 0.9} /> : null}
              <span>{texto}</span>
            </div>
          );
        })}
        {props.emojis ? (
          <div style={{ display: "flex", gap: 8 * k, marginTop: 4 * k }}>
            {Array.from(String(props.emojis)).filter((c) => c.trim()).map((e, i) => {
              const s = spring({ frame: frame - Math.round((props.emojis_em ?? 0.15) * fps) - i * 3, fps, config: { damping: 10, stiffness: 260 } });
              return (
                <span key={i} style={{ fontSize: W * 0.07 * (props.tamanho ?? 1), transform: `scale(${s})`, display: "inline-block" }}>
                  {e}
                </span>
              );
            })}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

/** Imagem pequena "colada" no canto (print de estudo, post, foto), com borda e sombra, entrando com pop. */
export const Recorte: React.FC<OverlayProps> = ({ props, brand, duration }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const t = frame / fps;
  const s = spring({ frame, fps, config: { damping: 12, stiffness: 200, mass: 0.6 } });
  const sai = interpolate(t, [duration - 0.15, duration], [1, 0], clamp);
  const largura = W * (props.largura ?? 0.26);
  const src = /^(https?:|data:)/.test(props.src || "") ? props.src : staticFile(props.src);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: W * (props.x ?? 0.78),
          top: H * (props.y ?? 0.2),
          width: largura,
          transform: `translate(-50%,-50%) scale(${(0.6 + 0.4 * s) * (props.escala ?? 1)}) rotate(${props.giro ?? 0}deg)`,
          opacity: Math.min(1, s * 1.5) * sai,
          borderRadius: 10 * (W / 1080),
          overflow: "hidden",
          boxShadow: "0 12px 34px rgba(0,0,0,0.38)",
          border: props.borda === false ? "none" : `${3 * (W / 1080)}px solid #fff`,
          background: "#fff",
        }}
      >
        <Img src={src} style={{ width: "100%", display: "block" }} />
      </div>
      {props.legenda ? (
        <div
          style={{
            position: "absolute",
            left: W * (props.x ?? 0.78),
            top: H * (props.y ?? 0.2) + largura * (props.proporcao ?? 1.25) * 0.5 + 10,
            transform: "translateX(-50%)",
            ...fontCss(brand, "body"),
            fontWeight: 700,
            fontSize: W * 0.026,
            color: "#fff",
            textShadow: "0 2px 8px rgba(0,0,0,0.6)",
            opacity: sai * Math.min(1, s * 1.5),
            whiteSpace: "nowrap",
          }}
        >
          {props.legenda}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
