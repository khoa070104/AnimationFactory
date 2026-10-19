import React from "react";
import { staticFile } from "remotion";

// Cut-out character drawn from rig DATA (same hierarchy and layer order as buildBi() in lib/bi_rig.jsx): every part is an <img> whose CSS transform is
// the chain of joint transforms; pivots are in 1x px of the 2x picture.
const T = (x: number, y: number) => `translate(${x}px,${y}px)`;
const R = (d: number) => `rotate(${d}deg)`;

export const Character: React.FC<{ rig: any; rigId: string; s: any; scale: number; flip: boolean; holds: any[]; sizes: Record<string, [number, number]>; PS: number }> = ({
  rig, rigId, s, scale, flip, holds, sizes, PS,
}) => {
  const src = (name: string) => (rigId === "bi" ? staticFile(`assets/png/${name}.png`) : staticFile(`rigs/${rigId}/${name}.png`));
  const part = (key: string, img: string, pivot: number[], tf: string, opacity = 1) => (
    <img key={key} src={src(img)} style={{ position: "absolute", left: 0, top: 0, transformOrigin: "0 0", opacity, transform: `${tf} scale(${1 / PS}) translate(${-pivot[0] * PS}px,${-pivot[1] * PS}px)` }} />
  );
  const j = s.j;
  const root = `${T(s.root[0], s.root[1])} scale(${flip ? -scale : scale},${scale})`;
  const waist = `${root} ${T(0, rig.waistY)} ${R(j.lean)}`;
  const hipL = `${root} ${T(-rig.hip.x, rig.hip.y)} ${R(j.legL)}`;
  const hipR = `${root} ${T(rig.hip.x, rig.hip.y)} ${R(j.legR)}`;
  const shL = `${waist} ${T(-rig.shoulder.x, rig.shoulder.y)} ${R(j.ls)}`;
  const shR = `${waist} ${T(rig.shoulder.x, rig.shoulder.y)} ${R(j.rs)}`;
  const elL = `${shL} ${T(0, rig.L1)} ${R(j.le)}`;
  const elR = `${shR} ${T(0, rig.L1)} ${R(j.re)}`;
  const handL = `${elL} ${T(0, rig.L2)}`;
  const handR = `${elR} ${T(0, rig.L2)}`;
  const neck = `${waist} ${T(0, rig.neck.y)} ${R(j.head)}`;
  const held = holds.map((h, i) => {
    const nm = h.prop.startsWith("ai:") ? `ai_${h.prop.slice(3)}` : h.prop;
    const sz = sizes[nm] || [200, 200];
    const pv = h.pivot || [sz[0] / PS / 2, sz[1] / PS / 2];
    const off = h.off || [0, 0];
    return (
      <img key={`held${i}`} src={staticFile(`assets/png/${nm}.png`)} style={{ position: "absolute", left: 0, top: 0, transformOrigin: "0 0",
        transform: `${h.side === "L" ? handL : handR} ${T(off[0], off[1])} ${R(h.rot || 0)} scale(${h.scale / PS}) translate(${-pv[0] * PS}px,${-pv[1] * PS}px)` }} />
    );
  });
  return (
    <div style={{ position: "absolute", left: 0, top: 0 }}>
      {part("shadow", rig.shadow.img, rig.shadow.pivot, root)}
      {part("legR", rig.leg.img, rig.leg.pivot, hipR)}
      {part("legL", rig.leg.img, rig.leg.pivot, hipL)}
      {part("auL", rig.armUpper.img, rig.armUpper.pivot, shL)}
      {part("auR", rig.armUpper.img, rig.armUpper.pivot, shR)}
      {part("torso", rig.torso.img, rig.torso.pivot, waist)}
      {part("alL", rig.armLower.img, rig.armLower.pivot, elL)}
      {part("alR", rig.armLower.img, rig.armLower.pivot, elR)}
      {held}
      {rig.head ? part("head", rig.head.img, rig.head.pivot, neck) : null}
      {Object.keys(s.faces).map((k) => (s.faces[k] > 0.001 ? part("face_" + k, rig.face.pattern.replace("{k}", k), rig.face.pivot, neck, s.faces[k]) : null))}
    </div>
  );
};
