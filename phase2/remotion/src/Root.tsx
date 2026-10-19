import React from "react";
import { Composition, staticFile } from "remotion";
import { Clip } from "./Clip";

// The clip is DATA (public/data/clip.json, written by phase2/tools/export_remotion.py): swapping scene data/assets needs no code change.
export const Root: React.FC = () => (
  <Composition
    id="Clip"
    component={Clip}
    width={1920}
    height={1080}
    fps={30}
    durationInFrames={900}
    defaultProps={{ data: null as any }}
    calculateMetadata={async () => {
      const data = await (await fetch(staticFile("data/clip.json"))).json();
      return { durationInFrames: Math.ceil(data.total * data.fps), fps: data.fps, width: data.w, height: data.h, props: { data } };
    }}
  />
);
