import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { sceneSignature } from "../sig.mjs";

function fixture() {
  const root = mkdtempSync(join(tmpdir(), "afsig-"));
  for (const d of ["src", "public/assets/png", "public/rigs/minh", "public/rigs/linh", "public/fonts", "public/audio"]) mkdirSync(join(root, d), { recursive: true });
  writeFileSync(join(root, "src/a.ts"), "code");
  writeFileSync(join(root, "public/assets/png/pen.png"), "pen");
  writeFileSync(join(root, "public/assets/png/basket.png"), "basket");
  writeFileSync(join(root, "public/rigs/minh/torso.png"), "m");
  writeFileSync(join(root, "public/rigs/linh/torso.png"), "l");
  writeFileSync(join(root, "public/fonts/arialbd.ttf"), "font");
  writeFileSync(join(root, "public/audio/s1.wav"), "a1");
  const sc = (id) => ({ id, start: 0, dur: 5, audio: "audio/s1.wav", bgImage: null, prims: [{ kind: "prop", img: "pen" }], holds: [{ prop: "pen", side: "R" }],
    chars: [{ rig: "minh", who: "main", x: 500 }, { rig: "linh", who: "cast1", x: 1500 }] });
  const data = { fps: 30, w: 1920, h: 1080, pngScale: 2, colors: { dark: [0, 0, 0] }, accent: { blue: "#00f" }, motionSrc: "motion", sizes: { pen: [36, 220], basket: [240, 190] },
    rigs: { minh: { shoulder: { x: 80 } }, linh: { shoulder: { x: 76 } } }, scenes: [sc("s1")] };
  return { root, data, sc: data.scenes[0] };
}
const sig = (f) => sceneSignature(f.root, f.data, f.sc);

test("same input -> same signature", () => { const f = fixture(); assert.equal(sig(f), sig(f)); });
test("a SUPPORTING character's rig data changes the signature", () => { const f = fixture(); const a = sig(f); f.data.rigs.linh.shoulder.x += 1; assert.notEqual(sig(f), a); });
test("a supporting character's picture changes the signature", () => { const f = fixture(); const a = sig(f); writeFileSync(join(f.root, "public/rigs/linh/torso.png"), "l2"); assert.notEqual(sig(f), a); });
for (const [name, mut] of [["fps", (d) => (d.fps = 24)], ["width", (d) => (d.w = 1280)], ["height", (d) => (d.h = 720)], ["png scale", (d) => (d.pngScale = 3)],
  ["colours", (d) => (d.colors.dark = [1, 1, 1])], ["accent colours", (d) => (d.accent.blue = "#0f0")], ["image size table", (d) => (d.sizes.pen = [40, 220])]]) {
  test(`${name} changes the signature`, () => { const f = fixture(); const a = sig(f); mut(f.data); assert.notEqual(sig(f), a); });
}
test("font file changes the signature", () => { const f = fixture(); const a = sig(f); writeFileSync(join(f.root, "public/fonts/arialbd.ttf"), "font2"); assert.notEqual(sig(f), a); });
test("audio changes the signature", () => { const f = fixture(); const a = sig(f); writeFileSync(join(f.root, "public/audio/s1.wav"), "a2"); assert.notEqual(sig(f), a); });
test("renderer code and motion library change the signature", () => {
  const f = fixture(); const a = sig(f);
  writeFileSync(join(f.root, "src/a.ts"), "code2"); const b = sig(f); assert.notEqual(b, a);
  f.data.motionSrc = "motion2"; assert.notEqual(sig(f), b);
});
test("a picture this scene does not use does NOT change the signature", () => { const f = fixture(); const a = sig(f); writeFileSync(join(f.root, "public/assets/png/basket.png"), "other"); f.data.sizes.basket = [1, 1]; assert.equal(sig(f), a); });
test("another scene's data does not change this scene's signature", () => { const f = fixture(); const a = sig(f); f.data.scenes.push({ ...f.sc, id: "s2" }); f.data.scenes[1].dur = 9; assert.equal(sig(f), a); });
test("the held prop picture and a background image are included", () => {
  const f = fixture(); const a = sig(f); writeFileSync(join(f.root, "public/assets/png/pen.png"), "pen2"); assert.notEqual(sig(f), a);
  f.sc.bgImage = "ai_kitchen"; const b = sig(f); writeFileSync(join(f.root, "public/assets/png/ai_kitchen.png"), "bg"); assert.notEqual(sig(f), b);
});
