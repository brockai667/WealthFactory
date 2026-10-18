import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

export const W = 1080;
export const H = 1920;
export const FPS = 30;

export const SANS = loadInter("normal", { weights: ["600", "800", "900"], subsets: ["latin"] }).fontFamily;
export const MONO = loadMono("normal", { weights: ["500", "700", "800"], subsets: ["latin"] }).fontFamily;

export const C = {
  gold: "#F4B41A",
  goldDeep: "#C98A00",
  cream: "#F2EADB",
  ink: "#151515",
  dark: "#0E0F12",
  red: "#D7263D",
  green: "#2E9E5B",
  grey: "rgba(255,255,255,0.55)",
};

export type Beat = {
  text: string;
  shot: string;
  hud?: [number, number, number];
  zoom?: "in" | "out";
  label?: string;
  day?: number;
  vote?: boolean;
  fx?: string[];
  glow?: [number, number, string];
  phase?: number;
  sfx?: string;
  knock?: string;
  t0: number;
  t1: number;
};
export type Word = { w: string; s: number; e: number; b: number };
export type Ep = {
  series: string;
  tagline: string;
  part: number;
  title: string;
  vote: [string, string];
  hud_labels: [string, string, string];
  cards: Record<string, any>;
  bubble?: { from: string; text: string; at: number; word?: string };
  beats: Beat[];
  words: Word[];
  fps: number;
  duration: number;
  voice: string;
  music: string;
  music_gain: number;
};

export const money = (n: number) => "$" + Math.round(n).toLocaleString("en-US");
