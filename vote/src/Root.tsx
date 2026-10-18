import React from "react";
import { Composition, staticFile } from "remotion";
import { Episode } from "./Episode";
import { Ep, FPS, H, W } from "./theme";

const empty = { beats: [], words: [], duration: 2 } as unknown as Ep;

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Episode"
    component={Episode}
    width={W}
    height={H}
    fps={FPS}
    durationInFrames={60}
    defaultProps={{ ep: empty }}
    calculateMetadata={async () => {
      const ep: Ep = await fetch(staticFile("episode.json")).then((r) => r.json());
      return { props: { ep }, durationInFrames: Math.ceil(ep.duration * FPS) };
    }}
  />
);
