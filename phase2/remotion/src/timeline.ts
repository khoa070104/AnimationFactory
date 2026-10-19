import { Easing } from "remotion";

// Port of charTimeline() (lib/scene_anim.jsx) + animateBi() key sampling: actions are serialised per character, entrances come from the nearest screen edge,
// holds/walks are shortened so the next cue is not delayed, then joint values are interpolated with the same ease (speed 0, influence 40%).
type Key = { t: number; pose?: any; face?: string; root?: [number, number] };
const ease = Easing.bezier(0.4, 0, 0.6, 1);

export function buildKeys(M: any, ch: any, dur: number, W: number) {
  const keys: Key[] = [];
  const actions = JSON.parse(JSON.stringify(ch.actions)) as any[];
  const order = actions.sort((a, b) => a.T - b.T);
  const side = ch.x < W / 2 ? -1 : 1;
  order.forEach((a) => {
    if (a.name === "enter") {
      a.params = a.params || {};
      if (a.params.fromX == null) a.params.fromX = side * 900;
    }
  });
  let busyUntil = 0;
  let enterFrom: number | null = null;
  const cues: any[] = [];
  order.forEach((a, idx) => {
    const T0 = Math.max(a.T, busyUntil);
    cues.push({ action: a.name, planned: a.T, actual: T0 });
    let r = M.ACTIONS[a.name](T0, a.params || {});
    const nxt = idx + 1 < order.length ? order[idx + 1].T : null;
    if (nxt !== null && a.name === "enter" && T0 + r.dur > nxt) {
      const pe = { ...(a.params || {}) };
      pe.walk = Math.min(Math.max(0.5, nxt - T0 - 0.25), 1.2);
      pe.fromX = ((a.params.fromX != null ? a.params.fromX : side * 900) * pe.walk) / 1.2;
      r = M.ACTIONS.enter(T0, pe);
      if (enterFrom === null && order[0] === a) enterFrom = pe.fromX;
    }
    if (a.name === "enter" && enterFrom === null && order[0] === a) enterFrom = a.params.fromX;
    if (nxt !== null && a.params && a.params.hold > 0.2 && T0 + r.dur > nxt) {
      const ph = { ...a.params };
      ph.hold = Math.max(0.2, a.params.hold - (T0 + r.dur - nxt));
      r = M.ACTIONS[a.name](T0, ph);
    }
    busyUntil = Math.max(busyUntil, T0 + r.dur);
    let ks = r.keys as Key[];
    if (a.stay) {
      const last = ks[ks.length - 2];
      ks = ks.slice(0, ks.length - 1);
      ks.push({ t: dur - 0.05, pose: last.pose });
    }
    ks.forEach((k) => keys.push(k));
  });
  const firstT = keys.length ? Math.min(...keys.map((k) => k.t)) : 1e9;
  if (firstT > 0.05) {
    const e0 = order.length && order[0].name === "enter" ? order[0] : null;
    keys.push(e0 ? { t: 0, pose: "idle", root: [enterFrom != null ? enterFrom : e0.params.fromX, 0] } : { t: 0, pose: "idle", root: [0, 0] });
  }
  if (ch.rest) keys.push({ t: 0.7, pose: ch.rest });
  (ch.faceCues || []).forEach((f: any) => keys.push({ t: f.t, face: f.face }));
  return { keys, cues };
}

export function makeSampler(M: any, rig: any, keys: Key[], base: [number, number], startFace: string, fps = 30) {
  // EffectCraft puts keyframes on the frame grid; so do we, which makes both renderers (and the shared motion QA) see the same curves
  keys.forEach((k) => (k.t = Math.round(k.t * fps) / fps));
  keys.sort((a, b) => a.t - b.t);
  const vals: Record<string, [number, number][]> = {};
  M.CH_ORDER.forEach((c: string) => (vals[c] = []));
  const prev: Record<string, number> = {};
  const rootK: [number, [number, number]][] = [];
  keys.forEach((K) => {
    const R = K.pose != null ? M.resolvePose(K.pose, rig) : null;
    if (R) {
      M.CH_ORDER.forEach((c: string) => {
        let v = R[c];
        if (prev[c] != null && c !== "le" && c !== "re") v += 360 * Math.round((prev[c] - v) / 360);
        prev[c] = v;
        vals[c].push([K.t, v]);
      });
    }
    if (K.root) rootK.push([K.t, [base[0] + K.root[0], base[1] + K.root[1]]]);
  });
  // two keys at the same time: the later one wins (setValueAtTime replaces a key at that time), so no zero-length segment can jump
  const dedupe = <V,>(arr: [number, V][]) => arr.filter((k, i) => i + 1 >= arr.length || arr[i + 1][0] !== k[0]);
  M.CH_ORDER.forEach((c: string) => (vals[c] = dedupe(vals[c])));
  const rootKd = dedupe(rootK);
  const faceEv: { t: number; face: string }[] = [];
  let cur = startFace;
  keys.forEach((k) => {
    if (k.face && k.face !== cur) {
      faceEv.push({ t: k.t, face: k.face });
      cur = k.face;
    }
  });
  const interp = (arr: [number, number][], t: number) => {
    if (!arr.length) return 0;
    if (t <= arr[0][0]) return arr[0][1];
    for (let i = 0; i < arr.length - 1; i++) {
      if (t < arr[i + 1][0]) {
        const p = (t - arr[i][0]) / (arr[i + 1][0] - arr[i][0]);
        return arr[i][1] + (arr[i + 1][1] - arr[i][1]) * ease(p);
      }
    }
    return arr[arr.length - 1][1];
  };
  return (t: number) => {
    const j: Record<string, number> = {};
    M.CH_ORDER.forEach((c: string) => (j[c] = interp(vals[c], t)));
    let root = base;
    if (rootKd.length) {
      root = [interp(rootKd.map((r) => [r[0], r[1][0]] as [number, number]), t), interp(rootKd.map((r) => [r[0], r[1][1]] as [number, number]), t)];
    }
    const w: Record<string, number> = {};
    M.FACE_KINDS.forEach((k: string) => (w[k] = 0));
    let state = startFace;
    let done = false;
    for (const e of faceEv) {
      if (t >= e.t) {
        state = e.face;
      } else if (t > e.t - 0.15) {
        const a = (t - (e.t - 0.15)) / 0.15;
        w[state] += 1 - a;
        w[e.face] += a;
        done = true;
        break;
      } else break;
    }
    if (!done) w[state] = 1;
    return { j, root, faces: w };
  };
}
