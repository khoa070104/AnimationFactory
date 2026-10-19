// Bi v2 motion library: named poses, 8 reusable actions, cross-fading expressions.
// Needs lib/bi_rig.jsx. Everything is data: a scene lists actions by name and start time, no per-scene code.
//
// ACTIONS (name: dur at default params): enter, point, cheer, wave, cheek (hand on cheek, worried), hold_phone, shrug, nod
// FACES: happy, neutral, worried, surprised, thinking
var IDLE = { ls: 12, le: 4, rs: -12, re: -4, head: 0, lean: 0, legL: 0, legR: 0 };
var POSES = {
  idle: {},
  point: { rs: -82, re: -4, ls: 10, le: 4 },
  cheer: { ls: 155, le: 12, rs: -155, re: -12, head: -3 },
  cheer_r: { rs: -155, re: -12, head: -3 },        // only the right arm up (the left hand holds something)
  cheer_l: { ls: 155, le: 12, head: -3 },
  wave_a: { rs: -140, re: -35, head: 3 },
  wave_b: { rs: -140, re: -85, head: 3 },
  cheek: { rHand: [90, -425], ls: 14, le: -6, head: -5 },
  cheek_b: { rHand: [90, -425], ls: 14, le: -6, head: -8 },
  phone: { rHand: [95, -300], head: 6 },
  shrug: { ls: 45, le: 75, rs: -45, re: -75, head: 6 },
  write_a: { rHand: [95, -300], lHand: [-95, -300], head: 10 },       // hands at the sides of the chest (like the phone pose): the held notebook reaches across the body
  write_b: { rHand: [100, -314], lHand: [-95, -300], head: 10 },
  carry: { lHand: [-110, -215] },
  nod_a: { head: 8 },
  nod_b: { head: -2 },
  step_a: { legL: 16, legR: -16, ls: -4, rs: 4 },
  step_b: { legL: -16, legR: 16, ls: 28, rs: -28 }
};
var CHANNELS = { ls: "shoulder_L", le: "elbow_L", rs: "shoulder_R", re: "elbow_R", head: "neck", lean: "waist", legL: "hip_L", legR: "hip_R" };
var CH_ORDER = ["ls", "le", "rs", "re", "head", "lean", "legL", "legR"];
var FACE_KINDS = ["happy", "neutral", "worried", "surprised", "thinking"];

function resolvePose(p, rig) {
  var src = (typeof p == "string") ? (POSES[p] || {}) : (p || {}), out = {}, k;
  rig = rig || BI_RIG;
  for (k in IDLE) out[k] = IDLE[k];
  for (k in src) if (k != "rHand" && k != "lHand") out[k] = src[k];
  if (src.lHand) { var a = handIK(rig, "L", src.lHand); out.ls = a[0]; out.le = a[1]; }
  if (src.rHand) { var b = handIK(rig, "R", src.rHand); out.rs = b[0]; out.re = b[1]; }
  return out;
}

// ---- actions: each returns { keys: [{t, pose, face?, root?}], dur } starting at absolute time T ----
var ACTIONS = {
  enter: function (T, p) {
    var from = (p && p.fromX != null) ? p.fromX : -900, k = [], i, walk = (p && p.walk != null) ? p.walk : 1.2, n = Math.max(2, Math.round(walk / 0.2));   // a step every ~0.2 s whatever the walk length
    k.push({ t: T, pose: "idle", root: [from, 0], face: "happy" });      // starts from the same still pose the character waited in off-screen
    for (i = 1; i <= n; i++) k.push({ t: T + walk * i / n, pose: (i % 2 ? "step_b" : "step_a"), root: (i == n ? [14, 0] : null) });
    k.push({ t: T + walk + 0.25, pose: "idle", root: [0, 0] });
    return { keys: k, dur: walk + 0.25 };
  },
  point: function (T, p) {
    var hold = (p && p.hold != null) ? p.hold : 1.0, sp = (p && p.speed) || 0.45;
    return { keys: [{ t: T, pose: "idle" }, { t: T + sp, pose: "point", face: (p && p.face) || "neutral" },
      { t: T + sp + hold, pose: "point" }, { t: T + 2 * sp + hold, pose: "idle" }], dur: 2 * sp + hold };
  },
  // point at several targets in a row without dropping the arm: p.times = absolute times (each aim lands on its time), p.hold after the last
  point_seq: function (T, p) {
    var tm = p.times, hold = (p.hold != null) ? p.hold : 0.9, sp = 0.45, aims = [-88, -82, -76, -72], k = [{ t: tm[0] - sp, pose: "idle", face: p.face || "neutral" }], i;
    for (i = 0; i < tm.length; i++) k.push({ t: tm[i], pose: { rs: aims[i % aims.length], re: -4, ls: 10, le: 4 } });
    k.push({ t: tm[tm.length - 1] + hold, pose: { rs: aims[(tm.length - 1) % aims.length], re: -4, ls: 10, le: 4 } });
    k.push({ t: tm[tm.length - 1] + hold + sp, pose: "idle" });
    return { keys: k, dur: tm[tm.length - 1] + hold + sp - (tm[0] - sp) };
  },
  cheer: function (T, p) {
    var hold = (p && p.hold != null) ? p.hold : 0.8, ps = (p && p.free == "R") ? "cheer_r" : (p && p.free == "L") ? "cheer_l" : "cheer";
    return { keys: [{ t: T, pose: "idle", root: [0, 0] }, { t: T + 0.5, pose: ps, face: "happy", root: [0, -30] },
      { t: T + 0.85, pose: ps, root: [0, 0] }, { t: T + 0.85 + hold, pose: ps }, { t: T + 1.45 + hold, pose: "idle" }], dur: 1.45 + hold };
  },
  wave: function (T, p) {
    var k = [{ t: T, pose: "idle", face: "happy" }, { t: T + 0.4, pose: "wave_a" }], i, t = T + 0.4;
    for (i = 0; i < 6; i++) { t += 0.25; k.push({ t: t, pose: (i % 2 ? "wave_a" : "wave_b") }); }
    k.push({ t: t + 0.4, pose: "idle" });
    return { keys: k, dur: t + 0.4 - T };
  },
  cheek: function (T, p) {
    var hold = (p && p.hold != null) ? p.hold : 1.2;
    return { keys: [{ t: T, pose: "idle" }, { t: T + 0.5, pose: "cheek", face: "worried" }, { t: T + 0.5 + hold / 2, pose: "cheek_b" },
      { t: T + 0.5 + hold, pose: "cheek" }, { t: T + 1.0 + hold, pose: "idle" }], dur: 1.0 + hold };
  },
  hold_phone: function (T, p) {
    var hold = (p && p.hold != null) ? p.hold : 1.4;
    return { keys: [{ t: T, pose: "idle", face: "neutral" }, { t: T + 0.5, pose: "phone" },
      { t: T + 0.5 + hold / 2, pose: "phone", face: "surprised" }, { t: T + 0.5 + hold, pose: "phone" }, { t: T + 1.0 + hold, pose: "idle" }], dur: 1.0 + hold };
  },
  write: function (T, p) {                                  // both hands in front of the chest, the writing hand scribbles; hold a notebook (left) and a pen (right) with `holds`
    var hold = (p && p.hold != null) ? p.hold : 2.0, k = [{ t: T, pose: "idle", face: "thinking" }, { t: T + 0.5, pose: "write_a" }], t = T + 0.5, i;
    for (i = 0; t + 0.2 < T + 0.5 + hold; i++) { t += 0.2; k.push({ t: t, pose: (i % 2 ? "write_a" : "write_b") }); }
    k.push({ t: T + 1.0 + hold, pose: "idle" });
    return { keys: k, dur: 1.0 + hold };
  },
  carry: function (T, p) {                                  // one arm hangs a little away from the body (a held basket/bag swings below the hand)
    var hold = (p && p.hold != null) ? p.hold : 1.6;
    return { keys: [{ t: T, pose: "idle", face: "happy" }, { t: T + 0.5, pose: "carry" }, { t: T + 0.5 + hold, pose: "carry" }, { t: T + 1.0 + hold, pose: "idle" }], dur: 1.0 + hold };
  },
  shrug: function (T, p) {
    return { keys: [{ t: T, pose: "idle" }, { t: T + 0.3, pose: "shrug", face: "thinking" }, { t: T + 1.2, pose: "shrug" }, { t: T + 1.6, pose: "idle" }], dur: 1.6 };
  },
  nod: function (T, p) {
    var k = [{ t: T, pose: "idle", face: "happy" }], i;
    for (i = 0; i < 6; i++) k.push({ t: T + 0.25 * (i + 1), pose: (i % 2 ? "nod_b" : "nod_a") });
    k.push({ t: T + 1.9, pose: "idle" });
    return { keys: k, dur: 1.9 };
  }
};

function easeProp(prop) {
  try {
    for (var k = 1; k <= prop.numKeys; k++) prop.setTemporalEaseAtKey(k, [new KeyframeEase(0, 40)], [new KeyframeEase(0, 40)]);
  } catch (e) {}
}

// Apply a list of keys (any actions concatenated, sorted by t) to a Bi built with allFaces:true.
// base = [x, y] of the root; first face = o.face given to buildBi.
function animateBi(comp, bi, keys, base, startFace) {
  keys.sort(function (a, b) { return a.t - b.t; });
  var vals = {}, c, i, prev = {};
  for (i = 0; i < CH_ORDER.length; i++) vals[CH_ORDER[i]] = [];
  var rootK = [];
  for (i = 0; i < keys.length; i++) {
    var K = keys[i], R = (K.pose != null) ? resolvePose(K.pose, bi.rig) : null;   // a key without a pose only carries a face / root change
    for (var j = 0; R && j < CH_ORDER.length; j++) {
      c = CH_ORDER[j]; var v = R[c];
      // unwrap so shoulders/head/legs never spin the long way round; ELBOWS are NOT unwrapped: going 141 -> -128 must straighten the
      // arm through 0, not sweep through the fully folded pose (180), which would look like the forearm flipping over the upper arm
      if (prev[c] != null && c != "le" && c != "re") v += 360 * Math.round((prev[c] - v) / 360);
      prev[c] = v; vals[c].push([K.t, v]);
    }
    if (K.root) rootK.push([K.t, [base[0] + K.root[0], base[1] + K.root[1]]]);
  }
  for (j = 0; j < CH_ORDER.length; j++) {
    c = CH_ORDER[j]; var pr = bi.joints[CHANNELS[c]].property("Rotation");
    for (i = 0; i < vals[c].length; i++) pr.setValueAtTime(vals[c][i][0], vals[c][i][1]);
    easeProp(pr);
  }
  if (rootK.length) {
    var pp = bi.root.property("Position");
    for (i = 0; i < rootK.length; i++) pp.setValueAtTime(rootK[i][0], rootK[i][1]);
  }
  // expressions: cross-fade 0.15 s
  var ev = [], cur = startFace;
  for (i = 0; i < keys.length; i++) if (keys[i].face && keys[i].face != cur) { ev.push({ t: keys[i].t, face: keys[i].face }); cur = keys[i].face; }
  var f, state = startFace, fk = {};
  for (f = 0; f < FACE_KINDS.length; f++) fk[FACE_KINDS[f]] = [];
  for (i = 0; i < ev.length; i++) {
    for (f = 0; f < FACE_KINDS.length; f++) {
      var kind = FACE_KINDS[f];
      fk[kind].push([ev[i].t - 0.15, kind == state ? 100 : 0]);
      fk[kind].push([ev[i].t, kind == ev[i].face ? 100 : 0]);
    }
    state = ev[i].face;
  }
  for (f = 0; f < FACE_KINDS.length; f++) {
    var arr = fk[FACE_KINDS[f]]; if (!arr.length) continue;
    var op = bi.faces[FACE_KINDS[f]].property("Opacity");
    for (i = 0; i < arr.length; i++) op.setValueAtTime(arr[i][0], arr[i][1]);
  }
}
// show a held prop between t0 and t1 (instant pop in/out at the ends)
function showBetween(layer, t0, t1) {
  var op = layer.property("Opacity");
  var fr = 1 / P.fps;   // keys snap to frames: a 0.01 s offset would collapse into the neighbouring key
  op.setValueAtTime(0, 0); op.setValueAtTime(t0 - fr, 0); op.setValueAtTime(t0, 100); op.setValueAtTime(t1, 100); op.setValueAtTime(t1 + fr, 0);
}
