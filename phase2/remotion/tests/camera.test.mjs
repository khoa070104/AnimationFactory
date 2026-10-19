import test from "node:test";
import assert from "node:assert/strict";
import { cameraAt, flipAt } from "../src/camera.ts";

const keys = [{ t: 0, cx: 960, cy: 540, z: 1 }, { t: 2, cx: 960, cy: 540, z: 1 }, { t: 2.5, cx: 1500, cy: 400, z: 2 }, { t: 3.999, cx: 1500, cy: 400, z: 2 }, { t: 4, cx: 600, cy: 500, z: 1.5 }];
test("no keys = the whole canvas", () => assert.deepEqual(cameraAt([], 1), [960, 540, 1]));
test("hold, eased move (smoothstep midpoint), hold", () => {
  assert.deepEqual(cameraAt(keys, 1), [960, 540, 1]);
  const m = cameraAt(keys, 2.25);
  assert.ok(Math.abs(m[2] - 1.5) < 1e-9 && Math.abs(m[0] - 1230) < 1e-6, m);
  assert.deepEqual(cameraAt(keys, 3), [1500, 400, 2]);
});
test("a cut (key 1 ms earlier) changes the frame at once, not by drifting", () => {
  assert.deepEqual(cameraAt(keys, 3.99), [1500, 400, 2]);
  assert.deepEqual(cameraAt(keys, 4.01), [600, 500, 1.5]);
});
test("two keys at the same time: the later wins", () => {
  assert.deepEqual(cameraAt([{ t: 0, cx: 1, cy: 1, z: 1 }, { t: 1, cx: 2, cy: 2, z: 1 }, { t: 1, cx: 9, cy: 9, z: 3 }, { t: 2, cx: 9, cy: 9, z: 3 }], 1.5), [9, 9, 3]);
});
test("facing follows the latest look", () => {
  const ch = { x: 500, flip: false, looks: [{ t: 1, at: [1500, 500] }, { t: 3, dir: "left" }] };
  assert.equal(flipAt(ch, 0.5), false);
  assert.equal(flipAt(ch, 2), false);          // looks right at x=1500
  assert.equal(flipAt(ch, 3.5), true);
  assert.equal(flipAt({ x: 500, flip: true, looks: [{ t: 0, at: [520, 0] }] }, 1), true);   // target straight ahead: keep facing
});
import { hiddenFactor } from "../src/camera.ts";
test("focus isolation fades an item out inside its windows and back in after", () => {
  assert.equal(hiddenFactor(undefined, 1), 1);
  assert.equal(hiddenFactor([[2, 4]], 1.9), 1);
  assert.ok(hiddenFactor([[2, 4]], 2.075) > 0.4 && hiddenFactor([[2, 4]], 2.075) < 0.6);
  assert.equal(hiddenFactor([[2, 4]], 3), 0);
  assert.equal(hiddenFactor([[2, 4]], 4.2), 1);
});
