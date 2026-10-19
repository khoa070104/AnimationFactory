// Three style frames. Needs lib/bi_rig.jsx first. Params: P.bars = [{label,value,h,color}], P.colors, P.ink.
var DARK = P.text.dark, GOOD = P.text.good, BAD = P.text.bad;

// ---- Frame 01: Bi happy, salary notification ----
var c1 = app.project.items.addComp("Frame01", P.w, P.h, 1, 1, P.fps);
var bi1 = buildBi(c1, { x: 520, y: 975, scale: 1.12, face: "happy", pose: { rs: -152, re: -18, ls: 16, le: 6, head: -5, legL: 2, legR: -2 } });
prop(c1, "phone", "phone", [1380, 650], 1.25);
prop(c1, "card", "card", [1380, 400], 1.0);
text(c1, "+15.000.000đ", [1448, 380], 54, GOOD);
text(c1, "Lương tháng 10", [1452, 438], 40, DARK);
prop(c1, "coin1", "coin", [1090, 250], 1.2, -15); prop(c1, "coin2", "coin", [1720, 230], 1.0, 20); prop(c1, "coin3", "coin", [1700, 860], 1.3, 8);
prop(c1, "spark1", "sparkle", [930, 540], 1.0); prop(c1, "spark2", "sparkle", [300, 330], 0.8);
text(c1, "Ting!", [905, 330], 92, P.colors.bi, -8);
background(c1, P.bg);

// ---- Frame 02: Bi points at spending chart ----
var c2 = app.project.items.addComp("Frame02", P.w, P.h, 1, 1, P.fps);
var bi2 = buildBi(c2, { x: 520, y: 975, scale: 1.2, face: "neutral", pose: { rs: -82, re: -4, ls: 10, le: 4, head: 4 } });
prop(c2, "board", "board", [1330, 540], 1.05);
text(c2, "Chi tiêu tháng 10", [1330, 292], 54, DARK);
var base = 780;
for (var i = 0; i < P.bars.length; i++) {
  var b = P.bars[i], cx = 1000 + i * 200;
  prop(c2, "bar_" + i, "bar_" + i, [cx, base - b.h / 2], 1.0);
  text(c2, b.value, [cx, base - b.h - 36], 46, DARK);
  text(c2, b.label, [cx, base + 44], 40, DARK);
}
prop(c2, "spark", "sparkle", [1085, base - P.bars[0].h - 80], 0.9);
background(c2, P.bg);

// ---- Frame 03: Bi worried, unexpected bill (CLOSE-UP, scale 2.4, torso cropped by the frame) ----
// right hand rests on the cheek (IK target in root space), clear of the eyebrows
var c3 = app.project.items.addComp("Frame03", P.w, P.h, 1, 1, P.fps);
var bi3 = buildBi(c3, { x: 620, y: 1615, scale: 2.4, face: "worried", frontArms: "R",
  pose: { rHand: [90, -425], ls: 14, le: -6, head: -5 } });
prop(c3, "bill", "bill", [1460, 570], 1.55, 5);
text(c3, "HÓA ĐƠN", [1470, 322], 58, [1, 1, 1], 5);
text(c3, "Sửa xe", [1462, 545], 84, DARK, 5);
text(c3, "3.500.000đ", [1468, 680], 72, BAD, 5);
prop(c3, "exclaim", "exclaim", [1060, 250], 1.5, -8);
prop(c3, "sweat1", "sweat", [330, 330], 1.5, -10); prop(c3, "sweat2", "sweat", [305, 470], 1.1, -10);
background(c3, P.bgAlt);

app.project.save(new File(P.out));
writeLn("saved " + P.out);
