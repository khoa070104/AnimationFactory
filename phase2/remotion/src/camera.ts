// The virtual camera: a pure function of scene time (so a cut or a move never restarts anybody's pose). Same maths as tools/shots.py camera_at().
export type CamKey = { t: number; cx: number; cy: number; z: number };
export function cameraAt(keys: CamKey[] | undefined, t: number, W = 1920, H = 1080): [number, number, number] {
  if (!keys || !keys.length) return [W / 2, H / 2, 1];
  const ks = keys.filter((k, i) => i + 1 >= keys.length || keys[i + 1].t !== k.t); // two keys at one time: the later one wins (a cut)
  if (t <= ks[0].t) return [ks[0].cx, ks[0].cy, ks[0].z];
  for (let i = 0; i + 1 < ks.length; i++) {
    const a = ks[i], b = ks[i + 1];
    if (t < b.t) {
      const p = (t - a.t) / (b.t - a.t), e = p * p * (3 - 2 * p);
      return [a.cx + (b.cx - a.cx) * e, a.cy + (b.cy - a.cy) * e, a.z + (b.z - a.z) * e];
    }
  }
  const l = ks[ks.length - 1];
  return [l.cx, l.cy, l.z];
}

// Who faces which way: `looks` = [{t, dir:'left'|'right'} | {t, at:[x,y]}] (from shot gaze); a character without looks keeps its static flip.
export function flipAt(ch: any, t: number): boolean {
  let f = !!ch.flip;
  for (const l of ch.looks || []) {
    if (l.t > t) break;
    if (l.dir) f = l.dir === "left";
    else if (l.at) f = l.at[0] < ch.x - 40 ? true : l.at[0] > ch.x + 40 ? false : f;
  }
  return f;
}

// Focus isolation: opacity factor (1 = shown) of an item that is hidden during the windows [[t0, t1], ...]; 0.15 s fades.
export function hiddenFactor(windows: number[][] | undefined, t: number): number {
  let h = 0;
  for (const [a0, a1] of windows || []) {
    const inn = Math.min(1, Math.max(0, (t - a0) / 0.15)), out = 1 - Math.min(1, Math.max(0, (t - a1) / 0.15));
    h = Math.max(h, Math.min(inn, out));
  }
  return 1 - h;
}
