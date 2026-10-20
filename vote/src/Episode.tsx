import React from "react";
import {
  AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Easing,
} from "remotion";
import { Card } from "./Cards";
import { Bubble, Calls, Dust, Glow, Rain, Steam, shakeOf } from "./Fx";
import { HookChips, HookDrain, HookRecap } from "./Hook";
import { HookJackpot, HookTicket } from "./HookFx";
import { Beat, C, Ep, MONO, SANS, Word, money } from "./theme";

/* cas slova (s) v danom beate, ktore zacina na token; null ak nie je */
const wordTime = (ep: Ep, bi: number, token: string) => {
  const w = ep.words.find((x) => x.b === bi && x.w.toLowerCase().replace(/[^a-z]/g, "").startsWith(token.toLowerCase()));
  return w ? w.s : null;
};

/* ---------- obrazok: Ken Burns + vstupny prechod + svetlo + efekty ---------- */
const Still: React.FC<{ ep: Ep; bi: number; len: number; fresh: boolean }> = ({ ep, bi, len, fresh }) => {
  const beat = ep.beats[bi];
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fx = beat.fx ?? [];
  const p = f / Math.max(1, len);
  const dir = beat.zoom === "out" ? -1 : 1;
  const s0 = beat.zoom ? (dir > 0 ? 1.08 : 1.24) : 1.1;
  const s1 = beat.zoom ? (dir > 0 ? 1.26 : 1.08) : 1.18;
  const scale = interpolate(p, [0, 1], [s0, s1], { easing: Easing.inOut(Easing.quad) });
  const panX = (((bi * 37) % 5) - 2) * 12 * p;
  const panY = (((bi * 53) % 3) - 1) * 16 * p;
  const punch = interpolate(f, [0, 6], [fresh ? 1.0 : 1.07, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const flick = 1 + 0.03 * Math.sin(f * 0.9 + bi) + 0.02 * Math.sin(f * 2.3) - ((f + bi * 7) % 61 < 2 ? 0.09 : 0);
  // vstupny prechod pri novom obrazku: strih s rozmazanim (whip / zoom)
  const k = interpolate(f, [0, 7], [1, 0], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const whip = fresh && bi % 2 === 0;
  const zoomIn = fresh && bi % 2 === 1;
  const entry = whip ? `translateX(${k * 160}px)` : zoomIn ? `scale(${1 + k * 0.22})` : "";
  const blur = fresh ? k * 14 : 0;
  const knockT = beat.knock ? wordTime(ep, bi, beat.knock) : null;
  const knockAt = knockT !== null ? Math.round((knockT - beat.t0) * fps) : null;
  return (
    <AbsoluteFill style={{ backgroundColor: "#000", overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `${entry} ${shakeOf(f, fx, knockAt)}`, filter: blur > 0.3 ? `blur(${blur}px)` : undefined }}>
        <AbsoluteFill style={{ transform: `scale(${scale * punch}) translate(${panX}px, ${panY}px)` }}>
          <Img src={staticFile(`img/${beat.shot}.jpg`)}
            style={{ width: "100%", height: "100%", objectFit: "cover", filter: `brightness(${flick}) contrast(1.05) saturate(1.06)` }} />
          {fx.includes("glow") && beat.glow ? <Glow x={beat.glow[0]} y={beat.glow[1]} color={beat.glow[2]} /> : null}
          {fx.includes("steam") ? <Steam x={0.25} y={0.47} /> : null}
        </AbsoluteFill>
      </AbsoluteFill>
      {fx.includes("rain") ? <Rain /> : null}
      {fx.includes("dust") ? <Dust /> : null}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.6) 100%)" }} />
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 16%, rgba(0,0,0,0) 58%, rgba(0,0,0,0.5) 100%)" }} />
      {knockAt !== null ? <AbsoluteFill style={{ backgroundColor: "#fff", opacity: interpolate(f - knockAt, [0, 2, 6], [0, 0.18, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }} /> : null}
    </AbsoluteFill>
  );
};

/* karta vchadza zprava (swipe) */
const CardIn: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const f = useCurrentFrame();
  const k = interpolate(f, [0, 8], [1, 0], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  return <AbsoluteFill style={{ transform: `translateX(${k * 100}%)`, filter: k > 0.02 ? `blur(${k * 10}px)` : undefined }}>{children}</AbsoluteFill>;
};

/* ---------- HUD hore: CASH / TAX DUE / ATTENTION ---------- */
const hudAt = (beats: Beat[], t: number) => {
  let cur: [number, number, number] = [0, 0, 0];
  let prev: [number, number, number] = [0, 0, 0];
  let start = 0;
  for (const b of beats) {
    if (b.t0 > t) break;
    if (b.hud) { prev = cur; cur = b.hud; start = b.t0; }
  }
  const k = Math.min(1, (t - start) / 1.1);
  const e = 1 - Math.pow(1 - k, 3);
  return { v: cur.map((c, i) => prev[i] + (c - prev[i]) * e), changed: cur.map((c, i) => c !== prev[i] && (t - start) < 1.6), down: cur.map((c, i) => c < prev[i]), k };
};

const Hud: React.FC<{ ep: Ep; t: number }> = ({ ep, t }) => {
  const { v, changed, down } = hudAt(ep.beats, t);
  const cell = (label: string, val: string, i: number, extra?: React.ReactNode) => {
    const up = changed[i];
    const col = up ? (i === 0 ? (down[0] ? C.red : C.gold) : C.red) : "#fff";
    return (
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6, alignItems: i === 0 ? "flex-start" : i === 2 ? "flex-end" : "center" }}>
        <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 24, letterSpacing: 3, color: "rgba(255,255,255,0.6)" }}>{label}</div>
        <div style={{ fontFamily: MONO, fontWeight: 800, fontSize: 40, color: col, transform: `scale(${up ? 1.08 : 1})`,
          transformOrigin: i === 0 ? "left" : i === 2 ? "right" : "center", textShadow: up ? `0 0 18px ${col}` : "0 2px 8px rgba(0,0,0,0.7)" }}>{val}</div>
        {extra}
      </div>
    );
  };
  const att = v[2];
  const hot = att > 40;
  const pulse = hot ? 0.5 + 0.5 * Math.sin(t * 8) : 0;
  return (
    <div style={{ position: "absolute", top: 70, left: 44, right: 44, display: "flex", padding: "22px 28px",
      background: "rgba(10,10,12,0.74)", borderRadius: 22, border: `2px solid ${hot ? `rgba(215,38,61,${0.4 + 0.5 * pulse})` : "rgba(255,255,255,0.12)"}` }}>
      {cell(ep.hud_labels[0], money(v[0]), 0)}
      {cell(ep.hud_labels[1], money(v[1]), 1)}
      {cell(ep.hud_labels[2], `${Math.round(att)}%`, 2,
        <div style={{ width: 200, height: 12, borderRadius: 6, background: "rgba(255,255,255,0.15)", overflow: "hidden" }}>
          <div style={{ width: `${att}%`, height: "100%", background: hot ? C.red : C.gold, boxShadow: hot ? `0 0 12px ${C.red}` : undefined }} />
        </div>)}
    </div>
  );
};

/* ---------- titulky 2-3 slova; aktivne zlte, peniaze zelene, hrozba cervena ---------- */
const MONEY = /^(\$|\d|one$|two$|three$|four|five$|six$|seven$|eight|nine$|ten$|twelve|twenty|thirty|forty|fifty|hundred|thousand|million|billion|half|percent|dollars?|cash|fortune)/i;
const DANGER = /^(irs|tax|taxed|trap|owe|public|gone|knock|never|isn't|isnt|nobody|cut|shrinking|missed|record|news)/i;
const tone = (w: string) => {
  const c = w.toLowerCase().replace(/[^a-z0-9$'-]/g, "");
  if (DANGER.test(c)) return "#FF5468";
  if (MONEY.test(c)) return "#4ADE80";
  return null;
};

const chunks = (words: Word[]) => {
  const out: Word[][] = [];
  let cur: Word[] = [];
  words.forEach((w, i) => {
    const nx = words[i + 1];
    cur.push(w);
    const curLen = cur.reduce((a, x) => a + x.w.length + 1, 0);
    const brk = /[.,!?:]$/.test(w.w) || cur.length >= 3 || !nx || nx.b !== w.b || curLen + (nx ? nx.w.length : 0) > 15;
    if (brk) { out.push(cur); cur = []; }
  });
  return out;
};

const Captions: React.FC<{ ep: Ep; t: number; y: number }> = ({ ep, t, y }) => {
  const cs = React.useMemo(() => chunks(ep.words), [ep.words]);
  const ci = cs.findIndex((c, i) => t >= c[0].s - 0.05 && t < (cs[i + 1] ? cs[i + 1][0].s - 0.05 : c[c.length - 1].e + 0.4));
  if (ci < 0) return null;
  const ch = cs[ci];
  const pop = Math.min(1, (t - ch[0].s + 0.05) / 0.12);
  const chars = ch.reduce((a, x) => a + x.w.length + 1, -1);
  const size = Math.min(92, Math.floor(1600 / Math.max(1, chars + ch.length * 0.3)));
  return (
    <div style={{ position: "absolute", top: y, left: 30, right: 30, textAlign: "center", whiteSpace: "nowrap",
      transform: `scale(${0.88 + 0.12 * pop}) rotate(${ci % 2 ? -1.2 : 1.2}deg)`, fontFamily: SANS, fontWeight: 900, fontSize: size, lineHeight: 1.1, letterSpacing: -1 }}>
      {ch.map((w, i) => {
        const spoken = t >= w.s - 0.03;
        const active = spoken && t < w.e + 0.05;
        const k = tone(w.w);
        const color = !spoken ? "rgba(255,255,255,0.42)" : k ?? (active ? "#FFC93C" : "#fff");
        return (
          <span key={i} style={{ display: "inline-block", color, WebkitTextStroke: "4px #000", paintOrder: "stroke fill",
            textShadow: "0 6px 0 rgba(0,0,0,0.55), 0 10px 24px rgba(0,0,0,0.5)", margin: "0 17px",
            transform: `translateY(${active ? -6 : 0}px)` }}>
            {w.w.replace(/[",]/g, "")}
          </span>
        );
      })}
    </div>
  );
};

/* ---------- stitok PROBLEM N ---------- */
const Label: React.FC<{ text: string }> = ({ text }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: f - 3, fps, config: { damping: 12 } });
  return (
    <div style={{ position: "absolute", top: 300, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
      <div style={{ transform: `scale(${s}) rotate(-2deg)`, background: C.gold, color: C.ink, fontFamily: MONO, fontWeight: 800,
        fontSize: 48, letterSpacing: 6, padding: "14px 32px", borderRadius: 10, boxShadow: "0 8px 24px rgba(0,0,0,0.5)" }}>{text}</div>
    </div>
  );
};

/* ---------- DAY N razitko ---------- */
const DayStamp: React.FC<{ n: number; series: string }> = ({ n, series }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: f, fps, config: { damping: 12, stiffness: 160 } });
  const out = interpolate(f, [34, 44], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: `rgba(8,8,10,${0.85 * out})`, alignItems: "center", justifyContent: "center", opacity: out }}>
      <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 34, letterSpacing: 10, color: C.gold, marginBottom: 10 }}>{series}</div>
      <div style={{ transform: `scale(${0.6 + 0.4 * s})`, fontFamily: SANS, fontWeight: 900, fontSize: 230, color: "#fff", letterSpacing: -6 }}>DAY {n}</div>
    </AbsoluteFill>
  );
};

/* ---------- hlasovacie tlacidla ---------- */
export const VoteButtons: React.FC<{ a: string; b: string; y: number; delay?: number }> = ({ a, b, y, delay = 0 }) => {
  const f = useCurrentFrame() - delay;
  const { fps } = useVideoConfig();
  const sa = spring({ frame: f, fps, config: { damping: 11 } });
  const sb = spring({ frame: f - 5, fps, config: { damping: 11 } });
  const pulse = 1 + 0.035 * Math.sin(Math.max(0, f) * 0.25);
  const btn = (txt: string, s: number, gold: boolean) => (
    <div style={{ transform: `scale(${s * pulse})`, width: 400, height: 150, borderRadius: 28, display: "flex", alignItems: "center",
      justifyContent: "center", background: gold ? C.gold : "#fff", color: C.ink, fontFamily: SANS, fontWeight: 900, fontSize: 76,
      letterSpacing: 2, boxShadow: `0 10px 0 ${gold ? C.goldDeep : "#9a9a9a"}, 0 20px 40px rgba(0,0,0,0.5)` }}>{txt}</div>
  );
  return (
    <div style={{ position: "absolute", top: y, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 40, alignItems: "center" }}>
      {btn(a, sa, true)}
      <div style={{ fontFamily: MONO, fontWeight: 800, fontSize: 40, color: "#fff", opacity: sb }}>OR</div>
      {btn(b, sb, false)}
    </div>
  );
};

/* ---------- celok ---------- */
type Seg = { shot: string; from: number; to: number; first: number; phases: number[] };

export const Episode: React.FC<{ ep: Ep }> = ({ ep }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame / fps;
  if (!ep.beats.length) return null;
  const last = ep.beats.length - 1;
  const fr = (i: number) => (i > last ? durationInFrames : Math.round(ep.beats[i].t0 * fps));
  // za sebou iduce beaty s tou istou kartou = jedna karta s fazami (animacia sa nerestartuje)
  const segs: Seg[] = [];
  ep.beats.forEach((b, i) => {
    const prev = segs[segs.length - 1];
    if (prev && (b.shot.startsWith("card:") || b.shot === "hook") && prev.shot === b.shot) {
      prev.to = fr(i + 1);
      prev.phases.push(fr(i) - prev.from);
    } else {
      segs.push({ shot: b.shot, from: fr(i), to: fr(i + 1), first: i, phases: [] });
    }
  });
  const curI = Math.max(0, ep.beats.findIndex((b, i) => t >= b.t0 && (i === last || t < ep.beats[i + 1].t0)));
  const cur = ep.beats[curI];
  // volitelny hak: bez ep.hook je hookN = 0 a vsetko ide ako predtym
  const hook = ep.hook;
  const hookN = hook ? Math.min(last, hook.beats ?? 2) : 0;
  const inHook = curI < hookN;
  const isHookCard = cur.shot === "hook";
  const isCard = cur.shot.startsWith("card:");
  const isEnd = cur.shot === "card:end";
  const musicVol = (f: number) =>
    ep.music_gain * interpolate(f, [0, 15, durationInFrames - 45, durationInFrames], [0, 1, 1, 0], { extrapolateRight: "clamp" });
  const sfx = (name: string, at: number, vol: number, key: string) => (
    <Sequence key={key} from={Math.max(0, at)} durationInFrames={fps * 6}>
      <Audio src={staticFile(`sfx/${name}.mp3`)} volume={vol} />
    </Sequence>
  );
  const sounds: React.ReactNode[] = [];
  if (hook && hook.kind === "drain") {
    sounds.push(sfx("cash", 0, 0.75, "h0"));
    const d0 = ep.beats.length > 1 ? fr(1) : 20;
    sounds.push(sfx("drain", d0 - 1, 0.6, "h1"), sfx("impact-bass-1", d0 + 19, 0.55, "h2"));
    if (hook.style === "jackpot" || hook.style === "ticket") sounds.push(sfx("whoosh-short", d0 - 2, 0.5, "h4"));
    if (hook.style === "ticket") sounds.push(sfx("tear", d0, 0.6, "h5"), sfx("tear", d0 + 8, 0.55, "h6"));
  }
  if (hook && hook.kind === "recap") sounds.push(sfx("impact-bass-1", fr(Math.min(last, hook.stamp_beat ?? 1)), 0.55, "h3"));
  if (hook?.chips && hook.chips.beat <= last)
    hook.chips.items.forEach((_, n) => sounds.push(sfx("pop", fr(hook.chips!.beat) + 4 + n * 10, 0.5, `hc${n}`)));
  ep.beats.forEach((b, i) => {
    const at = fr(i);
    const name = b.sfx === "impact" ? "impact-bass-1" : b.sfx === "whoosh" ? "whoosh-short" : b.sfx === "riser" ? "riser" : null;
    if (name) sounds.push(sfx(name, name === "riser" ? at + 10 : at - 2, name === "riser" ? 0.3 : 0.5, `s${i}`));
    if (b.day) sounds.push(sfx("impact-bass-1", at, 0.55, `d${i}`));
    if (b.label) sounds.push(sfx("pop", at + 3, 0.45, `l${i}`));
    if (b.knock) {
      const kt = wordTime(ep, i, b.knock);
      if (kt !== null) { const k = Math.round(kt * fps); sounds.push(sfx("impact-bass-1", k, 0.45, `k${i}`), sfx("impact-bass-1", k + 7, 0.4, `k2${i}`)); }
    }
    if ((b.fx ?? []).includes("calls")) for (let n = 0; n < 8; n++) sounds.push(sfx("ping", at + 8 + n * 8, 0.18, `c${i}_${n}`));
    if ((b.fx ?? []).includes("bubble") && ep.bubble) {
      const bt = wordTime(ep, i, ep.bubble?.word ?? "congrats");
      sounds.push(sfx("ping", bt !== null ? Math.round(bt * fps) : at + 20, 0.5, `b${i}`));
    }
  });
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {segs.map((s, k) => (
        <Sequence key={`v${k}`} from={s.from} durationInFrames={s.to - s.from}>
          {s.shot === "hook" && hook
            ? (hook.style === "jackpot" ? <HookJackpot h={hook} len={s.to - s.from} ph={s.phases} />
              : hook.style === "ticket" ? <HookTicket h={hook} len={s.to - s.from} ph={s.phases} />
              : <HookDrain h={hook} len={s.to - s.from} ph={s.phases} />)
            : s.shot.startsWith("card:")
            ? <CardIn><Card ep={ep} id={s.shot.slice(5)} len={s.to - s.from} phases={s.phases} /></CardIn>
            : <Still ep={ep} bi={s.first} len={s.to - s.from} fresh={s.first === 0 || ep.beats[s.first - 1].shot !== s.shot} />}
        </Sequence>
      ))}
      {ep.beats.map((b, i) => {
        const len = fr(i + 1) - fr(i);
        const fx = b.fx ?? [];
        const bt = fx.includes("bubble") ? wordTime(ep, i, ep.bubble?.word ?? "congrats") : null;
        const keepBubble = i > 0 && (ep.beats[i - 1].fx ?? []).includes("bubble") && ep.beats[i - 1].shot === b.shot;
        return (
          <Sequence key={`o${i}`} from={fr(i)} durationInFrames={len}>
            {b.label ? <Label text={b.label} /> : null}
            {fx.includes("calls") ? <Calls /> : null}
            {fx.includes("bubble") && ep.bubble ? <Bubble from={ep.bubble.from} text={ep.bubble.text}
              at={bt !== null ? Math.round((bt - b.t0) * fps) : Math.round(len * ep.bubble.at)} /> : null}
            {keepBubble && ep.bubble ? <Bubble from={ep.bubble.from} text={ep.bubble.text} at={-40} /> : null}
            {b.day ? <DayStamp n={b.day} series={ep.series} /> : null}
            {hook?.chips && hook.chips.beat === i ? <HookChips items={hook.chips.items} /> : null}
            {b.vote ? <VoteButtons a={ep.vote[0]} b={ep.vote[1]} y={1480} delay={Math.round(len * 0.45)} /> : null}
          </Sequence>
        );
      })}
      {hook && hook.kind === "recap" && hookN > 0 ? (
        <Sequence from={fr(0)} durationInFrames={fr(hookN) - fr(0)}>
          <HookRecap h={hook} stampAt={fr(Math.min(hookN - 1, hook.stamp_beat ?? 1)) - fr(0)} />
        </Sequence>
      ) : null}
      {!isEnd && !isHookCard && <Hud ep={ep} t={t} />}
      {!isEnd && !inHook && <Captions ep={ep} t={t} y={isCard ? 1600 : cur.vote ? 1210 : 1320} />}
      <Audio src={staticFile(ep.voice)} />
      <Audio src={staticFile(ep.music)} volume={musicVol} />
      {sounds}
    </AbsoluteFill>
  );
};
