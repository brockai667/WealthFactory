import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, MONO, SANS } from "./theme";

/* Animovane vrstvy nad ilustraciami - vsetko deterministicke (render po snimkach). */

const rnd = (i: number, k = 1) => {
  const x = Math.sin(i * 127.1 + k * 311.7) * 43758.5453;
  return x - Math.floor(x);
};

export const Rain: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width="1080" height="1920" style={{ position: "absolute", inset: 0 }}>
        {Array.from({ length: 90 }).map((_, i) => {
          const speed = 38 + rnd(i) * 30;
          const x = rnd(i, 2) * 1180 - 50;
          const y = ((rnd(i, 3) * 2200 + f * speed) % 2200) - 200;
          const l = 40 + rnd(i, 4) * 60;
          return <line key={i} x1={x} y1={y} x2={x - l * 0.18} y2={y + l} stroke="rgba(200,220,255,0.28)" strokeWidth={2 + rnd(i, 5) * 1.5} />;
        })}
      </svg>
    </AbsoluteFill>
  );
};

export const Dust: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none", mixBlendMode: "screen" }}>
      {Array.from({ length: 34 }).map((_, i) => {
        const x = 150 + rnd(i) * 780 + Math.sin(f * 0.02 + i) * 30;
        const y = ((300 + rnd(i, 2) * 1100 - f * (0.4 + rnd(i, 3) * 0.8)) % 1400 + 1400) % 1400 + 200;
        const s = 3 + rnd(i, 4) * 6;
        const o = 0.25 + 0.35 * Math.sin(f * 0.07 + i * 2);
        return <div key={i} style={{ position: "absolute", left: x, top: y, width: s, height: s, borderRadius: s,
          background: "rgba(255,220,150,1)", opacity: Math.max(0, o), filter: "blur(1px)" }} />;
      })}
    </AbsoluteFill>
  );
};

/* svetlo telefonu/lampy: pulzuje; x,y su relativne k obrazku (je vo vnutri transformovaneho kontajnera) */
export const Glow: React.FC<{ x: number; y: number; color: string }> = ({ x, y, color }) => {
  const f = useCurrentFrame();
  const o = 0.32 + 0.14 * Math.sin(f * 0.18) + 0.06 * Math.sin(f * 0.53);
  return (
    <div style={{ position: "absolute", left: `${x * 100}%`, top: `${y * 100}%`, width: 900, height: 900, marginLeft: -450, marginTop: -450,
      background: `radial-gradient(circle, ${color} 0%, rgba(0,0,0,0) 60%)`, opacity: o, mixBlendMode: "screen", pointerEvents: "none" }} />
  );
};

export const Steam: React.FC<{ x: number; y: number }> = ({ x, y }) => {
  const f = useCurrentFrame();
  return (
    <>
      {Array.from({ length: 7 }).map((_, i) => {
        const p = ((f * 0.012 + i / 7) % 1);
        return <div key={i} style={{ position: "absolute", left: `${x * 100}%`, top: `${y * 100}%`, width: 70 + p * 90, height: 70 + p * 90,
          marginLeft: -40 + Math.sin(f * 0.05 + i) * 30, marginTop: -p * 330, borderRadius: "50%", background: "rgba(255,255,255,0.55)",
          opacity: (1 - p) * 0.45 * Math.min(1, p * 5), filter: "blur(18px)" }} />;
      })}
    </>
  );
};

/* posun kamery z ruky / vibracia / klopanie -> transform pre kontajner obrazka */
export const shakeOf = (f: number, fx: string[], knockAt: number | null) => {
  let x = 0, y = 0, r = 0;
  if (fx.includes("handheld")) {
    x += Math.sin(f * 0.11) * 6 + Math.sin(f * 0.37) * 3;
    y += Math.cos(f * 0.09) * 5 + Math.sin(f * 0.29) * 2;
    r += Math.sin(f * 0.07) * 0.35;
  }
  if (fx.includes("buzz")) {
    const on = Math.floor(f / 12) % 2 === 0 ? 1 : 0;
    x += on * Math.sin(f * 3.1) * 4;
    y += on * Math.cos(f * 2.7) * 3;
  }
  if (knockAt !== null) {
    for (const k of [knockAt, knockAt + 7]) {
      const d = f - k;
      if (d >= 0 && d < 8) {
        const a = (1 - d / 8) * 16;
        x += Math.sin(d * 2.4) * a;
        y += Math.cos(d * 3.1) * a * 0.6;
      }
    }
  }
  return `translate(${x}px, ${y}px) rotate(${r}deg)`;
};

/* SMS bublina od bratranca */
export const Bubble: React.FC<{ from: string; text: string; at: number }> = ({ from, text, at }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: f - at, fps, config: { damping: 12 } });
  if (f < at) return null;
  return (
    <div style={{ position: "absolute", top: 330, left: 70, right: 70, transform: `translateY(${(1 - s) * -80}px) scale(${0.8 + 0.2 * s})`, opacity: s }}>
      <div style={{ background: "rgba(245,245,247,0.96)", borderRadius: 34, padding: "26px 34px", boxShadow: "0 20px 50px rgba(0,0,0,0.5)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 10 }}>
          <div style={{ width: 54, height: 54, borderRadius: 14, background: C.green, display: "flex", alignItems: "center", justifyContent: "center",
            color: "#fff", fontFamily: SANS, fontWeight: 900, fontSize: 30 }}>✉</div>
          <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 36, color: "#111" }}>{from}</div>
          <div style={{ marginLeft: "auto", fontFamily: SANS, fontWeight: 600, fontSize: 28, color: "#888" }}>now</div>
        </div>
        <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 46, color: "#111", lineHeight: 1.2 }}>{text}</div>
      </div>
    </div>
  );
};

/* zmeskane hovory: kopa notifikacii + pocitadlo do 40 */
export const Calls: React.FC<{ total?: number }> = ({ total = 40 }) => {
  const f = useCurrentFrame();
  const n = Math.min(total, Math.floor(interpolate(f, [6, 70], [0, total], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })));
  const shown = Array.from({ length: Math.min(n, 5) }).map((_, k) => n - 1 - k);
  const num = (i: number) => `+1 (${200 + Math.floor(rnd(i) * 700)}) 555-0${String(100 + Math.floor(rnd(i, 2) * 99)).slice(1)}`;
  return (
    <>
      <div style={{ position: "absolute", top: 300, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
        <div style={{ background: C.red, color: "#fff", fontFamily: MONO, fontWeight: 800, fontSize: 46, padding: "12px 30px", borderRadius: 40,
          boxShadow: "0 10px 30px rgba(0,0,0,0.5)" }}>{n} MISSED CALLS</div>
      </div>
      <div style={{ position: "absolute", top: 420, left: 80, right: 80 }}>
        {shown.map((i, k) => (
          <div key={i} style={{ background: "rgba(30,32,40,0.88)", borderRadius: 26, padding: "18px 26px", marginBottom: 14, display: "flex",
            alignItems: "center", gap: 18, opacity: 1 - k * 0.17, transform: `scale(${1 - k * 0.03})`, border: "2px solid rgba(255,255,255,0.08)" }}>
            <div style={{ width: 50, height: 50, borderRadius: 25, background: C.red, color: "#fff", display: "flex", alignItems: "center",
              justifyContent: "center", fontSize: 28 }}>✆</div>
            <div>
              <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 32, color: "#fff" }}>Missed call · Unknown</div>
              <div style={{ fontFamily: MONO, fontWeight: 500, fontSize: 28, color: "rgba(255,255,255,0.6)" }}>{num(i)}</div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
};
