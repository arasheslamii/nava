#!/usr/bin/env python3
"""ASR benchmark: WER (jiwer) + latency (p50/p95, RTF) across backend configs.

Datasets:
  personal:<dir>      dir with audio/ + references.tsv (filename<TAB>category<TAB>reference)
  librispeech:<dir>   dir tree with *.flac + *.trans.txt (e.g. LibriSpeech/test-clean)

Configs are "device:model:compute" (model optional), comma-separated, e.g.:
  cpu:small.en:int8 , cuda:distil-large-v3:int8 , cuda:distil-large-v3:float32

Usage:
  . .venv/bin/activate      # (CPU)  or  .venv-gpu + LD_LIBRARY_PATH for cuda configs
  python bench/run_bench.py --dataset personal:data/wer_personal \
         --configs cpu:small.en:int8
"""

from __future__ import annotations

import argparse
import csv
import re
import statistics as stats
import sys
import time
from pathlib import Path

import jiwer

from flowlinux.asr.factory import build_backend
from flowlinux.audio.load import load_audio_file

_PUNCT = re.compile(r"[^\w\s']")
_WS = re.compile(r"\s+")


def normalize(s: str) -> str:
    return _WS.sub(" ", _PUNCT.sub(" ", s.lower())).strip()


def load_personal(root: str):
    root = Path(root)
    items = []
    with (root / "references.tsv").open() as f:
        for row in csv.DictReader(f, delimiter="\t"):
            items.append((root / "audio" / row["filename"],
                          row.get("category", "-"), row["reference"]))
    return items


def load_librispeech(root: str, limit: int | None = None):
    root = Path(root)
    items = []
    for trans in root.rglob("*.trans.txt"):
        with trans.open() as f:
            for line in f:
                uid, _, text = line.strip().partition(" ")
                flac = trans.parent / f"{uid}.flac"
                if flac.exists():
                    items.append((flac, "libri", text))
                    if limit and len(items) >= limit:
                        return items
    return items


def pct(values, p):
    if not values:
        return 0.0
    return float(sorted(values)[min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))])


def parse_config(spec: str):
    parts = spec.split(":")
    device = parts[0]
    model = parts[1] if len(parts) > 1 and parts[1] else None
    compute = parts[2] if len(parts) > 2 else ("int8" if device == "cpu" else "int8")
    return device, model, compute


def run_config(spec: str, items):
    device, model, compute = parse_config(spec)
    backend = build_backend(engine="faster-whisper", model=model, device=device,
                            compute_type=compute)
    print(f"\n=== {backend.name} ===", flush=True)
    t0 = time.monotonic()
    backend.load()
    print(f"  model load: {time.monotonic() - t0:.1f}s", flush=True)

    refs, hyps, infers, rtfs = [], [], [], []
    by_cat: dict[str, list[tuple[str, str]]] = {}
    for audio_path, cat, ref in items:
        audio = load_audio_file(str(audio_path))
        res = backend.transcribe(audio, 16_000)
        refs.append(normalize(ref))
        hyps.append(normalize(res.text))
        infers.append(res.infer_s)
        rtfs.append(res.rtf)
        by_cat.setdefault(cat, []).append((normalize(ref), normalize(res.text)))
        print(f"  [{cat:6}] {res.infer_s:5.2f}s rtf {res.rtf:4.2f}  ref={ref[:48]!r} "
              f"hyp={res.text[:48]!r}", flush=True)

    overall_wer = jiwer.wer(refs, hyps) if refs else 0.0
    print(f"  ---- {spec} ----")
    print(f"  WER overall : {overall_wer * 100:5.2f}%   (n={len(refs)})")
    for cat, pairs in sorted(by_cat.items()):
        r = [p[0] for p in pairs]; h = [p[1] for p in pairs]
        print(f"  WER {cat:9}: {jiwer.wer(r, h) * 100:5.2f}%   (n={len(pairs)})")
    print(f"  latency infer: p50 {pct(infers,50):.2f}s  p95 {pct(infers,95):.2f}s  "
          f"mean RTF {stats.mean(rtfs):.2f}")
    return {"spec": spec, "wer": overall_wer, "p50": pct(infers, 50), "p95": pct(infers, 95),
            "rtf": stats.mean(rtfs) if rtfs else 0.0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, help="personal:<dir> or librispeech:<dir>")
    ap.add_argument("--configs", default="cpu:small.en:int8",
                    help="comma-separated device:model:compute specs")
    ap.add_argument("--limit", type=int, default=None, help="cap number of utterances")
    args = ap.parse_args()

    kind, _, root = args.dataset.partition(":")
    if kind == "personal":
        items = load_personal(root)
    elif kind == "librispeech":
        items = load_librispeech(root, args.limit)
    else:
        print(f"unknown dataset kind: {kind}", file=sys.stderr)
        return 2
    if args.limit:
        items = items[: args.limit]
    if not items:
        print("no items found in dataset", file=sys.stderr)
        return 2
    print(f"dataset {args.dataset}: {len(items)} utterances")

    summary = [run_config(spec.strip(), items) for spec in args.configs.split(",")]

    print("\n================ SUMMARY ================")
    print(f"{'config':32} {'WER%':>7} {'p50':>7} {'p95':>7} {'RTF':>6}")
    for s in summary:
        print(f"{s['spec']:32} {s['wer']*100:7.2f} {s['p50']:7.2f} {s['p95']:7.2f} {s['rtf']:6.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
