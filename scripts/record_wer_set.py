#!/usr/bin/env python3
"""Record a personal WER evaluation set — aligned (audio, reference-text) pairs.

For each item: type the EXACT sentence you will say (the ground-truth reference),
press Enter to START recording, read it aloud, press Enter to STOP. Saves 16 kHz mono
WAVs + appends to references.tsv  (filename<TAB>category<TAB>reference).

Resumable: re-run to add more; it continues numbering and appends to references.tsv.

Usage:
  . .venv/bin/activate
  python scripts/record_wer_set.py --out data/wer_personal --count 20
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from nava.audio.capture import AudioRecorder, save_wav

CATEGORIES = ("plain", "jargon", "noisy")

MIX_GUIDE = """\
Suggested mix for 20 utterances (priorities: English accuracy + noise robustness):
  • 8 PLAIN   — ordinary sentences, quiet room, natural pace (incl. some long run-ons,
                some with numbers/dates, a couple with filler words "um, like").
  • 6 JARGON  — YOUR names/terms/acronyms/product words/file paths/commands you actually
                dictate (this is what tests the custom dictionary later).
  • 6 NOISY   — read with real background noise: fan/AC, music or TV, typing, café/cross-talk.
Vary length (some 3–5 words, some 20+). Speak as you really would when dictating.
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/wer_personal")
    ap.add_argument("--count", type=int, default=20)
    ap.add_argument("--device", default=None, help="input device (default: pulse/pipewire)")
    args = ap.parse_args()

    out = Path(args.out)
    audio_dir = out / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    tsv = out / "references.tsv"

    existing = 0
    if tsv.exists():
        with tsv.open() as f:
            existing = sum(1 for _ in f) - 1  # minus header
        existing = max(existing, 0)
    else:
        with tsv.open("w", newline="") as f:
            csv.writer(f, delimiter="\t").writerow(["filename", "category", "reference"])

    print(MIX_GUIDE)
    print(f"Saving to: {out}   (already have {existing} items)\n")
    rec = AudioRecorder(device=args.device)

    target = args.count
    i = existing
    while i < target:
        n = i + 1
        print(f"── utterance {n}/{target} ─────────────────────────────")
        cat = ""
        while cat not in CATEGORIES:
            cat = input(f"  category {CATEGORIES}: ").strip().lower() or "plain"
        ref = ""
        while not ref.strip():
            ref = input("  reference text (exactly what you'll say): ").strip()
        cmd = input("  [Enter]=START recording, s=skip, q=quit: ").strip().lower()
        if cmd == "q":
            break
        if cmd == "s":
            continue
        rec.start()
        input("  ⏺  recording… [Enter]=STOP ")
        recording = rec.stop()
        if recording.duration_s < 0.3:
            print("  ! too short, retrying this one\n")
            continue
        fname = f"u{n:02d}.wav"
        save_wav(recording, str(audio_dir / fname))
        with tsv.open("a", newline="") as f:
            csv.writer(f, delimiter="\t").writerow([fname, cat, ref])
        print(f"  ✓ saved {fname}  ({recording.duration_s:.1f}s, peak {recording.peak})\n")
        i += 1

    print(f"\nDone. {i} utterances in {out}. references.tsv ready for the benchmark.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
