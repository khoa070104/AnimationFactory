// The motion definitions are NOT re-implemented: the same lib/bi_rig.jsx + lib/bi_motion.jsx the EffectCraft builder uses (POSES, ACTIONS, IK) are
// evaluated here from the source text carried in clip.json, so both renderers move a character identically.
let cache: any = null;
export function motionLib(src: string, pngScale: number) {
  if (cache && cache.src === src) return cache.lib;
  const lib = new Function(
    "P",
    src + "\nreturn { POSES: POSES, IDLE: IDLE, ACTIONS: ACTIONS, resolvePose: resolvePose, BI_RIG: BI_RIG, CH_ORDER: CH_ORDER, FACE_KINDS: FACE_KINDS };",
  )({ pngScale });
  cache = { src, lib };
  return lib;
}
