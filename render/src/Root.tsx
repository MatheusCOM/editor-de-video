import React from "react";
import { Composition } from "remotion";
import { Main } from "./Main";
import type { MainProps } from "./types";

const defaultProps: MainProps = {
  edl: {
    fps: 30,
    duration: 3,
    segments: [{ in: 0, out: 3 }],
    captions: { enabled: false, words: [] },
    zooms: [],
    overlays: [],
    broll: [],
  },
  brand: {
    name: "Padrão",
    colors: { primary: "#111", secondary: "#fff", accent: "#FFD400", text: "#fff" },
    fonts: {
      title: { family: "sans-serif", weight: 900 },
      caption: { family: "sans-serif", weight: 800 },
      body: { family: "sans-serif", weight: 600 },
      files: [],
    },
    logo: { file: null, position: "top-right", size: 0.14, opacity: 0.9 },
    radius: 18,
  },
  format: "9x16",
  width: 1080,
  height: 1920,
  video: "",
  sourceSize: { width: 1080, height: 1920 },
  safe: { top: 0.1, bottom: 0.18, left: 0.06, right: 0.06 },
};

export const Root: React.FC = () => (
  <Composition
    id="Main"
    component={Main as any}
    defaultProps={defaultProps}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={90}
    calculateMetadata={({ props }) => {
      const p = props as unknown as MainProps;
      return {
        width: p.width,
        height: p.height,
        fps: p.edl.fps,
        durationInFrames: Math.max(1, Math.round(p.edl.duration * p.edl.fps)),
      };
    }}
  />
);
