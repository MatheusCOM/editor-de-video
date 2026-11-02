import React from "react";
import { AbsoluteFill, Easing, interpolate, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import type { MainProps, Segment, Zoom } from "../types";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

export function segmentAt(segments: Segment[], t: number) {
  let acc = 0;
  for (const s of segments) {
    const d = (s.out - s.in) / (s.speed || 1);
    if (t < acc + d) return s;
    acc += d;
  }
  return segments[segments.length - 1];
}

export function zoomAt(zooms: Zoom[], t: number, fps: number) {
  let scale = 1;
  let fx: number | undefined;
  let fy: number | undefined;
  for (const z of zooms) {
    if (t < z.start || t >= z.end) continue;
    const type = z.type || "punch";
    let k = 1;
    if (type === "punch") {
      const ramp = 3 / fps; // 3 frames
      k = interpolate(t, [z.start, z.start + ramp], [0, 1], clamp);
    } else if (type === "slow") {
      k = interpolate(t, [z.start, z.end], [0, 1], { ...clamp, easing: Easing.inOut(Easing.sin) });
    } else {
      const r = Math.min(0.35, (z.end - z.start) / 2);
      k = interpolate(t, [z.start, z.start + r, z.end - r, z.end], [0, 1, 1, 0], {
        ...clamp,
        easing: Easing.inOut(Easing.cubic),
      });
    }
    scale *= 1 + (z.scale - 1) * k;
    if (z.x !== undefined) fx = z.x;
    if (z.y !== undefined) fy = z.y;
  }
  return { scale, fx, fy };
}

type Box = { left: number; top: number; width: number; height: number };

function coverBox(W: number, H: number, w: number, h: number, zoom: number, fx: number, fy: number, eyeLine: number): Box {
  const s = Math.max(W / w, H / h) * zoom;
  const dw = w * s;
  const dh = h * s;
  let left = W / 2 - fx * dw;
  let top = H * eyeLine - fy * dh;
  left = Math.min(0, Math.max(W - dw, left));
  top = Math.min(0, Math.max(H - dh, top));
  return { left, top, width: dw, height: dh };
}

function containBox(W: number, H: number, w: number, h: number, zoom: number, yCenter: number): Box {
  const s = Math.min(W / w, H / h) * zoom;
  const dw = w * s;
  const dh = h * s;
  return { left: (W - dw) / 2, top: Math.max(0, Math.min(H - dh, H * yCenter - dh / 2)), width: dw, height: dh };
}

export const VideoLayer: React.FC<{ p: MainProps }> = ({ p }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const t = frame / fps;
  const { edl, sourceSize } = p;
  const seg = segmentAt(edl.segments, t);
  const z = zoomAt(edl.zooms, t, fps);
  const fx = z.fx ?? seg.focus?.x ?? 0.5;
  const fy = z.fy ?? seg.focus?.y ?? 0.4;
  const mode = edl.reframe?.mode || "cover";
  const src = staticFile(p.video);
  const srcAspect = sourceSize.width / sourceSize.height;
  const dstAspect = W / H;
  // se o bruto já tem praticamente o mesmo formato, "blur" vira "cover"
  const effective = mode === "blur" && Math.abs(srcAspect - dstAspect) < 0.15 ? "cover" : mode;

  if (effective === "cover") {
    const box = coverBox(W, H, sourceSize.width, sourceSize.height, z.scale, fx, fy, 0.42);
    return (
      <AbsoluteFill style={{ backgroundColor: "black", overflow: "hidden" }}>
        <OffthreadVideo src={src} muted style={{ position: "absolute", ...box }} />
      </AbsoluteFill>
    );
  }
  const fg = containBox(W, H, sourceSize.width, sourceSize.height, z.scale, 0.5);
  const bg = coverBox(W, H, sourceSize.width, sourceSize.height, 1.15, fx, fy, 0.5);
  return (
    <AbsoluteFill style={{ backgroundColor: edl.reframe?.background || "black", overflow: "hidden" }}>
      {effective === "blur" ? (
        <OffthreadVideo
          src={src}
          muted
          style={{ position: "absolute", ...bg, filter: "blur(38px) brightness(0.6) saturate(1.2)" }}
        />
      ) : null}
      <OffthreadVideo src={src} muted style={{ position: "absolute", ...fg }} />
    </AbsoluteFill>
  );
};
