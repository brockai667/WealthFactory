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
  pause?: number;
  t0: number;
  t1: number;
};
/* volitelny uvodny hak (0-3 s). "drain" = kodova karta (beaty so shot "hook"): cislo sa zrazi z `from` na `to`.
   "recap" = prekryv nad obrazkami prvych `beats` beatov (PART N · YOU VOTED: X + nadpis + cervena peciatka dosledku). */
export type Hook = {
  kind: "drain" | "recap";
  style?: "card" | "jackpot" | "ticket";   // drain: vzhlad (default "card" = kremova karta)
  bg?: string;                     // drain jackpot/ticket: obrazok scenky v pozadi (napr. "img01")
  beats?: number;                  // kolko uvodnych beatov hak pokryva (default 2)
  top?: [string, string];          // drain: nadpis pred / po zrazeni ("YOU WON", "YOU GET")
  from?: number;
  to?: number;
  sub?: string;                    // drain: otazka pod cislom ("WHERE DID $62M GO?"), "$..." cast cervena
  chips?: { beat: number; items: string[] };   // cervene stitky-odpovede nad obrazkom v danom beate
  tag?: string;                    // recap: "PART 2 · YOU VOTED: CLAIM"
  big?: string;                    // recap: hlavny riadok
  stamp?: string;                  // recap: dosledok (cervena peciatka)
  stamp_beat?: number;             // recap: v ktorom beate peciatka udrie (default 1)
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
  hook?: Hook;
  beats: Beat[];
  words: Word[];
  fps: number;
  duration: number;
  voice: string;
  music: string;
  music_gain: number;
};

export const money = (n: number) => "$" + Math.round(n).toLocaleString("en-US");
