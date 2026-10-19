// Incremental render. A scene's clip is rendered again only when its signature changes (sig.mjs); the clip is then joined with ffmpeg (stream copy).
//   node render_clip.mjs WORKDIR [--force]     WORKDIR/public/data/clip.json (+ assets, rigs, audio)  ->  WORKDIR/out/clip.mp4, WORKDIR/out/render_log.json
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { codeHash, sceneSignature } from "./sig.mjs";

const engine = resolve(fileURLToPath(new URL(".", import.meta.url)));
const work = resolve(process.argv[2] || join(engine, "_spike"));
const pub = join(work, "public");
const data = JSON.parse(readFileSync(join(pub, "data", "clip.json"), "utf8"));
const force = process.argv.includes("--force");
const code = codeHash(engine, data);

mkdirSync(join(work, "out", "scenes"), { recursive: true });
const manifestFile = join(work, "out", "render_manifest.json");
const manifest = existsSync(manifestFile) && !force ? JSON.parse(readFileSync(manifestFile, "utf8")) : {};
const log = { rendered: [], reused: [], seconds: {} };
const files = [];
for (const sc of data.scenes) {
  const sig = sceneSignature(work, data, sc, code);
  const out = join(work, "out", "scenes", `${sc.id}.mp4`);
  if (manifest[sc.id] === sig && existsSync(out)) {
    log.reused.push(sc.id);
  } else {
    const t0 = Date.now();
    const a = Math.round(sc.start * data.fps), b = a + Math.round(sc.dur * data.fps) - 1;
    execFileSync("npx", ["remotion", "render", "src/index.ts", "Clip", `"${out}"`, `--frames=${a}-${b}`, "--concurrency=4", `--public-dir="${pub}"`], { cwd: engine, shell: true, stdio: "pipe" });
    manifest[sc.id] = sig;
    log.rendered.push(sc.id);
    log.seconds[sc.id] = (Date.now() - t0) / 1000;
  }
  files.push(out);
}
writeFileSync(manifestFile, JSON.stringify(manifest, null, 1));
const list = join(work, "out", "concat.txt");
writeFileSync(list, files.map((f) => `file '${f.replace(/\\/g, "/")}'`).join("\n"));
execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", list, "-c", "copy", join(work, "out", "clip.mp4")]);
writeFileSync(join(work, "out", "render_log.json"), JSON.stringify(log, null, 1));
console.log(JSON.stringify(log));
