import React from "react";
import { Composition } from "remotion";
import { Card, CardProps } from "./Card";
import { LogoAvatar, LogoBanner, LogoLockup, LogoMark } from "./Logo";
import { ReelProps, StickReel } from "./StickReel";

// Sample timing for Remotion Studio (`npm run studio`). Real renders pass public/reels/<n>/props.json instead.
const DEMO: ReelProps = {
  audio: null,
  music: null,
  lead: 0.3,
  handle: "",
  duration: 22,
  segments: [
    { kind: "hook", text: "रोहन रोज़ कहता था, मेरे पास टाइम नहीं है।", title: "5 घंटे कहाँ गए?", name: "रोहन", action: "shock", start: 0, end: 4 },
    { kind: "scene", text: "सुबह उठते ही उसका हाथ सीधा phone पर जाता।", caption: "बस दो मिनट...", action: "scroll_phone", prop: "clock", mood: "calm", with: "none", place: "home", shot: "medium", transition: "cut", start: 4, end: 8 },
    { kind: "scene", text: "पापा ने पूछा, तुम्हारे सपनों का क्या हुआ?", caption: "सपनों का क्या हुआ?", action: "argue", prop: "none", mood: "tense", with: "father", place: "home", shot: "two_shot", transition: "whip", start: 8, end: 13 },
    { kind: "lesson", text: "टाइम कम नहीं होता, हम उसे खो देते हैं।", start: 13, end: 17 },
    { kind: "ask", text: "आपका screen time कितना है?", start: 17, end: 22 },
  ],
};

const CARD: CardProps = { title: "इस हफ्ते की 5 सीख", subtitle: "छोटी कहानियाँ, बड़ी सीख" };

export const RemotionRoot: React.FC = () => (
  <>
  <Composition id="LogoAvatar" component={LogoAvatar} width={1080} height={1080} fps={30} durationInFrames={1} />
  <Composition id="LogoLockup" component={LogoLockup} width={2400} height={800} fps={30} durationInFrames={1} defaultProps={{ dark: false, transparent: false }} />
  <Composition id="LogoMark" component={LogoMark} width={1000} height={1000} fps={30} durationInFrames={1} />
  <Composition id="LogoBanner" component={LogoBanner} width={2560} height={1440} fps={30} durationInFrames={1} defaultProps={{ guides: false }} />
  <Composition
    id="Card"
    component={Card}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={105}
    defaultProps={CARD}
  />
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
  </>
);
