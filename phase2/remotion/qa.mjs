// Samples what the Remotion renderer draws (same keys, same ease) so Python can run check_motion.row_checks on it, exactly as for the Craft build.
//   node qa.mjs WORKDIR  -> JSON {cues:[{who,action,planned,actual}], rows:{"s01/main":{rig, rows:[...]}}}
import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const engine = resolve(fileURLToPath(new URL(".", import.meta.url)));
const work = resolve(process.argv[2]);
const data = JSON.parse(readFileSync(join(work, "public", "data", "clip.json"), "utf8"));
const { motionLib } = await import(pathToFileURL(join(engine, "src", "motion.ts")).href);
const { buildKeys, makeSampler } = await import(pathToFileURL(join(engine, "src", "timeline.ts")).href);
const M = motionLib(data.motionSrc, data.pngScale);
const cues = [], rows = {};
for (const sc of data.scenes) {
  for (const ch of sc.chars) {
    const rig = data.rigs[ch.rig] || M.BI_RIG;
    const { keys, cues: cs } = buildKeys(M, ch, sc.dur, data.w);
    cs.forEach((c) => cues.push({ who: `${sc.id}/${ch.who}`, ...c }));
    const sample = makeSampler(M, rig, keys, [ch.x, ch.y], ch.face, data.fps);
    const list = [];
    for (let f = 0; f < Math.round(sc.dur * data.fps); f++) {
      const { j, root } = sample(f / data.fps);
      list.push({ f, t: f / data.fps, rootx: root[0], rooty: root[1], shL: j.ls, elL: j.le, shR: j.rs, elR: j.re, neck: j.head, waist: j.lean, hipL: j.legL, hipR: j.legR, held: 0 });
    }
    rows[`${sc.id}/${ch.who}`] = { rig: ch.rig, rows: list };
  }
}
console.log(JSON.stringify({ cues, rows }));
