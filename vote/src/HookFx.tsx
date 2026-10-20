import React from "react";
import { AbsoluteFill, Img, interpolate, interpolateColors, spring, staticFile, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import { C, Hook, MONO, SANS, money } from "./theme";

/* Bohatsie varianty uvodneho haku (hook.style): "jackpot" (V2) a "ticket" (V3). Rovnaky obsah aj casovanie ako "card" (V1). */

const rnd = (i: number, k = 1) => {
  const x = Math.sin(i * 127.1 + k * 311.7) * 43758.5453;
  return x - Math.floor(x);
};
const cl = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/* spolocny stav: zrazenie cisla od d0 (zaciatok 2. VO riadku), dopad, otazka, odchod */
const useDrain = (h: Hook, len: number, ph: number[]) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const from = h.from ?? 100000000;
  const to = h.to ?? from;
  const d0 = ph.length ? ph[0] : Math.round(len * 0.5);
  const ROLL = 20;
  const k = interpolate(f, [d0, d0 + ROLL], [0, 1], { ...cl, easing: Easing.out(Easing.cubic) });
  const raw = from + (to - from) * k;
  const val = k >= 1 ? to : Math.round(raw / 1000) * 1000 + (k > 0 ? Math.floor(f * 7919) % 1000 : 0);
  const landAt = d0 + ROLL;
  const land = spring({ frame: f - landAt, fps, config: { damping: 10, stiffness: 260 } });
  const thump = f >= landAt ? 1 + 0.08 * Math.sin(Math.min(1, land) * Math.PI) : 1;
  const subAt = landAt + 2;
  const sub = f >= subAt ? spring({ frame: f - subAt, fps, config: { damping: 9, stiffness: 300 } }) : 0;
  const slamShake = f >= subAt && f < subAt + 9 ? Math.sin((f - subAt) * 2.9) * (9 - (f - subAt)) * 2.6 : 0;
  const top = h.top ?? ["YOU WON", "YOU GET"];
  const out = interpolate(f, [len - 8, len], [0, 1], { ...cl, easing: Easing.in(Easing.cubic) });
  return { f, fps, d0, k, val, land, thump, sub, slamShake, top, out, from, to, subAt };
};

const redMoney = (s: string, red: string) =>
  s.split(/(\$[0-9][0-9.,]*[MK]?)/).map((p, i) => (p.startsWith("$") ? <span key={i} style={{ color: red }}>{p}</span> : p));

/* rozmazany stmaveny obrazok scenky v pozadi */
const Backdrop: React.FC<{ img?: string; dim: number; blur: number; gray: number; scale: number }> = ({ img, dim, blur, gray, scale }) => (
  <AbsoluteFill style={{ backgroundColor: "#07080a", overflow: "hidden" }}>
    {img ? (
      <Img src={staticFile(`img/${img}.jpg`)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${scale})`,
        filter: `blur(${blur}px) brightness(${dim}) saturate(${1 - gray}) contrast(1.1)` }} />
    ) : null}
  </AbsoluteFill>
);

/* ---------------- V2 "jackpot": tmave pozadie, luce, padajuce bankovky + konfety, ziariaci displej ---------------- */
const Bill: React.FC<{ w: number; burn: number }> = ({ w, burn }) => (
  <div style={{ width: w, height: w * 0.46, borderRadius: 6, background: interpolateColors(burn, [0, 0.5, 1], ["#3f8f57", "#8a5a22", "#c0281e"]),
    border: `3px solid ${interpolateColors(burn, [0, 1], ["#1f5c35", "#5c0f0a"])}`, boxShadow: "0 6px 14px rgba(0,0,0,0.45)",
    display: "flex", alignItems: "center", justifyContent: "center" }}>
    <div style={{ width: w * 0.3, height: w * 0.3, borderRadius: "50%", border: `3px solid rgba(255,255,255,${0.45 - 0.3 * burn})`,
      display: "flex", alignItems: "center", justifyContent: "center", fontFamily: SANS, fontWeight: 900, fontSize: w * 0.2,
      color: `rgba(255,255,255,${0.7 - 0.4 * burn})` }}>$</div>
  </div>
);

export const HookJackpot: React.FC<{ h: Hook; len: number; ph: number[] }> = ({ h, len, ph }) => {
  const { f, fps, d0, k, val, thump, sub, slamShake, top, out, subAt } = useDrain(h, len, ph);
  const after = Math.max(0, f - d0);
  const gray = interpolate(f, [d0, d0 + 16], [0, 0.9], cl);
  const punch = interpolate(f, [0, 10], [1.22, 1.0], { ...cl, easing: Easing.out(Easing.cubic) }) * (f >= subAt ? 1 + 0.03 * Math.max(0, 1 - (f - subAt) / 8) : 1);
  const pop = spring({ frame: f, fps, config: { damping: 9, stiffness: 240 } });
  const flash = interpolate(f, [1, 2, 6], [0, 0.3, 0], cl) + interpolate(f - d0, [0, 2, 7], [0, 0.18, 0], cl);
  const rays = interpolate(f, [d0, d0 + 12], [1, 0], cl);
  const numCol = interpolateColors(k, [0, 0.5, 1], ["#43FF8E", "#FFB13B", "#FF2E4D"]);
  const glowCol = interpolateColors(k, [0, 0.5, 1], ["rgba(40,255,130,0.85)", "rgba(255,170,40,0.8)", "rgba(255,30,60,0.9)"]);
  const frameCol = interpolateColors(k, [0, 1], [C.gold, "#FF2E4D"]);
  const fade = Math.min(1, out * 4);
  const DOCK_Y = 1000;
  return (
    <AbsoluteFill style={{ backgroundColor: "#000", overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `scale(${punch * (1 + 0.25 * out)}) translateX(${slamShake}px)` }}>
        <Backdrop img={h.bg} dim={0.42 - 0.12 * gray} blur={7} gray={gray} scale={1.12 + f * 0.0015} />
        {/* cervena vineta po zrazeni */}
        <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 35%, rgba(120,0,10,${0.55 * gray}) 100%)` }} />
        {/* zlate luce + ziara */}
        <AbsoluteFill style={{ opacity: rays,
          background: `repeating-conic-gradient(from ${f * 0.9}deg at 50% 52%, rgba(255,200,70,0.30) 0deg 5deg, rgba(0,0,0,0) 5deg 15deg)`,
          WebkitMaskImage: "radial-gradient(circle at 50% 52%, #000 0%, rgba(0,0,0,0.6) 30%, rgba(0,0,0,0) 62%)",
          maskImage: "radial-gradient(circle at 50% 52%, #000 0%, rgba(0,0,0,0.6) 30%, rgba(0,0,0,0) 62%)" }} />
        <AbsoluteFill style={{ opacity: 0.6 * rays, background: "radial-gradient(circle at 50% 52%, rgba(255,190,60,0.55) 0%, rgba(0,0,0,0) 45%)" }} />
        {/* konfety */}
        {Array.from({ length: 70 }).map((_, i) => {
          const sp = 9 + rnd(i) * 9;
          const x = rnd(i, 2) * 1120 - 20 + Math.sin(f * 0.15 + i) * 26;
          const y = ((rnd(i, 3) * 2100 + f * sp) % 2100) - 120;
          const o = interpolate(f, [d0, d0 + 8], [1, 0], cl);
          const cols = [C.gold, "#ffffff", "#43FF8E", "#ffd86b"];
          return <div key={`c${i}`} style={{ position: "absolute", left: x, top: y, width: 12 + rnd(i, 4) * 8, height: 22 + rnd(i, 5) * 10,
            background: cols[i % 4], opacity: o * 0.9, borderRadius: 2, transform: `rotate(${f * (6 + rnd(i, 6) * 10) + i * 40}deg) scaleX(${Math.cos(f * 0.3 + i)})` }} />;
        })}
        {/* bankovky: padaju, po d0 sa otocia, zhoria do cervena a odletia hore */}
        {Array.from({ length: 22 }).map((_, i) => {
          const sp = 14 + rnd(i, 7) * 12;
          const x0 = rnd(i, 8) * 1180 - 120;
          const yAt = (fr: number) => ((rnd(i, 9) * 2300 + fr * sp) % 2300) - 260;
          const yd = yAt(Math.min(f, d0));
          const y = f < d0 ? yd : yd - after * after * 2.2 - after * 6;
          const rot = (f < d0 ? f : d0 + after * 4) * (2 + rnd(i, 10) * 4) * (i % 2 ? 1 : -1) + i * 33;
          const burn = interpolate(after, [0, 10], [0, 1], cl);
          const o = interpolate(after, [6, 20], [1, 0], cl);
          const w = 130 + rnd(i, 11) * 70;
          return <div key={`b${i}`} style={{ position: "absolute", left: x0 + (f < d0 ? Math.sin(f * 0.08 + i) * 30 : 0), top: y, opacity: o,
            transform: `rotate(${rot}deg) rotateX(${Math.sin(f * 0.12 + i) * 50}deg)`, filter: i % 3 === 0 ? "blur(2px)" : undefined }}>
            <Bill w={w} burn={burn} /></div>;
        })}
      </AbsoluteFill>
      <AbsoluteFill style={{ transform: `translateX(${slamShake}px) scale(${0.86 + 0.14 * pop})` }}>
        {/* text */}
        <div style={{ opacity: 1 - fade }}>
          <div style={{ position: "absolute", top: 660, left: 0, right: 0, textAlign: "center", fontFamily: SANS, fontWeight: 900, fontSize: 156,
            letterSpacing: -5, lineHeight: 1, color: "#fff", WebkitTextStroke: "5px #000", paintOrder: "stroke fill",
            textShadow: f < d0 ? "0 0 40px rgba(255,190,60,0.9), 0 8px 0 rgba(0,0,0,0.6)" : "0 0 30px rgba(255,40,60,0.7), 0 8px 0 rgba(0,0,0,0.6)" }}>
            {f < d0 ? top[0] : top[1]}
          </div>
        </div>
        <div style={{ position: "absolute", top: 860, left: 30, right: 30, display: "flex", justifyContent: "center",
          transform: `translate(${(230 - 540) * out}px, ${(152 - DOCK_Y) * out}px) scale(${(1 - 0.72 * out) * thump})` }}>
          <div style={{ padding: "18px 26px", borderRadius: 26, background: "rgba(6,8,10,0.86)", border: `6px solid ${frameCol}`,
            boxShadow: `0 0 50px ${glowCol}, inset 0 0 30px rgba(0,0,0,0.8)`, opacity: 1 - 0.4 * out }}>
            <div style={{ fontFamily: MONO, fontWeight: 800, fontSize: 140, letterSpacing: -6, lineHeight: 1.15, color: numCol,
              textShadow: `0 0 18px ${glowCol}, 0 0 44px ${glowCol}`, fontVariantNumeric: "tabular-nums" }}>{money(val)}</div>
          </div>
        </div>
        {h.sub ? (
          <div style={{ position: "absolute", top: 1170, left: 30, right: 30, textAlign: "center", opacity: Math.min(1, sub * 1.5) * (1 - fade), whiteSpace: "nowrap",
            transform: `scale(${1.35 - 0.35 * sub}) rotate(-2deg)`, fontFamily: SANS, fontWeight: 900, fontSize: 84, letterSpacing: -2, color: "#fff",
            lineHeight: 1.05, WebkitTextStroke: "5px #000", paintOrder: "stroke fill", textShadow: "0 8px 0 rgba(0,0,0,0.6), 0 0 30px rgba(0,0,0,0.6)" }}>
            {redMoney(h.sub, "#FF2E4D")}
          </div>
        ) : null}
      </AbsoluteFill>
      <AbsoluteFill style={{ backgroundColor: "#fff", opacity: flash }} />
    </AbsoluteFill>
  );
};

/* ---------------- V3 "ticket": makro tiketu, svetelny prejazd, cervene kusy sa odtrhnu ---------------- */
/* zubata ciara medzi dvoma bodmi (v % plochy tiketu) */
const jag = (a: [number, number], b: [number, number], n: number, seed: number) => {
  const pts: [number, number][] = [];
  for (let i = 1; i < n; i++) {
    const t = i / n;
    const nx = -(b[1] - a[1]), ny = b[0] - a[0];
    const l = Math.hypot(nx, ny) || 1;
    const o = (rnd(i, seed) - 0.5) * 3.2;
    pts.push([a[0] + (b[0] - a[0]) * t + (nx / l) * o, a[1] + (b[1] - a[1]) * t + (ny / l) * o]);
  }
  return pts;
};
const poly = (p: [number, number][]) => `polygon(${p.map(([x, y]) => `${x.toFixed(2)}% ${y.toFixed(2)}%`).join(", ")})`;

const TW = 960, TH = 720;
const TicketFace: React.FC<{ val: number; col: string; head: string; sweep: number }> = ({ val, col, head, sweep }) => {
  const balls = ["07", "14", "23", "38", "41"];
  return (
    <div style={{ position: "absolute", inset: 0, borderRadius: 18, overflow: "hidden", background: "linear-gradient(160deg, #fbf3dc 0%, #f1e3bd 100%)" }}>
      {/* ochranny vzor */}
      <div style={{ position: "absolute", inset: 0, backgroundImage: "repeating-linear-gradient(45deg, rgba(160,120,40,0.07) 0px, rgba(160,120,40,0.07) 2px, rgba(0,0,0,0) 2px, rgba(0,0,0,0) 14px)" }} />
      {/* hlavicka */}
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 120, background: "linear-gradient(90deg, #b3121f, #e0342a)",
        display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 48px" }}>
        <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: 64, color: "#fff", letterSpacing: 2 }}>★ JACKPOT</div>
        <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 30, color: "rgba(255,255,255,0.85)", letterSpacing: 3 }}>DRAW 0417</div>
      </div>
      {/* YOU WON / YOU GET */}
      <div style={{ position: "absolute", top: 150, left: 0, right: 0, textAlign: "center", fontFamily: SANS, fontWeight: 900, fontSize: 128,
        letterSpacing: -4, color: C.ink, lineHeight: 1 }}>{head}</div>
      {/* peciatka so sumou */}
      <div style={{ position: "absolute", top: 300, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
        <div style={{ transform: "rotate(-3deg)", border: `7px solid ${col}`, borderRadius: 18, padding: "4px 18px",
          fontFamily: MONO, fontWeight: 800, fontSize: 126, letterSpacing: -6, lineHeight: 1.15, color: col, fontVariantNumeric: "tabular-nums" }}>
          {money(val)}
        </div>
      </div>
      {/* tazene cisla */}
      <div style={{ position: "absolute", top: 530, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 22 }}>
        {[...balls, "09"].map((b, i) => (
          <div key={i} style={{ width: 104, height: 104, borderRadius: 52, background: i === 5 ? C.gold : "#fff", border: `5px solid ${i === 5 ? C.goldDeep : C.ink}`,
            display: "flex", alignItems: "center", justifyContent: "center", fontFamily: MONO, fontWeight: 800, fontSize: 46, color: C.ink }}>{b}</div>
        ))}
      </div>
      {/* ciarovy kod */}
      <div style={{ position: "absolute", bottom: 26, left: 60, right: 60, height: 26, backgroundImage: "repeating-linear-gradient(90deg, #222 0px, #222 3px, rgba(0,0,0,0) 3px, rgba(0,0,0,0) 7px, #222 7px, #222 8px, rgba(0,0,0,0) 8px, rgba(0,0,0,0) 13px)", opacity: 0.55 }} />
      {/* svetelny prejazd */}
      <div style={{ position: "absolute", top: -200, bottom: -200, width: 260, left: `${-30 + sweep * 160}%`, transform: "rotate(20deg)",
        background: "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.75) 50%, rgba(255,255,255,0) 100%)", mixBlendMode: "screen" }} />
    </div>
  );
};

export const HookTicket: React.FC<{ h: Hook; len: number; ph: number[] }> = ({ h, len, ph }) => {
  const { f, fps, d0, k, val, thump, sub, slamShake, top, out } = useDrain(h, len, ph);
  const col = interpolateColors(k, [0, 0.6, 1], ["#0B6B37", "#7a3a1a", "#C8102E"]);
  const sweep = interpolate(f, [4, 30], [0, 1], cl);
  const macro = interpolate(f, [0, 12], [1.07, 1.0], { ...cl, easing: Easing.out(Easing.cubic) });
  const bgPush = interpolate(f, [0, 12], [1.35, 1.15], { ...cl, easing: Easing.out(Easing.cubic) });
  const drift = 1 + f * 0.0012;
  const flash = interpolate(f, [1, 2, 6], [0, 0.3, 0], cl);
  // dva kusy: A = pravy dolny roh (-50% CASH), B = pravy horny roh (-24% IRS)
  const cuts = (h.chips?.items ?? ["−50% CASH", "−24% IRS"]).map((s) => s.replace(" OPTION", ""));
  const A0 = d0, B0 = d0 + 8, HOLD = 12;
  const jA = jag([100, 60], [58, 100], 9, 3);
  const jB = jag([66, 0], [100, 34], 8, 5);
  const main = poly([[0, 0], [66, 0], ...jB, [100, 34], [100, 60], ...jA, [58, 100], [0, 100]]);
  const pA = poly([[100, 60], [100, 100], [58, 100], ...[...jA].reverse()]);
  const pB = poly([[66, 0], [100, 0], [100, 34], ...[...jB].reverse()]);
  const piece = (clip: string, start: number, dir: [number, number], spin: number, label: string, lx: number, ly: number) => {
    const red = interpolate(f, [start, start + 2], [0, 1], cl);
    const t = Math.max(0, f - start - HOLD);
    const pop = f >= start ? spring({ frame: f - start, fps, config: { damping: 8, stiffness: 300 } }) : 0;
    const mx = dir[0] * (t * t * 3 + t * 10 + 26 * pop), my = dir[1] * (t * t * 3 + t * 10 + 26 * pop);
    const tf = `translate(${mx}px, ${my}px) rotate(${spin * (t * 1.6 + 4 * pop)}deg)`;
    const o = interpolate(t, [8, 16], [1, 0], cl);
    return (
      <>
        <div style={{ position: "absolute", inset: 0, clipPath: clip, WebkitClipPath: clip, transform: tf, opacity: o }}>
          <TicketFace val={val} col={col} head={f < d0 ? top[0] : top[1]} sweep={sweep} />
          <div style={{ position: "absolute", inset: 0, background: "#D7263D", opacity: 0.92 * red }} />
        </div>
        {f >= start ? (
          <div style={{ position: "absolute", left: lx, top: ly, transform: `${tf} scale(${0.6 + 0.4 * pop}) rotate(-6deg)`, opacity: o,
            background: "#D7263D", border: "5px solid #fff", borderRadius: 14, padding: "8px 20px", boxShadow: "0 12px 30px rgba(0,0,0,0.6)",
            fontFamily: MONO, fontWeight: 800, fontSize: 60, color: "#fff", letterSpacing: 1, whiteSpace: "nowrap" }}>{label}</div>
        ) : null}
      </>
    );
  };
  const fade = Math.min(1, out * 3);
  return (
    <AbsoluteFill style={{ backgroundColor: "#000", overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `scale(${macro * drift * (1 + 0.35 * out)}) translateX(${slamShake}px)`, opacity: 1 - 0.85 * out }}>
        <Backdrop img={h.bg} dim={0.38} blur={10} gray={interpolate(f, [d0, d0 + 16], [0, 0.6], cl)} scale={bgPush} />
        <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(255,200,110,0.28) 0%, rgba(0,0,0,0) 55%), radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 45%, rgba(0,0,0,0.75) 100%)" }} />
        {/* tiket */}
        <div style={{ position: "absolute", left: (1080 - TW) / 2, top: 560, width: TW, height: TH, transform: `rotate(-4deg) scale(${thump})`,
          filter: "drop-shadow(0 30px 40px rgba(0,0,0,0.7))" }}>
          <div style={{ position: "absolute", inset: 0, clipPath: main, WebkitClipPath: main }}>
            <TicketFace val={val} col={col} head={f < d0 ? top[0] : top[1]} sweep={sweep} />
          </div>
          {piece(pA, A0, [1, 1], 1, cuts[0] ?? "", 450, 590)}
          {piece(pB, B0, [1, -1], -1, cuts[1] ?? "", 520, 0)}
        </div>
        {h.sub ? (
          <div style={{ position: "absolute", top: 1360, left: 30, right: 30, textAlign: "center", opacity: Math.min(1, sub * 1.5) * (1 - fade), whiteSpace: "nowrap",
            transform: `scale(${1.35 - 0.35 * sub}) rotate(-2deg)`, fontFamily: SANS, fontWeight: 900, fontSize: 84, letterSpacing: -2, color: "#fff",
            lineHeight: 1.05, WebkitTextStroke: "5px #000", paintOrder: "stroke fill", textShadow: "0 8px 0 rgba(0,0,0,0.6)" }}>
            {redMoney(h.sub, "#FF2E4D")}
          </div>
        ) : null}
      </AbsoluteFill>
      <AbsoluteFill style={{ backgroundColor: "#fff", opacity: flash }} />
    </AbsoluteFill>
  );
};
