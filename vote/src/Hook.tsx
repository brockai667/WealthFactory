import React from "react";
import { AbsoluteFill, interpolate, interpolateColors, spring, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import { C, Hook, MONO, SANS, money } from "./theme";

/* Uvodny hak (0-3 s), vsetko kodom. Pouzije sa len ked diel ma pole "hook" - bez neho sa nic nemeni. */

const GREEN = "#0B5E31";   // tmava zelena: citatelna na kremovej aj na mobile
const RED = "#C8102E";

/* text, v ktorom je "$..." cast cervena */
const redMoney = (s: string) =>
  s.split(/(\$[0-9][0-9.,]*[MK]?)/).map((p, i) => (p.startsWith("$") ? <span key={i} style={{ color: RED }}>{p}</span> : p));

/* "drain": YOU WON $100,000,000 -> YOU GET $38,000,000 (cervena) + WHERE DID $62M GO?, na konci cislo odpluje do HUD */
export const HookDrain: React.FC<{ h: Hook; len: number; ph: number[] }> = ({ h, len, ph }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const from = h.from ?? 100000000;
  const to = h.to ?? from;
  const d0 = ph.length ? ph[0] : Math.round(len * 0.5);   // zaciatok druheho VO riadku = zaciatok zrazenia
  const ROLL = 20;
  const pop = spring({ frame: f, fps, config: { damping: 9, stiffness: 220 } });
  const k = interpolate(f, [d0, d0 + ROLL], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  // valec: medzi krokmi cisla "preskakuju" ako na automate, presne na konci
  const raw = from + (to - from) * k;
  const val = k >= 1 ? to : Math.round(raw / 1000) * 1000 + (k > 0 ? (Math.floor(f * 7919) % 1000) : 0);
  const col = interpolateColors(k, [0, 0.6, 1], [GREEN, "#6b3a1f", RED]);
  const land = spring({ frame: f - d0 - ROLL, fps, config: { damping: 10, stiffness: 260 } });
  const thump = f >= d0 + ROLL ? 1 + 0.08 * Math.sin(Math.min(1, land) * Math.PI) : 1;
  const sub = spring({ frame: f - d0 - ROLL - 2, fps, config: { damping: 12 } });
  const swap = f >= d0 ? 1 : 0;   // tvrdy strih nadpisu (ziadne prelinanie dvoch textov)
  const hop = f >= d0 ? spring({ frame: f - d0, fps, config: { damping: 11, stiffness: 240 } }) : 1;
  const top = h.top ?? ["YOU WON", "YOU GET"];
  // posledne snimky: cislo sa zmensi a odleti do HUD (CASH vlavo hore)
  const DOCK = 8;
  const dk = interpolate(f, [len - DOCK, len], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.in(Easing.cubic) });
  const numY = 1010;
  const dx = (230 - 540) * dk;
  const dy = (152 - numY) * dk;
  const ds = 1 - 0.72 * dk;
  const burst = interpolate(f, [0, 12], [0.45, 0.12], { extrapolateRight: "clamp" });
  const fade = Math.min(1, dk * 4);   // nadpis a otazka zmiznu hned na zaciatku odletu
  const shake = f < 6 ? Math.sin(f * 2.7) * (6 - f) * 2.2 : 0;
  const head = (txt: string, o: number, y: number) => (
    <div style={{ position: "absolute", top: 700, left: 0, right: 0, textAlign: "center", opacity: o, transform: `translateY(${y}px)`,
      fontFamily: SANS, fontWeight: 900, fontSize: 150, letterSpacing: -5, color: C.ink, lineHeight: 1 }}>{txt}</div>
  );
  return (
    <AbsoluteFill style={{ backgroundColor: C.cream, overflow: "hidden" }}>
      <AbsoluteFill style={{ backgroundImage: "repeating-linear-gradient(0deg, rgba(0,0,0,0.025) 0px, rgba(0,0,0,0.025) 2px, rgba(0,0,0,0) 2px, rgba(0,0,0,0) 6px)" }} />
      <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 47%, rgba(244,180,26,${burst}) 0%, rgba(244,180,26,0) 55%)` }} />
      <AbsoluteFill style={{ transform: `translateX(${shake}px)` }}>
        <div style={{ opacity: 1 - fade }}>
          {swap ? head(top[1], 1, 30 * (1 - hop)) : head(top[0], 1, 0)}
        </div>
        <div style={{ position: "absolute", top: numY - 90, left: 0, right: 0, display: "flex", justifyContent: "center",
          transform: `translate(${dx}px, ${dy}px) scale(${ds * (0.8 + 0.2 * pop) * thump})`, opacity: 1 - 0.5 * dk }}>
          <div style={{ fontFamily: MONO, fontWeight: 800, fontSize: 144, letterSpacing: -6, color: col, lineHeight: 1.25,
            fontVariantNumeric: "tabular-nums" }}>{money(val)}</div>
        </div>
        {h.sub ? (
          <div style={{ position: "absolute", top: 1200, left: 40, right: 40, textAlign: "center", opacity: sub * (1 - fade),
            transform: `scale(${0.7 + 0.3 * sub})`, fontFamily: SANS, fontWeight: 900, fontSize: 92, letterSpacing: -2, color: C.ink, lineHeight: 1.05 }}>
            {redMoney(h.sub)}
          </div>
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* cervene stitky-odpovede ("-50% CASH OPTION", "-24% IRS") nad obrazkom */
export const HookChips: React.FC<{ items: string[] }> = ({ items }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <div style={{ position: "absolute", top: 300, left: 60, right: 60, display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 22 }}>
      {items.map((t, i) => {
        const s = spring({ frame: f - 4 - i * 10, fps, config: { damping: 10, stiffness: 200 } });
        return (
          <div key={i} style={{ transform: `scale(${s}) rotate(${i % 2 ? 2 : -3}deg)`, transformOrigin: "left center", background: RED, color: "#fff",
            fontFamily: MONO, fontWeight: 800, fontSize: 58, letterSpacing: 2, padding: "12px 30px", borderRadius: 16,
            border: "4px solid #fff", boxShadow: "0 12px 30px rgba(0,0,0,0.55)" }}>{t}</div>
        );
      })}
    </div>
  );
};

/* "recap": prekryv pre diel N >= 2 nad obrazkom. stampAt = snimka (od zaciatku haku), kedy udrie peciatka. */
export const HookRecap: React.FC<{ h: Hook; stampAt: number }> = ({ h, stampAt }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s1 = spring({ frame: f, fps, config: { damping: 11, stiffness: 200 } });
  const st = interpolate(f, [stampAt, stampAt + 6], [2.2, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.quad) });
  const so = interpolate(f, [stampAt, stampAt + 3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const flash = interpolate(f - stampAt, [0, 2, 8], [0, 0.35, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0) 70%)" }} />
      {h.tag ? (
        <div style={{ position: "absolute", top: 300, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
          <div style={{ background: C.gold, color: C.ink, fontFamily: MONO, fontWeight: 800, fontSize: 40, letterSpacing: 3, padding: "12px 28px",
            borderRadius: 10, boxShadow: "0 8px 24px rgba(0,0,0,0.5)", transform: `scale(${s1})` }}>{h.tag}</div>
        </div>
      ) : null}
      {h.big ? (
        <div style={{ position: "absolute", top: 640, left: 40, right: 40, textAlign: "center", transform: `scale(${0.6 + 0.4 * s1})`,
          fontFamily: SANS, fontWeight: 900, fontSize: 118, lineHeight: 1.02, letterSpacing: -4, color: "#fff",
          WebkitTextStroke: "6px #000", paintOrder: "stroke fill", textShadow: "0 10px 30px rgba(0,0,0,0.6)" }}>{h.big}</div>
      ) : null}
      {h.stamp ? (
        <div style={{ position: "absolute", top: 960, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
          <div style={{ opacity: so, transform: `rotate(-6deg) scale(${st})`, background: "rgba(255,255,255,0.92)", border: `10px solid ${RED}`, color: RED,
            borderRadius: 16, padding: "14px 34px", fontFamily: MONO, fontWeight: 800, fontSize: 70, letterSpacing: 3, textAlign: "center", maxWidth: 940 }}>{h.stamp}</div>
        </div>
      ) : null}
      <AbsoluteFill style={{ backgroundColor: "#fff", opacity: flash }} />
    </AbsoluteFill>
  );
};
