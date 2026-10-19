// Sample the animated joint values of comp P.comp frame by frame (run on a saved project).
var cmp = null;
for (var i = 1; i <= app.project.numItems; i++) { var it = app.project.item(i); if (it instanceof CompItem && it.name == P.comp) cmp = it; }
var N = Math.floor(cmp.duration * P.fps);
var J = ["shoulder_L", "elbow_L", "shoulder_R", "elbow_R", "neck", "waist", "hip_L", "hip_R"];
var held = null;
for (var k = 1; k <= cmp.numLayers; k++) if (cmp.layer(k).name.indexOf("held_") == 0) held = cmp.layer(k);
writeLn("HELDPARENT " + (held && held.parent ? held.parent.name : "none"));
for (var f = 0; f < N; f++) {
  var t = f / P.fps, row = [f, t.toFixed(3)];
  var PX = P.prefix || "";
  var rp = cmp.layer(PX + "Bi_root").property("Position").valueAtTime(t, false);
  row.push(rp[0].toFixed(2)); row.push(rp[1].toFixed(2));
  for (var j = 0; j < J.length; j++) row.push(cmp.layer(PX + J[j]).property("Rotation").valueAtTime(t, false).toFixed(3));
  row.push(held ? held.property("Opacity").valueAtTime(t, false).toFixed(0) : "0");
  writeLn("S " + row.join(" "));
}
