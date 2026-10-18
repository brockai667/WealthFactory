import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import { VoteButtons } from "./Episode";
import { C, Ep, MONO, SANS, money } from "./theme";

/* Datove karty kodom (styl saveo.house): kremove pozadie + mono nadpis, tmave karty pre pravidla / titul / koniec. */

const useSpr = (delay = 0, damping = 13) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: f - delay, fps, config: { damping } });
};

const Paper: React.FC<{ dark?: boolean; children: React.ReactNode }> = ({ dark, children }) => {
  const f = useCurrentFrame();
  const z = interpolate(f, [0, 90], [1.0, 1.03], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: dark ? C.dark : C.cream }}>
      <AbsoluteFill style={{
        backgroundImage: dark
          ? "radial-gradient(ellipse at 50% 40%, rgba(244,180,26,0.10) 0%, rgba(0,0,0,0) 60%)"
          : "repeating-linear-gradient(0deg, rgba(0,0,0,0.025) 0px, rgba(0,0,0,0.025) 2px, rgba(0,0,0,0) 2px, rgba(0,0,0,0) 6px)",
      }} />
      <AbsoluteFill style={{ transform: `scale(${z})`, alignItems: "center", justifyContent: "center", padding: "330px 80px 380px" }}>
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Mono: React.FC<{ children: React.ReactNode; color?: string; size?: number }> = ({ children, color = C.ink, size = 34 }) => (
  <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: size, letterSpacing: 6, color, textAlign: "center" }}>{children}</div>
);

const Stamp: React.FC<{ text: string; delay: number; rot?: number }> = ({ text, delay, rot = -8 }) => {
  const f = useCurrentFrame();
  const s = interpolate(f, [delay, delay + 6], [2.2, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.quad) });
  const o = interpolate(f, [delay, delay + 3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{ opacity: o, transform: `rotate(${rot}deg) scale(${s})`, border: `8px solid ${C.red}`, color: C.red, borderRadius: 14,
      padding: "10px 30px", fontFamily: MONO, fontWeight: 800, fontSize: 64, letterSpacing: 4, marginTop: 40 }}>{text}</div>
  );
};

const Title: React.FC<{ c: any }> = ({ c }) => {
  const words: string[] = [...c.big, c.accent];
  return (
    <Paper dark>
      <Mono color={C.gold}>{c.small}</Mono>
      <div style={{ height: 40 }} />
      {words.map((w, i) => {
        const s = useSpr(4 + i * 5);
        const acc = i === words.length - 1;
        return (
          <div key={i} style={{ transform: `translateY(${(1 - s) * 60}px)`, opacity: s, fontFamily: SANS, fontWeight: 900,
            fontSize: acc ? 220 : 170, lineHeight: 0.98, letterSpacing: -6, color: acc ? C.gold : "#fff" }}>{w}</div>
        );
      })}
    </Paper>
  );
};

const Jackpot: React.FC<{ c: any; len: number; ph: number[] }> = ({ c, len, ph }) => {
  const f = useCurrentFrame();
  const cut = ph.length ? ph[0] + 4 : Math.round(len * 0.35);
  const strike = interpolate(f, [cut, cut + 8], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const s2 = useSpr(cut + 6);
  const count = interpolate(f, [0, 14], [0, c.from], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  return (
    <Paper>
      <Mono>{c.label}</Mono>
      <div style={{ height: 60 }} />
      <div style={{ position: "relative", fontFamily: SANS, fontWeight: 900, fontSize: 130, color: C.ink, letterSpacing: -4 }}>
        {money(count)}
        <div style={{ position: "absolute", left: 0, top: "52%", height: 14, width: `${strike}%`, background: C.red, borderRadius: 7 }} />
      </div>
      <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: 90, color: C.red, opacity: s2, margin: "10px 0" }}>↓</div>
      <div style={{ transform: `scale(${s2})`, fontFamily: SANS, fontWeight: 900, fontSize: 150, color: C.goldDeep, letterSpacing: -5 }}>{money(c.to)}</div>
      <div style={{ opacity: s2, fontFamily: SANS, fontWeight: 800, fontSize: 52, color: C.ink, marginTop: 10 }}>{c.note}</div>
      <div style={{ opacity: s2 * 0.6, fontFamily: SANS, fontWeight: 600, fontSize: 40, color: C.ink, marginTop: 18 }}>{c.alt}</div>
    </Paper>
  );
};

const Tax: React.FC<{ c: any; len: number }> = ({ c, len }) => {
  const f = useCurrentFrame();
  const fill = interpolate(f, [8, 30], [0, c.pct], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const s = useSpr(0);
  const s2 = useSpr(Math.round(len * 0.4));
  return (
    <Paper>
      <Mono>{c.label}</Mono>
      <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 52, color: C.ink, marginTop: 30 }}>{c.line}</div>
      <div style={{ transform: `scale(${s})`, fontFamily: SANS, fontWeight: 900, fontSize: 300, color: C.red, letterSpacing: -10, lineHeight: 1 }}>
        {Math.round(fill)}%
      </div>
      <div style={{ width: 880, height: 110, borderRadius: 18, background: C.green, display: "flex", overflow: "hidden", marginTop: 20, border: `5px solid ${C.ink}` }}>
        <div style={{ width: `${fill}%`, background: C.red, display: "flex", alignItems: "center", justifyContent: "center",
          color: "#fff", fontFamily: MONO, fontWeight: 800, fontSize: 40 }}>{(c.bar ?? ["IRS", "YOU"])[0]}</div>
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontFamily: MONO, fontWeight: 800, fontSize: 40 }}>{(c.bar ?? ["IRS", "YOU"])[1]}</div>
      </div>
      <div style={{ display: "flex", width: 880, justifyContent: "space-between", marginTop: 26, opacity: s2 }}>
        <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: 58, color: C.red }}>−{money(c.amount)}</div>
        <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: 58, color: C.green }}>{money(c.left)}</div>
      </div>
    </Paper>
  );
};

const Bracket: React.FC<{ c: any; len: number; ph: number[] }> = ({ c, len, ph }) => {
  const s = useSpr(0);
  const p2 = ph.length ? ph[0] : Math.round(len * 0.3);
  const s2 = useSpr(p2);
  return (
    <Paper>
      <Mono>{c.label}</Mono>
      <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 52, color: C.ink, marginTop: 30 }}>{c.line}</div>
      <div style={{ transform: `scale(${s})`, fontFamily: SANS, fontWeight: 900, fontSize: 300, color: C.ink, letterSpacing: -10, lineHeight: 1 }}>{c.pct}%</div>
      <div style={{ opacity: s2, fontFamily: SANS, fontWeight: 800, fontSize: 56, color: C.ink, marginTop: 10 }}>You still owe</div>
      <div style={{ transform: `scale(${s2})`, fontFamily: SANS, fontWeight: 900, fontSize: 140, color: C.red, letterSpacing: -4 }}>{money(c.owe)}</div>
      <Stamp text={c.stamp} delay={ph.length ? p2 + 30 : Math.round(len * 0.55)} />
    </Paper>
  );
};

const Rule: React.FC<{ c: any }> = ({ c }) => {
  const s = useSpr(0);
  const lines: string[] = c.text.split("\n");
  return (
    <Paper dark>
      <div style={{ transform: `scale(${s})`, background: C.gold, color: C.ink, fontFamily: MONO, fontWeight: 800, fontSize: 52,
        letterSpacing: 8, padding: "12px 34px", borderRadius: 12 }}>{c.small}</div>
      <div style={{ height: 60 }} />
      {lines.map((l, i) => {
        const si = useSpr(6 + i * 10);
        return (
          <div key={i} style={{ opacity: si, transform: `translateY(${(1 - si) * 40}px)`, fontFamily: SANS, fontWeight: 900, fontSize: 118,
            lineHeight: 1.05, letterSpacing: -3, color: i === lines.length - 1 ? C.gold : "#fff", textAlign: "center" }}>{l}</div>
        );
      })}
    </Paper>
  );
};

const Public: React.FC<{ c: any; len: number }> = ({ c, len }) => {
  const s1 = useSpr(0);
  const s2 = useSpr(Math.round(len * 0.25));
  const box = (txt: string, s: number, red: boolean) => (
    <div style={{ transform: `scale(${s})`, background: red ? C.red : "#fff", color: red ? "#fff" : C.ink, border: `5px solid ${C.ink}`,
      borderRadius: 20, padding: "28px 46px", fontFamily: SANS, fontWeight: 900, fontSize: 72, textAlign: "center" }}>{txt}</div>
  );
  return (
    <Paper>
      <Mono>{c.label}</Mono>
      <div style={{ height: 50 }} />
      {box(c.line, s1, false)}
      <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: 110, color: C.ink, opacity: s2, lineHeight: 1.2 }}>↓</div>
      {box(c.arrow, s2, true)}
      <Stamp text={c.stamp} delay={Math.round(len * 0.45)} rot={6} />
      <div style={{ opacity: s2 * 0.7, fontFamily: SANS, fontWeight: 600, fontSize: 42, color: C.ink, marginTop: 40 }}>{c.foot}</div>
    </Paper>
  );
};

const End: React.FC<{ c: any; ep: Ep }> = ({ c, ep }) => {
  const s1 = useSpr(0);
  const s2 = useSpr(6);
  const foot: string[] = c.foot.split("\n");
  return (
    <AbsoluteFill style={{ backgroundColor: C.dark }}>
      <AbsoluteFill style={{ backgroundImage: "radial-gradient(ellipse at 50% 38%, rgba(244,180,26,0.16) 0%, rgba(0,0,0,0) 60%)" }} />
      <AbsoluteFill style={{ alignItems: "center", paddingTop: 300 }}>
        <Mono color={C.gold} size={30}>{c.small}</Mono>
        <div style={{ height: 50 }} />
        <div style={{ transform: `scale(${s1})`, fontFamily: SANS, fontWeight: 900, fontSize: 240, color: "#fff", letterSpacing: -8, lineHeight: 1 }}>{c.big}</div>
        <div style={{ transform: `scale(${s2})`, fontFamily: SANS, fontWeight: 900, fontSize: 150, color: C.gold, letterSpacing: -4, lineHeight: 1.1 }}>{c.accent}</div>
        <div style={{ height: 70 }} />
        {foot.map((l, i) => (
          <div key={i} style={{ opacity: s2, fontFamily: SANS, fontWeight: i === 0 ? 900 : 700, fontSize: i === 0 ? 64 : 50,
            color: i === 0 ? "#fff" : "rgba(255,255,255,0.75)", marginTop: 8 }}>{l}</div>
        ))}
      </AbsoluteFill>
      {ep.vote?.length === 2 ? <VoteButtons a={ep.vote[0]} b={ep.vote[1]} y={1330} delay={10} /> : null}
    </AbsoluteFill>
  );
};

/* Vysledok hlasovania z minuleho dielu: dva pruhy s % (ak su realne hlasy), inak len "YOU CHOSE X". */
const Result: React.FC<{ c: any; len: number }> = ({ c, len }) => {
  const f = useCurrentFrame();
  const opts: { name: string; pct?: number }[] = c.options ?? [];
  const win = c.winner ?? 0;
  const hasPct = opts.length === 2 && opts.every((o) => typeof o.pct === "number");
  const s = useSpr(0);
  const sw = useSpr(Math.round(len * 0.45));
  return (
    <Paper dark>
      <Mono color={C.gold}>{c.label}</Mono>
      <div style={{ height: 70 }} />
      {hasPct ? opts.map((o, i) => {
        const fill = interpolate(f, [6 + i * 4, 34 + i * 4], [0, o.pct as number], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
        const w = i === win;
        return (
          <div key={i} style={{ width: 900, marginBottom: 46, opacity: s }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontFamily: SANS, fontWeight: 900, fontSize: 84,
              color: w ? C.gold : "rgba(255,255,255,0.6)", letterSpacing: -2 }}>
              <span>{o.name}</span><span>{Math.round(fill)}%</span>
            </div>
            <div style={{ height: 46, borderRadius: 23, background: "rgba(255,255,255,0.12)", overflow: "hidden", marginTop: 10 }}>
              <div style={{ width: `${fill}%`, height: "100%", background: w ? C.gold : "rgba(255,255,255,0.45)", borderRadius: 23 }} />
            </div>
          </div>
        );
      }) : (
        <div style={{ transform: `scale(${s})`, fontFamily: SANS, fontWeight: 900, fontSize: 200, color: C.gold, letterSpacing: -6 }}>
          {opts[win]?.name}
        </div>
      )}
      {c.foot ? <div style={{ opacity: sw, transform: `translateY(${(1 - sw) * 30}px)`, fontFamily: SANS, fontWeight: 800, fontSize: 56,
        color: "#fff", marginTop: 30, textAlign: "center" }}>{c.foot}</div> : null}
    </Paper>
  );
};

export const Card: React.FC<{ ep: Ep; id: string; len: number; phases?: number[] }> = ({ ep, id, len, phases = [] }) => {
  const c = ep.cards[id];
  if (!c) return null;
  switch (c.kind) {
    case "title": return <Title c={c} />;
    case "jackpot": return <Jackpot c={c} len={len} ph={phases} />;
    case "tax": return <Tax c={c} len={len} />;
    case "bracket": return <Bracket c={c} len={len} ph={phases} />;
    case "rule": return <Rule c={c} />;
    case "public": return <Public c={c} len={len} />;
    case "end": return <End c={c} ep={ep} />;
    case "result": return <Result c={c} len={len} />;
    default: return null;
  }
};
