#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Syntetizuje zvuky pre uvodny hak (bez licencii, cisty kod): assets/sfx/cash.mp3 (pokladna cha-ching)
a assets/sfx/drain.mp3 (valec automatu, ktory klesa). Spusti raz: python tools/sfx_synth.py"""
import os, shutil, subprocess, tempfile
import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "sfx")
FF = shutil.which("ffmpeg") or "ffmpeg"
SR = 44100
rng = np.random.default_rng(7)


def t(sec):
    return np.arange(int(sec * SR)) / SR


def bell(f0, dur, tau, partials=((1, 1), (2.76, 0.5), (5.4, 0.28), (8.93, 0.12))):
    x = t(dur)
    y = sum(a * np.sin(2 * np.pi * f0 * r * x) * np.exp(-x / (tau / r ** 0.5)) for r, a in partials)
    return y * np.minimum(1, x / 0.002)


def place(buf, sig, at):
    i = int(at * SR)
    buf[i:i + len(sig)] += sig[: len(buf) - i]


def cash():
    buf = np.zeros(int(1.2 * SR))
    # "cha": mechanicky klik + sum zasuvky
    n = rng.standard_normal(int(0.09 * SR)) * np.exp(-t(0.09) / 0.025)
    n = np.convolve(n, np.ones(3) / 3, mode="same")
    place(buf, 0.5 * n, 0.0)
    place(buf, 0.9 * np.sin(2 * np.pi * 180 * t(0.05)) * np.exp(-t(0.05) / 0.012), 0.0)
    # "ching": dva zvoncky
    place(buf, 0.55 * bell(2093, 1.0, 0.45), 0.06)
    place(buf, 0.45 * bell(2637, 1.0, 0.40), 0.10)
    # mince
    for k in range(7):
        place(buf, 0.12 * bell(3800 + rng.random() * 2600, 0.12, 0.03), 0.12 + rng.random() * 0.35)
    return buf


def drain():
    dur = 0.9
    buf = np.zeros(int(dur * SR))
    # tikanie valca, spomaluje sa a klesa
    tt, k = 0.0, 0
    while tt < 0.72:
        f = 2400 - 1700 * (tt / 0.72)
        place(buf, 0.22 * np.sin(2 * np.pi * f * t(0.018)) * np.exp(-t(0.018) / 0.005), tt)
        tt += 0.026 + 0.05 * (tt / 0.72) ** 2
        k += 1
    # klesajuci ton (vyfuknutie)
    x = t(0.8)
    f = 520 * np.exp(-x * 2.6) + 70
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = 0.35 * np.sin(ph) * np.minimum(1, x / 0.03) * np.exp(-x / 0.5)
    place(buf, y, 0.02)
    return buf


def tear():
    # papier: praskajuci sum s rychlymi zrnkami
    d = 0.32
    n = rng.standard_normal(int(d * SR))
    env = np.exp(-t(d) / 0.12) * (0.4 + 0.6 * (rng.random(int(d * SR)) > 0.7))
    y = np.diff(n * env, prepend=0)
    return np.convolve(y, np.ones(4) / 4, mode="same")


def write(name, y):
    y = y / max(1e-6, np.max(np.abs(y))) * 0.89
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "x.wav")
        sf.write(wav, y.astype(np.float32), SR)
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", wav, "-b:a", "160k", os.path.join(OUT, name + ".mp3")], check=True)
    print("ok", name)


if __name__ == "__main__":
    write("cash", cash())
    write("drain", drain())
    write("tear", tear())
