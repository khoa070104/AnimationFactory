"""Decode-based duration: render an audio file through FilmCraft to WAV and measure the WAV.
Independent of any duration metadata in the source file. Usage: python decode_check.py FILE.mp3 [...]"""
import json, subprocess, sys, tempfile
from pathlib import Path
F = r"C:\Program Files\FilmCraft\filmcraft-cli.exe"; T = 254016000000

def probe_seconds(f):
    return json.loads(subprocess.run([F, "probe", str(f), "--compact"], capture_output=True, text=True).stdout)["duration"] / T

def decoded_seconds(mp3):
    tmp = Path(tempfile.mkdtemp()); proj = tmp / "d.fcproj"; wav = tmp / "d.wav"
    p = str(Path(mp3).resolve()).replace("\\", "/")
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
        print(f"{f}: probe={probe_seconds(f):.2f}s decoded-to-WAV={decoded_seconds(f):.2f}s")
