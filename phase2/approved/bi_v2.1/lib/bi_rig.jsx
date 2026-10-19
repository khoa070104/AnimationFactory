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
  part(comp, "head", NK, "head", [110, 200]);
  bi.faces = {};
  bi.face = part(comp, "face_" + o.face, NK, "face_" + o.face, [110, 200]);
  // arms drawn in FRONT of the head (e.g. hand on head): o.frontArms = "R" | "L"
  if (o.frontArms) { var side = o.frontArms; comp.layer("arm_" + side + "_lower").moveToBeginning(); }
  bi.joints = { waist: T, neck: NK, shoulder_L: SL, shoulder_R: SR, elbow_L: EL, elbow_R: ER, hip_L: HL, hip_R: HR };
  return bi;
}
