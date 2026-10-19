var out = [];
for (var i = 1; i <= app.project.numItems; i++) {
  var it = app.project.item(i);
  if (it instanceof CompItem) {
    var names = {}, dup = 0;
    for (var k = 1; k <= it.numLayers; k++) { var n = it.layer(k).name; if (names[n]) dup++; names[n] = 1; }
    out.push(it.name + ":" + it.numLayers + ":" + dup);
  }
}
writeLn("LAYERS " + out.join(","));
