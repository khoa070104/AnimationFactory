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
