import React, { useMemo } from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { Character } from "./Character";
import { motionLib } from "./motion";
import { buildKeys, makeSampler } from "./timeline";
import { cameraAt, flipAt } from "./camera";

const css = (c: number[]) => `rgb(${Math.round(c[0] * 255)},${Math.round(c[1] * 255)},${Math.round(c[2] * 255)})`;
const FONT = `@font-face{font-family:AFArial;src:url(${staticFile("fonts/arialbd.ttf")});font-weight:700}`;

// Stand-in setting drawn in code (flat shapes): a home corner. The Antigravity background replaces it when that asset exists.
const Setting: React.FC<{ kind: string }> = ({ kind }) => (
  <svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0 }}>
    <rect x={0} y={930} width={1920} height={150} fill="#ead9b8" />
    <rect x={0} y={925} width={1920} height={8} fill="#c9b48c" />
    <g stroke="#2b2f3a" strokeWidth={6} strokeLinejoin="round">
      <rect x={420} y={130} width={240} height={210} rx={14} fill="#cfe6f5" />
      <path d="M540 130 V340 M420 235 H660" fill="none" />
      <rect x={1560} y={190} width={260} height={16} rx={6} fill="#b98a52" />
      <rect x={1590} y={120} width={70} height={70} rx={10} fill="#e8a45a" />
      <rect x={1690} y={140} width={60} height={50} rx={10} fill="#8fc7a5" />
    </g>
  </svg>
);

const Scene: React.FC<{ sc: any; D: any; M: any }> = ({ sc, D, M }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const PS = D.pngScale;
  const sizes = D.sizes;
  const chars = useMemo(
    () =>
      sc.chars.map((ch: any) => {
        const rig = D.rigs[ch.rig] || M.BI_RIG;
        const { keys } = buildKeys(M, ch, sc.dur, D.w);
        return { ch, rig, sample: makeSampler(M, rig, keys, [ch.x, ch.y], ch.face, D.fps) };
      }),
    [sc.id],
  );
  const col = (c: string) => (D.colors[c] ? css(D.colors[c]) : D.accent[c] || "#2b2f3a");
  const prim = (p: any, i: number) => {
    const a = p.appear == null ? 0 : Math.max(p.appear, 2 / fps);
    const op = p.appear == null ? 1 : interpolate(t, [a - 1 / fps, a + 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    if (op <= 0) return null;
    if (p.kind === "prop") {
      const sz = sizes[p.img] || [200, 200];
      const pop = p.appear == null ? 1 : interpolate(t, [a - 1 / fps, a + 0.18, a + 0.3], [0.6, 1.06, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
      return (
        <img key={i} src={staticFile(`assets/png/${p.img}.png`)} style={{ position: "absolute", left: 0, top: 0, transformOrigin: "0 0", opacity: op,
          transform: `translate(${p.x}px,${p.y}px) rotate(${p.rot || 0}deg) scale(${(p.scale * pop) / PS}) translate(${-sz[0] / 2}px,${-sz[1] / 2}px)` }} />
      );
    }
    const left = p.align === "left";
    return (
      <div key={i} style={{ position: "absolute", left: p.x, top: p.y - 0.82 * p.size, transform: `${left ? "" : "translateX(-50%)"} rotate(${p.rot || 0}deg)`, whiteSpace: "nowrap",
        fontFamily: "AFArial", fontWeight: 700, fontSize: p.size, lineHeight: 1, color: col(p.color), opacity: op }}>
        {p.text}
      </div>
    );
  };
  const [cx, cy, z] = cameraAt(sc.camera, t, D.w, D.h);
  return (
    <AbsoluteFill style={{ background: css(sc.bgRGB) }}>
      {/* WORLD: background, scene props, content items, characters: moved and scaled by the camera */}
      <AbsoluteFill style={{ transformOrigin: "0 0", transform: `translate(${D.w / 2 - cx * z}px, ${D.h / 2 - cy * z}px) scale(${z})` }}>
        {sc.bgImage ? <img src={staticFile(`assets/png/${sc.bgImage}.png`)} style={{ position: "absolute", left: 0, top: 0, width: D.w }} /> : <Setting kind={sc.id} />}
        {sc.prims.map((p: any, i: number) => (p.space === "screen" ? null : prim(p, i)))}
        {chars.map(({ ch, rig, sample }: any, i: number) => (
          <Character key={i} rig={rig} rigId={ch.rig} s={sample(t)} scale={ch.scale} flip={flipAt(ch, t)} PS={PS} sizes={sizes}
            holds={sc.holds.filter((h: any) => (h.who || "main") === ch.who)} />
        ))}
      </AbsoluteFill>
      {/* SCREEN: items marked space:"screen" and the subtitles never move with the camera */}
      {sc.prims.map((p: any, i: number) => (p.space === "screen" ? prim(p, i) : null))}
      {sc.subs.map((s: any, i: number) =>
        t >= s.t0 && t < s.t1 ? (
          <div key={i}>
            <div style={{ position: "absolute", left: 960 - s.w / 2, top: sc.subtitleY - 42, width: s.w, height: 84, borderRadius: 42, background: "rgba(255,255,255,0.9)" }} />
            <div style={{ position: "absolute", left: 0, width: 1920, textAlign: "center", top: sc.subtitleY + 14 - 0.82 * 44, fontFamily: "AFArial", fontWeight: 700, fontSize: 44, lineHeight: 1, color: "#2b2f3a" }}>{s.text}</div>
          </div>
        ) : null,
      )}
    </AbsoluteFill>
  );
};

export const Clip: React.FC<{ data: any }> = ({ data }) => {
  const { fps } = useVideoConfig();
  const M = useMemo(() => (data ? motionLib(data.motionSrc, data.pngScale) : null), [data]);
  if (!data) return null;
  return (
    <AbsoluteFill style={{ background: "#fff" }}>
      <style>{FONT}</style>
      {data.scenes.map((sc: any) => (
        <Sequence key={sc.id} from={Math.round(sc.start * fps)} durationInFrames={Math.round(sc.dur * fps)}>
          <Scene sc={sc} D={data} M={M} />
          <Audio src={staticFile(sc.audio)} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
