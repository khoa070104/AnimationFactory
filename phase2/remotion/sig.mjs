// Cache signature of one scene's rendered clip. EVERYTHING that can change a pixel or a sound of that scene must be in here:
// its data, the rig data of EVERY character in it, every picture it draws (and their sizes), fonts, audio, output size/fps/png scale, colours, and the renderer code.
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

export const sha = (...parts) => { const h = createHash("sha256"); parts.forEach((p) => h.update(p)); return h.digest("hex").slice(0, 16); };
const fileHash = (f) => (existsSync(f) ? sha(readFileSync(f)) : "-");
const dirHash = (d) => (existsSync(d) ? sha(...readdirSync(d).sort().map((n) => n + fileHash(join(d, n)))) : "-");

export function codeHash(root, data) {
  return sha(...readdirSync(join(root, "src")).sort().map((n) => n + fileHash(join(root, "src", n))), data.motionSrc);
}

export function sceneSignature(root, data, sc, code = codeHash(root, data)) {
  const pub = join(root, "public");
  const imgs = new Set([...sc.prims.filter((p) => p.kind === "prop").map((p) => p.img), ...sc.holds.map((h) => h.prop.replace(/^ai:/, "ai_")), ...(sc.bgImage ? [sc.bgImage] : [])]);
  const names = [...imgs].sort();
  const rigIds = [...new Set(sc.chars.map((c) => c.rig))].sort();
  return sha(
    JSON.stringify(sc), code,
    JSON.stringify([data.fps, data.w, data.h, data.pngScale, data.colors, data.accent]),
    ...names.map((n) => n + fileHash(join(pub, "assets", "png", n + ".png")) + JSON.stringify(data.sizes[n] || null)),
    ...rigIds.map((id) => id + JSON.stringify(data.rigs[id] || null) + dirHash(join(pub, "rigs", id))),   // every character, not only the first
    dirHash(join(pub, "fonts")), fileHash(join(pub, sc.audio)),
  );
}
