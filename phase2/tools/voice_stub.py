"""DRAFT voice: silent audio + estimated word timings, so a scene can be built and reviewed (character motion, cue timing, layout) WITHOUT calling the paid
voice API. It can never be mistaken for a real voice:
  * the scene's audio/<id>.sig holds "stub:<real signature>", which never equals the real signature, so the real voice step regenerates that scene;
  * status.json is not touched here (voice_generated stays false); build_video --draft marks the output as a draft.
Timing = characters / chars_per_sec (cost_model calibrated on the real voice, 15 chars/s by default) spread over the words by their length.
  python voice_stub.py PROJECT [--only s01,s02]"""
import json
import struct
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sbload  # noqa: E402

RATE = 24000


def chars_per_sec():
    import build_storyboard as SBD
    return SBD.CHARS_PER_SEC


def words_json(text, cps):
    words = text.split()
    total = max(1.0, len(text) / cps)
    weights = [len(w) + 1 for w in words]
    scale = total / sum(weights)
    t, out = 0.08, []                                             # the real engine starts the first word almost at once (gaps between scenes then match real ones)
    for w, wt in zip(words, weights):
        d = wt * scale
        out.append({"text": w, "start": round(t, 3), "end": round(t + d * 0.9, 3), "type": "word"})
        t += d
    return [{"words": out, "stub": True}], t + 0.25


def make(proj, sc, sig, cps):
    proj = Path(proj)
    (proj / "audio").mkdir(exist_ok=True)
    wj, total = words_json(sc["voice"], cps)
    f = proj / "audio" / f"{sc['id']}.mp3"
    with wave.open(str(f), "wb") as w:                              # a WAV container under the .mp3 name: FilmCraft probes by content
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(struct.pack("<h", 0) * int(RATE * total))
    f.with_suffix(".words.json").write_text(json.dumps(wj, ensure_ascii=False), encoding="utf-8")
    (proj / "audio" / f"{sc['id']}.sig").write_text("stub:" + sig, encoding="utf-8")
    return total


def run(proj, only=None):
    """Create a stub for every scene that has no REAL up-to-date voice. Returns the list of scene ids stubbed."""
    import voice_project as V
    proj = Path(proj)
    sb = sbload.load_storyboard(proj)
    cps = chars_per_sec()
    done = []
    for sc in sb["scenes"]:
        if only and sc["id"] not in only:
            continue
        sig = V.sig_of(sb, sc)
        sg = proj / "audio" / f"{sc['id']}.sig"
        real = sg.exists() and sg.read_text() == sig and (proj / "audio" / f"{sc['id']}.mp3").exists()
        cur = sg.read_text() if sg.exists() else ""
        if real or cur == "stub:" + sig:
            continue                                                  # real voice already there, or this exact text is already stubbed
        make(proj, sc, sig, cps)
        done.append(sc["id"])
    return done


def is_stub(proj, sid):
    sg = Path(proj) / "audio" / f"{sid}.sig"
    return sg.exists() and sg.read_text().startswith("stub:")


if __name__ == "__main__":
    print("stubbed:", run(sys.argv[1], sys.argv[3].split(",") if len(sys.argv) > 3 and sys.argv[2] == "--only" else None))
