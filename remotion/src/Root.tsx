import React from "react";
import { Composition } from "remotion";
import { ReelProps, StickReel } from "./StickReel";

// Sample timing for Remotion Studio (`npm run studio`). Real renders pass public/props.json instead.
const DEMO: ReelProps = {
  audio: null,
  lead: 0.3,
  handle: "",
  duration: 21,
  segments: [
    { kind: "hook", text: "रोहन रोज़ कहता था, मेरे पास टाइम नहीं है।", title: "5 घंटे कहाँ गए?", start: 0, end: 4 },
    { kind: "scene", text: "सुबह उठते ही उसका हाथ सीधा phone पर जाता।", caption: "बस दो मिनट...", action: "scroll_phone", prop: "clock", mood: "calm", start: 4, end: 8 },
    { kind: "scene", text: "एक दिन वो गिरा, पर फिर उठ खड़ा हुआ।", caption: "गिरो, फिर उठो", action: "fall_getup", prop: "none", mood: "tense", start: 8, end: 13 },
    { kind: "lesson", text: "टाइम कम नहीं होता, हम उसे खो देते हैं।", start: 13, end: 17 },
    { kind: "ask", text: "आपका screen time कितना है?", start: 17, end: 21 },
  ],
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="StickReel"
    component={StickReel}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={Math.ceil(DEMO.duration * 30)}
    defaultProps={DEMO}
    calculateMetadata={({ props }) => ({ durationInFrames: Math.ceil(props.duration * 30) })}
  />
);
