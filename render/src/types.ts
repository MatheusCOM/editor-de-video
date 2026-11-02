export type Word = {
  text: string;
  start: number;
  end: number;
  emphasis?: boolean;
  color?: string;
  emoji?: string;
};

export type Segment = { in: number; out: number; focus?: { x: number; y: number }; speed?: number };

export type Zoom = {
  start: number;
  end: number;
  scale: number;
  type?: "punch" | "slow" | "smooth";
  x?: number;
  y?: number;
};

export type Overlay = {
  type: string;
  start: number;
  end: number;
  props?: Record<string, any>;
};

export type BRoll = {
  src: string; // já reescrito para caminho em public/
  start: number;
  end: number;
  src_in?: number;
  mode?: "full" | "pip" | "split_top";
  ken_burns?: boolean;
  kind?: "video" | "image";
};

export type CaptionStyle = {
  enabled?: boolean;
  style?: "pop" | "karaoke" | "box" | "plain" | "typewriter";
  reveal?: "page" | "word";
  words_per_line?: number;
  max_chars?: number;
  lines?: number;
  position?: number; // 0..1 (centro vertical do bloco)
  size?: number; // fração da largura (altura da fonte)
  uppercase?: boolean;
  color?: string;
  highlight_color?: string;
  box_color?: string;
  stroke?: number; // px a 1080 de largura
  stroke_color?: string;
  shadow?: boolean;
  font?: "caption" | "title" | "body" | "mono";
  weight?: number;
  tracking?: string;
  animation?: "pop" | "slide" | "fade" | "none";
  emphasis_scale?: number;
  background?: string | null; // faixa atrás do texto
  words: Word[];
};

export type FontRef = { family: string; weight: number; tracking?: string };

export type Brand = {
  name: string;
  colors: Record<string, string>;
  fonts: {
    title: FontRef;
    caption: FontRef;
    body: FontRef;
    mono?: FontRef;
    files: { family: string; weight: number; file: string; style?: string }[];
  };
  logo: { file: string | null; text?: string; position: string; size: number; opacity: number };
  radius: number;
  handle?: string;
  cta_default?: string;
  medico?: { nome?: string; crm?: string; rqe?: string; especialidade?: string };
  assinatura?: { nome?: string; registro_tipo?: string; registro?: string; extra?: string; cargo?: string };
  segmento?: string;
};

export type Safe = { top: number; bottom: number; left: number; right: number };

export type MainProps = {
  edl: {
    fps: number;
    duration: number;
    segments: Segment[];
    captions: CaptionStyle;
    zooms: Zoom[];
    overlays: Overlay[];
    broll: BRoll[];
    reframe?: { mode?: "cover" | "blur" | "contain"; background?: string; region?: { top?: number; bottom?: number } };
    style?: Record<string, any>;
  };
  brand: Brand;
  format: string;
  width: number;
  height: number;
  video: string;
  sourceSize: { width: number; height: number };
  safe: Safe;
};
