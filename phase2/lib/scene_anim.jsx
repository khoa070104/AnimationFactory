// Animated multi-scene build from resolved storyboard data (P.scenes). Needs bi_rig.jsx + bi_motion.jsx.
// No per-scene code: actions run at cue times, items pop in at their cues, subtitles follow the spoken segments.
var FR = 1 / P.fps;
function colorOf(name) { return P.colors[name] || P.text.dark; }
function popIn(layer, t0, isProp) {
  var t = Math.max(t0, 2 * FR), op = layer.property("Opacity");
  op.setValueAtTime(0, 0); op.setValueAtTime(t - FR, 0); op.setValueAtTime(t + 0.12, 100);
  if (isProp) {
    var sc = layer.property("Scale"), b = sc.value;
    sc.setValueAtTime(0, [b[0] * 0.6, b[1] * 0.6]); sc.setValueAtTime(t - FR, [b[0] * 0.6, b[1] * 0.6]);
    sc.setValueAtTime(t + 0.18, [b[0] * 1.06, b[1] * 1.06]); sc.setValueAtTime(t + 0.3, b);
  }
}
function showWindow(layer, t0, t1) {
  var op = layer.property("Opacity");
  op.setValueAtTime(0, 0); op.setValueAtTime(Math.max(t0 - FR, FR), 0); op.setValueAtTime(Math.max(t0, 2 * FR), 100);
  op.setValueAtTime(t1 - FR, 100); op.setValueAtTime(t1, 0);
}
function rigOf(id) { return (id && P.rigs && P.rigs[id]) ? P.rigs[id] : BI_RIG; }
// Actions never overlap within one character: one that would start before the previous one has finished starts right after it (overlapping
// keyframes make joints snap). point_seq keeps its absolute aim times, so it is never shifted (it only counts as busy until it ends).
function charTimeline(comp, bi, actions, faceCues, rest, base, face, dur, label) {
  var keys = [], firstT = 1e9, i, enterFrom = null;
  var order = actions.slice().sort(function (x, y) { return x.T - y.T; }), busyUntil = 0;
  var side = (base[0] < P.w / 2) ? -1 : 1;                  // a character walks in from the screen edge nearest to where it ends up (never across the stage)
  order.forEach(function (a) { if (a.name == "enter") { a.params = a.params || {}; if (a.params.fromX == null) a.params.fromX = side * 900; } });
  order.forEach(function (a) {
    var T0 = Math.max(a.T, busyUntil);
    writeLn("CUE " + label + " " + a.name + " " + a.T.toFixed(3) + " " + T0.toFixed(3));
    var r = ACTIONS[a.name](T0, a.params || {});
    var nxt = null, oi = order.indexOf(a) + 1;
    if (oi < order.length) nxt = order[oi].T;
    if (nxt !== null && a.name == "enter" && T0 + r.dur > nxt) {                // an entrance cut short so the next cue is not overlapped by the walk (never below 0.5 s of walking)
      var ew = Math.max(0.5, nxt - T0 - 0.25), pe = {}, ke;
      for (ke in (a.params || {})) pe[ke] = a.params[ke];
      pe.walk = Math.min(ew, 1.2);
      pe.fromX = (a.params.fromX != null ? a.params.fromX : side * 900) * pe.walk / 1.2;                    // same walking speed, shorter distance
      writeLn("WALKCLAMP " + label + " enter 1.20 -> " + pe.walk.toFixed(2));
      r = ACTIONS.enter(T0, pe);
      if (enterFrom === null && order[0] === a) enterFrom = pe.fromX;
    }
    if (a.name == "enter" && enterFrom === null && order[0] === a) enterFrom = a.params.fromX;
    if (nxt !== null && a.params && a.params.hold > 0.2 && T0 + r.dur > nxt) {   // a hold that would delay the next cue is shortened to fit (the cue timing is the criterion, the hold is only a maximum)
      var over = T0 + r.dur - nxt, ph = {}, kk;
      for (kk in a.params) ph[kk] = a.params[kk];
      ph.hold = Math.max(0.2, a.params.hold - over);
      writeLn("HOLDCLAMP " + label + " " + a.name + " " + a.params.hold.toFixed(2) + " -> " + ph.hold.toFixed(2));
      r = ACTIONS[a.name](T0, ph);
    }
    busyUntil = Math.max(busyUntil, T0 + r.dur);
    var ks = r.keys;
    if (a.stay) {                            // keep the final pose until the end of the scene instead of returning to idle
      var last = ks[ks.length - 2];
      ks = ks.slice(0, ks.length - 1);
      ks.push({ t: dur - 0.05, pose: last.pose });
    }
    for (i = 0; i < ks.length; i++) { keys.push(ks[i]); if (ks[i].t < firstT) firstT = ks[i].t; }
  });
  if (firstT > 0.05) {
    // before its first action the character stands where the story puts it, unless that action is an entrance: then it waits OFF-screen at the entrance point
    // (otherwise it would be visible at its final spot, slide out, and walk in again)
    var e0 = (order.length && order[0].name == "enter") ? order[0] : null;
    if (e0) keys.push({ t: 0, pose: "idle", root: [enterFrom != null ? enterFrom : e0.params.fromX, 0] });
    else keys.push({ t: 0, pose: "idle", root: [0, 0] });
  }
  if (rest) keys.push({ t: 0.7, pose: rest });
  (faceCues || []).forEach(function (f) { keys.push({ t: f.t, face: f.face }); });
  animateBi(comp, bi, keys, base, face);
}
var report = [];
for (var si = 0; si < P.scenes.length; si++) {
  var sc = P.scenes[si];
  var comp = app.project.items.addComp(sc.id, P.w, P.h, 1, sc.dur, P.fps);
  var b = sc.bi;
  var bi = buildBi(comp, { x: b.x, y: b.y, scale: b.scale, face: b.face, frontArms: b.frontArms, allFaces: true, pose: {}, rig: rigOf(b.rig), flip: b.flip });
  var castBi = [];
  (sc.cast || []).forEach(function (c, ci) {                  // supporting characters: own rig, own actions, layer names prefixed "c<n>_"
    castBi.push({ c: c, bi: buildBi(comp, { x: c.x, y: c.y, scale: c.scale, face: c.face, allFaces: true, pose: {}, rig: rigOf(c.rig), flip: c.flip, prefix: "c" + (ci + 1) + "_" }) });
  });
  (sc.holds || []).forEach(function (h) {
    var tb = bi, wm = /^cast(\d+)$/.exec(h.who || "");
    if (wm && castBi[+wm[1] - 1]) tb = castBi[+wm[1] - 1].bi;                  // the held prop follows the hand of the character named in `who` (default: the main one)
    var l = holdProp(comp, tb, h.side, h.prop, h.scale, h.pivot, h.rot || 0, h.off);
    popIn(l, 0.4, false);
  });
  // ---- items ----
  sc.prims.forEach(function (p) {
    var l;
    if (p.kind == "prop") l = prop(comp, p.img + "_" + p.x + "_" + p.y, p.img, [p.x, p.y], p.scale, p.rot || 0);
    else l = text(comp, p.text, [p.x, p.y], p.size, colorOf(p.color), p.rot || 0, p.align);
    if (p.appear != null) popIn(l, p.appear, p.kind == "prop");
  });
  // ---- character timelines ----
  charTimeline(comp, bi, sc.actions, sc.face_cues, sc.rest, [b.x, b.y], b.face, sc.dur, sc.id + "/main");
  castBi.forEach(function (cb) { charTimeline(comp, cb.bi, cb.c.actions || [], cb.c.face_cues || [], cb.c.rest, [cb.c.x, cb.c.y], cb.c.face, sc.dur, sc.id + "/cast" + (castBi.indexOf(cb) + 1)); });
  // ---- subtitles ----
  (sc.subs || []).forEach(function (s) {
    var bar = prop(comp, "subbar", s.bar, [960, sc.subtitleY], 1.0, 0);
    var tx = text(comp, s.text, [960, sc.subtitleY + 14], 44, P.text.dark);
    bar.name = "sub_bar"; tx.name = "sub_text";   // +14: point text is positioned on its baseline
    showWindow(bar, s.t0, s.t1); showWindow(tx, s.t0, s.t1);
  });
  if (sc.camera) {                           // camera move: a null parents every scene layer except subtitles (and the background, added later)
    var cam = comp.layers.addNull(); cam.name = "camera";
    cam.property("Anchor Point").setValue([P.w / 2, P.h / 2]); cam.property("Position").setValue([P.w / 2, P.h / 2]);
    for (var q = 1; q <= comp.numLayers; q++) {
      var ly = comp.layer(q);
      if (ly.name != "camera" && ly.name != "sub_bar" && ly.name != "sub_text" && !ly.parent) ly.parent = cam;
    }
    var cz = sc.camera.zoom, cp = sc.camera.pan;
    cam.property("Scale").setValueAtTime(0, [cz[0] * 100, cz[0] * 100]); cam.property("Scale").setValueAtTime(sc.dur, [cz[1] * 100, cz[1] * 100]);
    cam.property("Position").setValueAtTime(0, [P.w / 2 + cp[0][0], P.h / 2 + cp[0][1]]); cam.property("Position").setValueAtTime(sc.dur, [P.w / 2 + cp[1][0], P.h / 2 + cp[1][1]]);
    easeProp(cam.property("Scale")); easeProp(cam.property("Position"));
  }
  if (sc.fade_out) {                         // end of the video: dissolve to the background colour over the last `fade_out` seconds
    var fo = comp.layers.addSolid(sc.bgRGB, "fadeout", P.w, P.h, 1);
    fo.moveToBeginning();
    var fop = fo.property("Opacity");
    fop.setValueAtTime(0, 0); fop.setValueAtTime(sc.dur - sc.fade_out, 0); fop.setValueAtTime(sc.dur - FR, 100);
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
