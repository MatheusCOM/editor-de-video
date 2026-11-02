import { Easing, interpolate, spring } from "remotion";

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** Escala de "pop" (0 → overshoot → 1). */
export function popIn(frame: number, fps: number, delay = 0, stiffness = 220) {
  return spring({ frame: frame - delay, fps, config: { damping: 12, stiffness, mass: 0.6 } });
}

/** Opacidade de entrada/saída em segundos (local à Sequence). */
export function fadeInOut(frame: number, fps: number, durationSec: number, inSec = 0.15, outSec = 0.15) {
  const d = durationSec * fps;
  return interpolate(frame, [0, inSec * fps, Math.max(inSec * fps + 1, d - outSec * fps), d], [0, 1, 1, 0], clamp);
}

export function slideIn(frame: number, fps: number, from: number, delay = 0, dur = 0.35) {
  return interpolate(frame - delay, [0, dur * fps], [from, 0], { ...clamp, easing: Easing.out(Easing.cubic) });
}

export function exitProgress(frame: number, fps: number, durationSec: number, outSec = 0.25) {
  const d = durationSec * fps;
  return interpolate(frame, [d - outSec * fps, d], [0, 1], { ...clamp, easing: Easing.in(Easing.cubic) });
}

export function textShadow(stroke: number, color: string, shadow = true) {
  const s = stroke;
  const parts: string[] = [];
  if (s > 0) {
    const steps = 16;
    for (let i = 0; i < steps; i++) {
      const a = (i / steps) * Math.PI * 2;
      parts.push(`${(Math.cos(a) * s).toFixed(1)}px ${(Math.sin(a) * s).toFixed(1)}px 0 ${color}`);
    }
  }
  if (shadow) parts.push(`0 ${Math.max(4, s * 1.2)}px ${Math.max(10, s * 3)}px rgba(0,0,0,0.55)`);
  return parts.join(", ");
}
