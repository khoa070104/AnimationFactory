// Static scene previews from expanded storyboard data (P.scenes). Needs bi_rig.jsx + bi_motion.jsx (POSES, resolvePose).
// No per-scene code: every scene is data -> comp. Render one frame per comp for the storyboard thumbnails.
function colorOf(name) { return P.colors[name] || P.text.dark; }
for (var si = 0; si < P.scenes.length; si++) {
  var sc = P.scenes[si];
  var comp = app.project.items.addComp(sc.id, P.w, P.h, 1, 1, P.fps);
  var b = sc.bi;
  var prig = (b.rig && P.rigs && P.rigs[b.rig]) ? P.rigs[b.rig] : BI_RIG;
  var bi = buildBi(comp, { x: b.x, y: b.y, scale: b.scale, face: b.face, frontArms: b.frontArms, pose: resolvePose(b.pose, prig), rig: prig, flip: b.flip });
  var castB = [];
  (sc.cast || []).forEach(function (c, ci) {
    var crig = (c.rig && P.rigs && P.rigs[c.rig]) ? P.rigs[c.rig] : BI_RIG;
    castB.push(buildBi(comp, { x: c.x, y: c.y, scale: c.scale, face: c.face, pose: resolvePose(c.pose, crig), rig: crig, flip: c.flip, prefix: "c" + (ci + 1) + "_" }));
  });
  (sc.holds || []).forEach(function (h) {
    var tb = bi, wm = /^cast(\d+)$/.exec(h.who || "");
    if (wm && castB[+wm[1] - 1]) tb = castB[+wm[1] - 1];
    holdProp(comp, tb, h.side, h.prop, h.scale, h.pivot, h.rot || 0, h.off);
  });
  sc.prims.forEach(function (p) {
    if (p.kind == "prop") prop(comp, p.img + "_" + p.x, p.img, [p.x, p.y], p.scale, p.rot || 0);
    else text(comp, p.text, [p.x, p.y], p.size, colorOf(p.color), p.rot || 0, p.align);
  });
  if (sc.subtitle) {
    var sy = sc.subtitleY || 1030;
    prop(comp, "subbar", sc.subbar, [960, sy], 1.0, 0);
    text(comp, sc.subtitle, [960, sy + 14], 44, P.text.dark);       // +14: point text is positioned on its baseline
  }
  background(comp, sc.bgRGB);
  if (sc.bgImage) {                          // AI background: full-canvas image above the base colour, below everything else
    var bgl = comp.layers.add(img(sc.bgImage)); bgl.name = "bg_image";
    bgl.property("Anchor Point").setValue([bgl.source.width / 2, bgl.source.height / 2]);
    bgl.property("Position").setValue([P.w / 2, P.h / 2]);
    var k = 100 * P.w / bgl.source.width; bgl.property("Scale").setValue([k, k]);
    bgl.moveToEnd(); comp.layer("bg").moveToEnd();
  }
}
app.project.save(new File(P.out));
writeLn("saved " + P.out + " scenes=" + P.scenes.length);
