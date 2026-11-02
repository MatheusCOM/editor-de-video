import React from "react";
import { AbsoluteFill, Img, interpolate, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import type { BRoll as BRollT, Brand } from "../types";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

export const BRollClip: React.FC<{ b: BRollT; brand: Brand }> = ({ b, brand }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const d = (b.end - b.start) * fps;
  const fade = interpolate(frame, [0, 3, d - 3, d], [0, 1, 1, 0], clamp);
  const kb = b.ken_burns !== false ? interpolate(frame, [0, d], [1.0, 1.12], clamp) : 1;
  const src = staticFile(b.src);
  const media =
    b.kind === "image" ? (
      <Img src={src} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${kb})` }} />
    ) : (
      <OffthreadVideo
        src={src}
        muted
        startFrom={Math.round((b.src_in || 0) * fps)}
        style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${kb})` }}
      />
    );
  if (b.mode === "pip") {
    const k = W / 1080;
    return (
      <AbsoluteFill>
        <div
          style={{
            position: "absolute",
            width: W * 0.62,
            height: W * 0.62 * 0.75,
            left: W * 0.19,
            top: H * 0.16,
            overflow: "hidden",
            borderRadius: brand.radius * 1.5 * k,
            border: `${6 * k}px solid ${brand.colors.secondary || "#fff"}`,
            boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
            opacity: fade,
            transform: `scale(${0.85 + 0.15 * fade})`,
          }}
        >
          {media}
        </div>
      </AbsoluteFill>
    );
  }
  if (b.mode === "split_top") {
    return (
      <AbsoluteFill>
        <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H / 2, overflow: "hidden", opacity: fade }}>
          {media}
        </div>
      </AbsoluteFill>
    );
  }
  return <AbsoluteFill style={{ opacity: fade, overflow: "hidden" }}>{media}</AbsoluteFill>;
};
