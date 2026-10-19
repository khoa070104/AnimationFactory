"""Decode-based audio/video duration through FilmCraft (independent of any duration metadata in the file).
probe_seconds(f): FilmCraft's own probe; decoded_seconds(audio): render the audio to WAV and measure the WAV.
Usage: python decode_check.py FILE [...]"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import toolpaths

TICKS = 254016000000


def probe_seconds(f):
    r = subprocess.run([toolpaths.filmcraft(), "probe", str(f), "--compact"], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"FilmCraft probe failed for {f}: {r.stderr[-200:]}")
    return json.loads(r.stdout)["duration"] / TICKS


def decoded_seconds(audio):
    F = toolpaths.filmcraft()
    tmp = Path(tempfile.mkdtemp())
    proj, wav = tmp / "d.fcproj", tmp / "d.wav"
    p = str(Path(audio).resolve()).replace("\\", "/")
    seq = [{"id": "file.newSequence", "params": {"name": "S", "width": 1920, "height": 1080, "fps": 30}},
           {"id": "file.import", "params": {"paths": [p]}}]
    r = subprocess.run([F, "--save-as", str(proj), "run", "-"], input="\n".join(json.dumps(x) for x in seq), capture_output=True, text=True)
    item = json.loads(r.stdout.splitlines()[-1])["result"]["items"][0]
    place = {"id": "timeline.place", "params": {"item": item, "audioTrack": "A1", "seconds": 0, "video": False}}
    subprocess.run([F, "--project", str(proj), "--save", "run", "-"], input=json.dumps(place), capture_output=True, text=True, check=True)
    subprocess.run([F, "--project", str(proj), "export", str(wav), "--format", "wav"], capture_output=True, text=True, check=True)
    return probe_seconds(wav)


if __name__ == "__main__":
    for f in sys.argv[1:]:
        print(f"{f}: probe={probe_seconds(f):.2f}s decoded={decoded_seconds(f):.2f}s")
