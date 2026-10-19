// Cut-out character rig + helpers for EffectCraft scripts (concatenated after `var P = {...}` by the Python builders).
// The rig is DATA (BI_RIG below = the hand-drawn character Bi; AI characters come from tools/char_rig.py as P.rigs[id] with the same fields), so one
// builder serves every character: parts, pivots, hip/shoulder/neck positions and arm segment lengths all come from the rig.
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
// Bi, expressed as a rig (numbers = what buildBi used to hard-code). Root = feet; y up is negative; joint offsets in 1x px.
var BI_RIG = {
  id: "bi", kinds: ["happy", "neutral", "worried", "surprised", "thinking"],
  shadow: { img: "shadow", pivot: [210, 35] },
  leg: { img: "leg", pivot: [30, 10] }, hip: { x: 36, y: -186 },
  torso: { img: "torso", pivot: [120, 202] }, waistY: -186,
  shoulder: { x: 80, y: -168 }, L1: 85, L2: 85,
  armUpper: { img: "arm_upper", pivot: [20, 15] }, armLower: { img: "arm_lower", pivot: [20, 15] },
  neck: { y: -196 }, head: { img: "head", pivot: [110, 200] }, face: { pattern: "face_{k}", pivot: [110, 200] },
  handK: 1
};
function faceImg(rig, k) { return rig.face.pattern.replace("{k}", k); }
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
function text(comp, str, pos, size, color, rot, align) {
  var l = comp.layers.addText(str);
  var p = l.property("Source Text"), d = p.value;
  d.font = P.font; d.fontSize = size; d.fillColor = color; d.applyFill = true;
  d.justification = (align == "left") ? ParagraphJustification.LEFT_JUSTIFY : ParagraphJustification.CENTER_JUSTIFY;
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

// Two-link IK (segments L1 upper, L2 lower; default 85/85 = Bi). S = shoulder, T = hand target, both in root space (1x px, y up is negative).
// out = +1 elbow bends toward viewer's right (right arm), -1 toward the left. Returns [shoulderRot, elbowRot] in degrees.
function ik(S, T, out, L1, L2) {
  L1 = L1 || 85; L2 = L2 || L1;
  var dx = T[0] - S[0], dy = T[1] - S[1];
  var D = Math.min(Math.sqrt(dx * dx + dy * dy), L1 + L2 - 0.01);
  D = Math.max(D, Math.abs(L1 - L2) + 0.01);
  D = Math.max(D, Math.sqrt(L1 * L1 + L2 * L2 - 2 * L1 * L2 * Math.cos(30 * Math.PI / 180)));   // never closer than an elbow flexion of 150 deg: a short upper arm + long forearm (AI rigs) would fold flat (179 deg) on poses made for Bi
  var A1 = Math.acos(Math.max(-1, Math.min(1, (L1 * L1 + D * D - L2 * L2) / (2 * L1 * D))));    // at the shoulder
  var A2 = Math.acos(Math.max(-1, Math.min(1, (L2 * L2 + D * D - L1 * L1) / (2 * L2 * D))));    // at the wrist
  var tt = Math.atan2(-dx, dy), best = null;
  [1, -1].forEach(function (sg) {
    var ts = tt + sg * A1, tf = tt - sg * A2, score = -Math.sin(ts) * out;   // elbow x offset toward `out`
    if (!best || score > best.score) best = { ts: ts, tf: tf, score: score };
  });
  var r = (best.tf - best.ts) * 180 / Math.PI;
  while (r > 180) r -= 360; while (r <= -180) r += 360;
  return [best.ts * 180 / Math.PI, r];
}
// Hand target given in BI root space (the poses are authored for Bi) -> this rig's root space, then IK. side = "L" | "R".
function handIK(rig, side, T) {
  var sg = (side == "L") ? -1 : 1, k = rig.handK || 1;
  var S = [sg * rig.shoulder.x, rig.waistY + rig.shoulder.y];
  var Tt = [S[0] + (T[0] - sg * 80) * k, S[1] + (T[1] + 354) * k];
  return ik(S, Tt, sg, rig.L1, rig.L2);
}
// pose keys: ls, le (left shoulder / elbow), rs, re (right), head, lean (waist), legL, legR;
// or rHand / lHand = [x, y] hand target in (Bi) root space (IK; keep lean = 0 when used)
// o.rig = rig (default BI_RIG); o.prefix = layer-name prefix for supporting characters; o.flip = face left
function buildBi(comp, o) {
  var rig = o.rig || BI_RIG, px = o.prefix || "";
  var pose = o.pose || {}, g = function (k) { return pose[k] || 0; };
  var R = joint(comp, px + "Bi_root", null, [o.x, o.y]);
  R.property("Scale").setValue([o.scale * 100 * (o.flip ? -1 : 1), o.scale * 100]);
  var bi = { root: R, rig: rig };
  part(comp, px + "shadow", R, rig.shadow.img, rig.shadow.pivot);
  var HL = joint(comp, px + "hip_L", R, [-rig.hip.x, rig.hip.y]), HR = joint(comp, px + "hip_R", R, [rig.hip.x, rig.hip.y]);
  setRot(HL, g("legL")); setRot(HR, g("legR"));
  part(comp, px + "leg_R", HR, rig.leg.img, rig.leg.pivot); part(comp, px + "leg_L", HL, rig.leg.img, rig.leg.pivot);
  var T = joint(comp, px + "waist", R, [0, rig.waistY]); setRot(T, g("lean"));
  var SL = joint(comp, px + "shoulder_L", T, [-rig.shoulder.x, rig.shoulder.y]), SR = joint(comp, px + "shoulder_R", T, [rig.shoulder.x, rig.shoulder.y]);
  var EL = joint(comp, px + "elbow_L", SL, [0, rig.L1]), ER = joint(comp, px + "elbow_R", SR, [0, rig.L1]);
  var ls = g("ls"), le = g("le"), rs = g("rs"), re = g("re");
  if (pose.lHand) { var a = handIK(rig, "L", pose.lHand); ls = a[0]; le = a[1]; }
  if (pose.rHand) { var b = handIK(rig, "R", pose.rHand); rs = b[0]; re = b[1]; }
  setRot(SL, ls); setRot(EL, le); setRot(SR, rs); setRot(ER, re);
  // order bottom -> top: upper arms (sleeves emerge from under the shoulder caps), torso, lower arms + hands, head
  part(comp, px + "arm_L_upper", SL, rig.armUpper.img, rig.armUpper.pivot); part(comp, px + "arm_R_upper", SR, rig.armUpper.img, rig.armUpper.pivot);
  part(comp, px + "torso", T, rig.torso.img, rig.torso.pivot);
  part(comp, px + "arm_L_lower", EL, rig.armLower.img, rig.armLower.pivot); part(comp, px + "arm_R_lower", ER, rig.armLower.img, rig.armLower.pivot);
  var NK = joint(comp, px + "neck", T, [0, rig.neck.y]); setRot(NK, g("head"));
  bi.headLayer = rig.head ? part(comp, px + "head", NK, rig.head.img, rig.head.pivot) : null;
  bi.faces = {};
  // o.allFaces: create every expression layer (hidden except o.face) so motion can cross-fade between them
  var kinds = o.allFaces ? rig.kinds : [o.face];
  kinds.forEach(function (k) {
    var f = part(comp, px + "face_" + k, NK, faceImg(rig, k), rig.face.pivot);
    if (k != o.face) f.property("Opacity").setValue(0);
    bi.faces[k] = f;
    if (!bi.headLayer) bi.headLayer = f;                           // rigs whose heads are complete pictures have no separate base head
  });
  bi.face = bi.faces[o.face];
  // arms drawn in FRONT of the head (e.g. hand on head): o.frontArms = "R" | "L"
  if (o.frontArms) { var side = o.frontArms; comp.layer(px + "arm_" + side + "_lower").moveToBeginning(); }
  // hand attach points (null at the centre of each hand): props held in a hand are parented here, so they follow the arm exactly
  var HNL = joint(comp, px + "hand_L", EL, [0, rig.L2]), HNR = joint(comp, px + "hand_R", ER, [0, rig.L2]);
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
