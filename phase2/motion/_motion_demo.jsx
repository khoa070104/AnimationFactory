var P = {"assets": "D:/AnimationFactory/phase2/assets", "out": "D:/AnimationFactory/phase2/motion/motion_demo.ecproj", "w": 1920, "h": 1080, "fps": 30, "pngScale": 2, "font": "Inter", "text": {"font": "Inter", "dark": [0.114, 0.114, 0.122], "good": [0.18, 0.62, 0.36], "bad": [0.84, 0.27, 0.27], "minHeadlinePx": 64, "minBodyPx": 44, "minLabelPx": 40}, "bg": [1.0, 0.9647058823529412, 0.8980392156862745], "bgAlt": [0.9058823529411765, 0.9333333333333333, 0.9607843137254902], "colors": {"bi": [0.9490196078431372, 0.4196078431372549, 0.12941176470588237]}, "debug": false, "comp": null};
// Bi v2 rig + helpers for EffectCraft scripts (concatenated after `var P = {...}` by the Python builders).
// Conventions (see STYLE_GUIDE.md):
//  * every joint is a null with Anchor (0,0); layers are parented first, then Rotation/Scale are reset and Position set (assigning a parent
//    makes EffectCraft keep the world pose by rewriting the child's local rotation/scale/position);
//  * PNGs are rendered at 2x (PS); parts use Scale 50% and Anchor = pivot(1x) * PS;
//  * rotation > 0 is clockwise: the viewer's LEFT arm swings outward with +, the RIGHT arm with -.
var PS = P.pngScale;
var IMGS = {};
function img(name) {
  if (!IMGS[name]) IMGS[name] = app.project.importFile(new ImportOptions(new File(P.assets + "/png/" + name + ".png")));
  return IMGS[name];
}
function joint(comp, name, parent, pos) {
  var n = comp.layers.addNull(); n.name = name;
  n.property("Anchor Point").setValue([0, 0]);
  if (parent) n.parent = parent;
  // EffectCraft keeps the WORLD pose when a parent is assigned (it back-fills local rotation/scale), so reset them
  n.property("Rotation").setValue(0); n.property("Scale").setValue([100, 100]);
  n.property("Position").setValue(pos);
  return n;
}
// image part hung on a joint, pivot given in 1x image pixels
function part(comp, name, parent, imgName, pivot) {
  var l = comp.layers.add(img(imgName)); l.name = name;
  if (parent) l.parent = parent;
  l.property("Rotation").setValue(0);
  l.property("Anchor Point").setValue([pivot[0] * PS, pivot[1] * PS]);
  l.property("Scale").setValue([100 / PS, 100 / PS]);
  l.property("Position").setValue([0, 0]);
  return l;
}
// free-standing prop, pivot = centre unless given; scale in 1.0 = natural size
function prop(comp, name, imgName, pos, scale, rot, pivot) {
  var l = comp.layers.add(img(imgName)); l.name = name;
  var w = l.source.width, h = l.source.height;
  l.property("Anchor Point").setValue(pivot ? [pivot[0] * PS, pivot[1] * PS] : [w / 2, h / 2]);
  l.property("Scale").setValue([100 * scale / PS, 100 * scale / PS]);
  l.property("Position").setValue(pos);
  if (rot) l.property("Rotation").setValue(rot);
  return l;
}
function text(comp, str, pos, size, color, rot) {
  var l = comp.layers.addText(str);
  var p = l.property("Source Text"), d = p.value;
  d.font = P.font; d.fontSize = size; d.fillColor = color; d.applyFill = true;
  d.justification = ParagraphJustification.CENTER_JUSTIFY;
  try { d.fontStyle = "Bold"; } catch (e) {}
  p.setValue(d);
  l.property("Position").setValue(pos);
  if (rot) l.property("Rotation").setValue(rot);
  return l;
}
function background(comp, hex) {
  var s = comp.layers.addSolid(hex, "bg", P.w, P.h, 1); s.moveToEnd(); return s;
}
function setRot(l, deg) { l.property("Rotation").setValue(deg); }

// Two-link IK (both segments 85 px). S = shoulder, T = hand target, both in root space (1x px, y up is negative).
// out = +1 elbow bends toward viewer's right (right arm), -1 toward the left. Returns [shoulderRot, elbowRot] in degrees.
function ik(S, T, out) {
  var dx = T[0] - S[0], dy = T[1] - S[1], L = 85;
  var D = Math.min(Math.sqrt(dx * dx + dy * dy), 2 * L - 0.01);
  var A = Math.acos(D / (2 * L)), tt = Math.atan2(-dx, dy), best = null;
  [1, -1].forEach(function (sg) {
    var ts = tt + sg * A, tf = tt - sg * A, score = -Math.sin(ts) * out;   // elbow x offset toward `out`
    if (!best || score > best.score) best = { ts: ts, tf: tf, score: score };
  });
  var r = (best.tf - best.ts) * 180 / Math.PI;
  while (r > 180) r -= 360; while (r <= -180) r += 360;
  return [best.ts * 180 / Math.PI, r];
}
// pose keys: ls, le (left shoulder / elbow), rs, re (right), head, lean (waist), legL, legR;
// or rHand / lHand = [x, y] hand target in root space (IK; keep lean = 0 when used)
function buildBi(comp, o) {
  var pose = o.pose || {}, g = function (k) { return pose[k] || 0; };
  var R = joint(comp, "Bi_root", null, [o.x, o.y]);
  R.property("Scale").setValue([o.scale * 100, o.scale * 100]);
  var bi = { root: R };
  part(comp, "shadow", R, "shadow", [210, 35]);
  var HL = joint(comp, "hip_L", R, [-36, -186]), HR = joint(comp, "hip_R", R, [36, -186]);
  setRot(HL, g("legL")); setRot(HR, g("legR"));
  part(comp, "leg_R", HR, "leg", [30, 10]); part(comp, "leg_L", HL, "leg", [30, 10]);
  var T = joint(comp, "waist", R, [0, -186]); setRot(T, g("lean"));
  var SL = joint(comp, "shoulder_L", T, [-80, -168]), SR = joint(comp, "shoulder_R", T, [80, -168]);
  var EL = joint(comp, "elbow_L", SL, [0, 85]), ER = joint(comp, "elbow_R", SR, [0, 85]);
  var ls = g("ls"), le = g("le"), rs = g("rs"), re = g("re");
  if (pose.lHand) { var a = ik([-80, -354], pose.lHand, -1); ls = a[0]; le = a[1]; }
  if (pose.rHand) { var b = ik([80, -354], pose.rHand, 1); rs = b[0]; re = b[1]; }
  setRot(SL, ls); setRot(EL, le); setRot(SR, rs); setRot(ER, re);
  // order bottom -> top: upper arms (sleeves emerge from under the shoulder caps), torso, lower arms + hands, head
  part(comp, "arm_L_upper", SL, "arm_upper", [20, 15]); part(comp, "arm_R_upper", SR, "arm_upper", [20, 15]);
  part(comp, "torso", T, "torso", [120, 202]);
  part(comp, "arm_L_lower", EL, "arm_lower", [20, 15]); part(comp, "arm_R_lower", ER, "arm_lower", [20, 15]);
  var NK = joint(comp, "neck", T, [0, -196]); setRot(NK, g("head"));
  bi.headLayer = part(comp, "head", NK, "head", [110, 200]);
  bi.faces = {};
  // o.allFaces: create every expression layer (hidden except o.face) so motion can cross-fade between them
  var kinds = o.allFaces ? ["happy", "neutral", "worried", "surprised", "thinking"] : [o.face];
  kinds.forEach(function (k) {
    var f = part(comp, "face_" + k, NK, "face_" + k, [110, 200]);
    if (k != o.face) f.property("Opacity").setValue(0);
    bi.faces[k] = f;
  });
  bi.face = bi.faces[o.face];
  // arms drawn in FRONT of the head (e.g. hand on head): o.frontArms = "R" | "L"
  if (o.frontArms) { var side = o.frontArms; comp.layer("arm_" + side + "_lower").moveToBeginning(); }
  // hand attach points (null at the centre of each hand): props held in a hand are parented here, so they follow the arm exactly
  var HNL = joint(comp, "hand_L", EL, [0, 85]), HNR = joint(comp, "hand_R", ER, [0, 85]);
  bi.joints = { waist: T, neck: NK, shoulder_L: SL, shoulder_R: SR, elbow_L: EL, elbow_R: ER, hand_L: HNL, hand_R: HNR, hip_L: HL, hip_R: HR };
  return bi;
}

// Prop held in a hand. pivot = grip point in 1x image px (default: image centre); off = extra [x, y] offset in hand space.
function holdProp(comp, bi, side, imgName, scale, pivot, rot, off) {
  var h = bi.joints["hand_" + side];
  var l = comp.layers.add(img(imgName)); l.name = "held_" + imgName;
  l.parent = h;
  l.property("Rotation").setValue(rot || 0);
  var pv = pivot || [l.source.width / PS / 2, l.source.height / PS / 2];
  l.property("Anchor Point").setValue([pv[0] * PS, pv[1] * PS]);
  l.property("Scale").setValue([100 * scale / PS, 100 * scale / PS]);
  l.property("Position").setValue(off || [0, 0]);
  l.moveAfter(bi.headLayer);           // just below the head layer, so above torso, arms and hands
  return l;
}

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
  wave_a: { rs: -140, re: -35, head: 3 },
  wave_b: { rs: -140, re: -85, head: 3 },
  cheek: { rHand: [90, -425], ls: 14, le: -6, head: -5 },
  cheek_b: { rHand: [90, -425], ls: 14, le: -6, head: -8 },
  phone: { rHand: [95, -300], head: 6 },
  shrug: { ls: 45, le: 75, rs: -45, re: -75, head: 6 },
  nod_a: { head: 8 },
  nod_b: { head: -2 },
  step_a: { legL: 16, legR: -16, ls: -8, rs: 8 },
  step_b: { legL: -16, legR: 16, ls: 28, rs: -28 }
};
var CHANNELS = { ls: "shoulder_L", le: "elbow_L", rs: "shoulder_R", re: "elbow_R", head: "neck", lean: "waist", legL: "hip_L", legR: "hip_R" };
var CH_ORDER = ["ls", "le", "rs", "re", "head", "lean", "legL", "legR"];
var FACE_KINDS = ["happy", "neutral", "worried", "surprised", "thinking"];

function resolvePose(p) {
  var src = (typeof p == "string") ? (POSES[p] || {}) : (p || {}), out = {}, k;
  for (k in IDLE) out[k] = IDLE[k];
  for (k in src) if (k != "rHand" && k != "lHand") out[k] = src[k];
  if (src.lHand) { var a = ik([-80, -354], src.lHand, -1); out.ls = a[0]; out.le = a[1]; }
  if (src.rHand) { var b = ik([80, -354], src.rHand, 1); out.rs = b[0]; out.re = b[1]; }
  return out;
}

// ---- actions: each returns { keys: [{t, pose, face?, root?}], dur } starting at absolute time T ----
var ACTIONS = {
  enter: function (T, p) {
    var from = (p && p.fromX != null) ? p.fromX : -900, k = [], i, n = 6, walk = 1.2;
    k.push({ t: T, pose: "step_a", root: [from, 0], face: "happy" });
    for (i = 1; i <= n; i++) k.push({ t: T + walk * i / n, pose: (i % 2 ? "step_b" : "step_a"), root: (i == n ? [14, 0] : null) });
    k.push({ t: T + walk + 0.25, pose: "idle", root: [0, 0] });
    return { keys: k, dur: walk + 0.25 };
  },
  point: function (T, p) {
    var hold = (p && p.hold != null) ? p.hold : 1.0, sp = (p && p.speed) || 0.45;
    return { keys: [{ t: T, pose: "idle" }, { t: T + sp, pose: "point", face: (p && p.face) || "neutral" },
      { t: T + sp + hold, pose: "point" }, { t: T + 2 * sp + hold, pose: "idle" }], dur: 2 * sp + hold };
  },
  cheer: function (T, p) {
    var hold = (p && p.hold != null) ? p.hold : 0.8;
    return { keys: [{ t: T, pose: "idle", root: [0, 0] }, { t: T + 0.5, pose: "cheer", face: "happy", root: [0, -30] },
      { t: T + 0.85, pose: "cheer", root: [0, 0] }, { t: T + 0.85 + hold, pose: "cheer" }, { t: T + 1.45 + hold, pose: "idle" }], dur: 1.45 + hold };
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
    var K = keys[i], R = resolvePose(K.pose);
    for (var j = 0; j < CH_ORDER.length; j++) {
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

// Motion demo: every action + a chain of direct pose-to-pose transitions. Needs bi_rig.jsx + bi_motion.jsx.
// P.debug: add coloured markers on hands/elbows for pixel verification.
var BASEX = 700, BASEY = 975;
var DUR = 0;
var timeline = [], labels = [], T = 0.3;
function add(name, label, p) {
  var a = ACTIONS[name](T, p);
  for (var i = 0; i < a.keys.length; i++) timeline.push(a.keys[i]);
  labels.push({ t: T, t1: T + a.dur + 0.4, text: label });
  var t0 = T; T += a.dur + 0.4;
  return { t0: t0, t1: t0 + a.dur };
}
add("enter", "1 · Xuất hiện (đi vào)", { fromX: -700 });
var aP = add("point", "2 · Chỉ tay", { hold: 1.2 });
add("cheer", "3 · Giơ tay mừng", {});
add("wave", "4 · Vẫy tay", {});
add("cheek", "5 · Tay lên má (lo lắng)", {});
var aH = add("hold_phone", "6 · Cầm điện thoại", {});
add("shrug", "7 · Nhún vai", {});
add("nod", "8 · Gật đầu", {});
// chain: direct pose-to-pose, no pass through idle (0.45 s per transition)
var chain = ["point", "cheek", "cheer", "wave_a", "shrug", "phone", "point", "cheek", "idle"], ct = T;
labels.push({ t: T, t1: T + chain.length * 0.55 + 1.2, text: "9 · Chuyển tiếp liên tục giữa tư thế" });
for (var ci = 0; ci < chain.length; ci++) timeline.push({ t: ct + 0.55 * (ci + 1), pose: chain[ci], face: (ci == 1 ? "worried" : ci == 2 ? "happy" : ci == 5 ? "surprised" : ci == 7 ? "worried" : null) });
T = ct + chain.length * 0.55 + 1.2;
DUR = T;
var cm = app.project.items.addComp("MotionDemo", P.w, P.h, 1, DUR, P.fps);
var bi = buildBi(cm, { x: BASEX, y: BASEY, scale: 1.0, face: "neutral", allFaces: true, pose: {} });
var held = holdProp(cm, bi, "R", "phone", 0.34, [150, 470], 0, [0, 0]);   // grip at the bottom of the phone
showBetween(held, aH.t0 + 0.3, aH.t1 + 0.2);
// the board that "point" refers to
prop(cm, "board", "board", [1450, 480], 0.8);
text(cm, "Chi tiêu", [1450, 330], 54, P.text.dark);
animateBi(cm, bi, timeline, [BASEX, BASEY], "neutral");
for (var li = 0; li < labels.length; li++) {
  var L = text(cm, labels[li].text, [1250, 130], 60, P.colors.bi);
  var o = L.property("Opacity");
  var fr = 1 / P.fps;
  o.setValueAtTime(0, 0); o.setValueAtTime(labels[li].t - fr, 0); o.setValueAtTime(labels[li].t, 100); o.setValueAtTime(labels[li].t1 - fr, 100); o.setValueAtTime(labels[li].t1, 0);
}
if (P.debug) {
  function marker(name, parent, color) {
    var m = cm.layers.addSolid(color, name, 14, 14, 1);
    m.parent = parent; m.property("Rotation").setValue(0); m.property("Scale").setValue([100, 100]);
    m.property("Anchor Point").setValue([7, 7]); m.property("Position").setValue([0, 0]); return m;
  }
  marker("m_handR", bi.joints.hand_R, [1, 0, 1]); marker("m_handL", bi.joints.hand_L, [0, 1, 1]);
  marker("m_elbR", bi.joints.elbow_R, [0, 1, 0]); marker("m_elbL", bi.joints.elbow_L, [0, 0, 1]);
}
background(cm, P.bg);
app.project.save(new File(P.out));
writeLn("saved " + P.out + " dur=" + DUR);
writeLn("SCHEDULE " + [aP.t0, aP.t1, aH.t0, aH.t1].join(","));
