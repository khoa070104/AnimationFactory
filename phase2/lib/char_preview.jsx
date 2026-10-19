// Character preview: the rig in four poses side by side (idle, point, cheer, cheek) with every expression row below. Needs bi_rig.jsx + bi_motion.jsx.
// P.rig = the rig to show (default Bi). Used by tools/char_preview.py for the UI and for the rig quality check.
var comp = app.project.items.addComp("Preview", P.w, P.h, 1, 1, P.fps);
var rig = P.rig || BI_RIG;
var poses = ["idle", "point", "cheer", "cheek"], i;
for (i = 0; i < poses.length; i++) {
  buildBi(comp, { x: 300 + i * 440, y: 700, scale: 1.0, face: ["happy", "neutral", "surprised", "worried"][i], pose: resolvePose(poses[i], rig), rig: rig, prefix: "p" + i + "_" });
}
// expressions row (the head layers only)
for (i = 0; i < rig.kinds.length; i++) {
  var f = prop(comp, "exp_" + rig.kinds[i], faceImg(rig, rig.kinds[i]), [200 + i * 330, 930], 0.55, 0);
}
background(comp, P.bg);
app.project.save(new File(P.out));
writeLn("saved " + P.out);
