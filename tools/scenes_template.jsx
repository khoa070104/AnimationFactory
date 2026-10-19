// Prepended by build_scenes.py:  var P = {...params...};
var A = P.assets;
function imp(n) { return app.project.importFile(new ImportOptions(new File(A + "/" + n + ".png"))); }
var IMG = {};
["head","face_happy","face_worried","face_normal","torso","legs","arm","phone","coin"].forEach(function (n) { IMG[n] = imp(n); });

function easeKeys(prop) {
  try {
    for (var k = 1; k <= prop.numKeys; k++) {
      prop.setTemporalEaseAtKey(k, [new KeyframeEase(0, 70)], [new KeyframeEase(0, 70)]);
    }
  } catch (e) {}
}
function part(comp, name, parent, pos, anchor, img) {
  var l = comp.layers.add(IMG[img]); l.name = name;
  l.property("Anchor Point").setValue(anchor); l.property("Position").setValue(pos);
  if (parent) l.parent = parent; return l;
}
function text(comp, str, pos, size, color, just) {
  var l = comp.layers.addText(str);
  var p = l.property("Source Text"); var d = p.value;
  d.fontSize = size; d.fillColor = color; d.applyFill = true; d.justification = just || ParagraphJustification.CENTER_JUSTIFY;
  p.setValue(d); l.property("Position").setValue(pos); return l;
}
function key(l, prop, pairs) {
  var pr = l.property(prop);
  pairs.forEach(function (p) { pr.setValueAtTime(p[0], p[1]); }); easeKeys(pr);
}
function fade(l, t0, t1) { key(l, "Opacity", [[t0, 0], [t1, 100]]); }

function character(comp, face, cx) {
  var bi = comp.layers.addNull(); bi.name = "Bi_root"; bi.property("Position").setValue([0, 0]);
  var gy = 0;
  part(comp, "legs", bi, [cx, 900], [85, 100], "legs");
  var armL = part(comp, "arm_L", bi, [cx - 90, 630], [25, 20], "arm");
  var torso = part(comp, "torso", bi, [cx, 700], [85, 110], "torso");
  var armR = part(comp, "arm_R", bi, [cx + 90, 630], [25, 20], "arm");
  var head = part(comp, "head", bi, [cx, 500], [110, 110], "head");
  var f = part(comp, "face_" + face, head, [cx, 500], [110, 110], "face_" + face);
  return { root: bi, armL: armL, armR: armR, head: head, face: f };
}
function bg(comp, color) {
  var s = comp.layers.addSolid(color, "bg", 1920, 1080, 1); s.moveToEnd(); return s;
}
function appear(ch, t) {   // 1) enter from left with overshoot
  key(ch.root, "Position", [[t, [-900, 0]], [t + 0.5, [30, 0]], [t + 0.7, [0, 0]]]);
}

// ---------- Scene 1 ----------
var c1 = app.project.items.addComp("Scene1", 1920, 1080, 1, P.s1.dur, 30);
var ch1 = character(c1, "happy", 450);
appear(ch1, 0.3);
// cheer: right arm up at "giau nhat xom"
key(ch1.armR, "Rotation", [[P.s1.cheer, 0], [P.s1.cheer + 0.4, 160], [P.s1.cheer + 1.2, 160], [P.s1.cheer + 1.6, 0]]);
var ph1 = part(c1, "phone", null, [1250, 540], [150, 260], "phone");
key(ph1, "Scale", [[0.8, [0, 0]], [1.1, [110, 110]], [1.3, [100, 100]]]);
var amt1 = text(c1, "+15.000.000đ", [1250, 520], 34, [0.1, 0.6, 0.25]); fade(amt1, P.s1.ting, P.s1.ting + 0.2);
key(amt1, "Scale", [[P.s1.ting, [60, 60]], [P.s1.ting + 0.25, [115, 115]], [P.s1.ting + 0.4, [100, 100]]]);
for (var i = 0; i < 3; i++) {
  var co = part(c1, "coin" + i, null, [1000 + i * 250, 250], [40, 40], "coin");
  key(co, "Scale", [[P.s1.ting + i * 0.15, [0, 0]], [P.s1.ting + i * 0.15 + 0.3, [120, 120]], [P.s1.ting + i * 0.15 + 0.5, [100, 100]]]);
  key(co, "Position", [[P.s1.ting + i * 0.15, [1000 + i * 250, 250]], [P.s1.dur, [1000 + i * 250, 200]]]);
}
var t1 = text(c1, "Ngày nhận lương", [960, 110], 60, [0.15, 0.15, 0.18]); fade(t1, 0.2, 0.8);
var cap1 = text(c1, P.s1.caption, [960, 1050], 40, [0.15, 0.15, 0.18]);
bg(c1, [1, 0.957, 0.863]);

// ---------- Scene 2 ----------
var c2 = app.project.items.addComp("Scene2", 1920, 1080, 1, P.s2.dur, 30);
var ch2 = character(c2, "normal", 450);
// 2) expression change: normal -> worried (face layers cross-fade) and head tilts
var fw = part(c2, "face_worried", ch2.head, [450, 500], [110, 110], "face_worried");
key(ch2.face, "Opacity", [[P.s2.worry, 100], [P.s2.worry + 0.25, 0]]);
// 4) closing beat: face turns happy again + end card
var fh = part(c2, "face_happy", ch2.head, [450, 500], [110, 110], "face_happy");
key(fh, "Opacity", [[P.s2.end, 0], [P.s2.end + 0.25, 100]]);
key(fw, "Opacity", [[P.s2.worry, 0], [P.s2.worry + 0.25, 100], [P.s2.end, 100], [P.s2.end + 0.25, 0]]);
key(ch2.head, "Rotation", [[P.s2.worry, 0], [P.s2.worry + 0.5, -8], [P.s2.end, -8], [P.s2.end + 0.4, 0]]);
var endc = text(c2, P.s2.endCard, [1000, 160], 56, [0.1, 0.45, 0.25]); fade(endc, P.s2.end, P.s2.end + 0.4);
var ph2 = part(c2, "phone", null, [1000, 540], [150, 260], "phone");
var amt2 = text(c2, "87.000đ", [1000, 520], 52, [0.85, 0.15, 0.15]);
key(amt2, "Scale", [[0.2, [0, 0]], [0.5, [110, 110]], [0.7, [100, 100]]]);
var names = ["Tiền nhà", "Ăn uống", "Mua sắm"], hs = [300, 200, 150], cols = [[0.25, 0.45, 0.85], [0.95, 0.6, 0.15], [0.8, 0.3, 0.5]];
for (var j = 0; j < 3; j++) {
  var x = 1380 + j * 180, tj = P.s2.point[j];
  var b = c2.layers.addSolid(cols[j], "bar" + j, 120, hs[j], 1);
  b.property("Anchor Point").setValue([60, hs[j]]); b.property("Position").setValue([x, 800]);
  key(b, "Scale", [[tj - 0.3, [100, 0]], [tj + 0.2, [100, 105]], [tj + 0.4, [100, 100]]]);
  var lb = text(c2, names[j], [x, 860], 34, [0.15, 0.15, 0.18]); fade(lb, tj - 0.3, tj);
}
// 3) pointing at each bar in turn (speed = P.pointSpeed seconds per move)
var ps = P.pointSpeed, ang = [-70, -78, -85], pt = P.s2.point, pk = [];
// each move takes exactly `ps` seconds and ends when the cue word starts; the wobble only fits if the next move is not too close
for (var m = 0; m < 3; m++) {
  pk.push([pt[m] - ps, m == 0 ? 0 : ang[m - 1]]); pk.push([pt[m], ang[m]]);
  var nextStart = m < 2 ? pt[m + 1] - ps : 1e9;
  if (pt[m] + 0.25 < nextStart) pk.push([pt[m] + 0.25, ang[m] - 4]);
}
pk.push([pt[2] + 1.0, ang[2]]); pk.push([pt[2] + 1.6, 0]);
pk = pk.filter(function (v, i) { return i == 0 || v[0] > pk[i - 1][0] + 0.01; });
key(ch2.armR, "Rotation", pk);
var cap2 = text(c2, P.s2.caption, [960, 1050], 38, [0.15, 0.15, 0.18]);
bg(c2, [0.863, 0.902, 0.933]);

app.project.save(new File(P.out));
writeLn("saved " + P.out);
