import React from "react";
import { Composition } from "remotion";
import { Card, CardProps } from "./Card";
import { LogoAvatar, LogoBanner, LogoLockup, LogoMark } from "./Logo";
import { ReelProps, StickReel } from "./StickReel";
import { ComicReel } from "./comic/ComicReel";

// The workflow renders "StickReel" for every Reel; a comic script's props (style "comic") get the comic look
const Reel: React.FC<ReelProps> = (p) => (p.style === "comic" ? <ComicReel {...p} /> : <StickReel {...p} />);

// Sample timing for Remotion Studio (`npm run studio`). Real renders pass public/reels/<n>/props.json instead.
const DEMO: ReelProps = {
  audio: null,
  music: null,
  lead: 0.3,
  handle: "",
  duration: 26,
  hero: "boy",
  segments: [
    { kind: "hook", text: "तीन साल मैंने उसके एक मैसेज का इंतज़ार किया।", title: "3 साल, 1 मैसेज", name: "रोहन", action: "shy", start: 0, end: 4 },
    { kind: "scene", text: "कॉलेज के पहले दिन मैंने उसे देखा, और बस देखता रह गया।", caption: "पहली नज़र", action: "shy", prop: "none", mood: "happy", with: "none", place: "classroom", shot: "close", transition: "cut", start: 4, end: 8 },
    { kind: "scene", text: "पापा बोले, पहले पढ़ाई, फिर ये सब।", caption: "पहले पढ़ाई!", action: "argue", prop: "none", mood: "tense", with: "father", place: "home", shot: "two_shot", transition: "whip", start: 8, end: 12 },
    { kind: "scene", text: "आखिरी दिन मैंने हिम्मत की, और गुलाब लेकर उसके सामने बैठ गया।", caption: "आखिरी मौका", action: "propose", prop: "none", mood: "happy", with: "partner", place: "park", shot: "two_shot", transition: "zoom", start: 12, end: 17 },
    { kind: "lesson", text: "जो दिल में है, वक्त रहते कह दो।", start: 17, end: 21 },
    { kind: "ask", text: "आपने कभी किसी से दिल की बात कही?", start: 21, end: 26 },
  ],
};

// A comic Reel for the Studio (`examples/comic.json` is the same script)
const COMIC: ReelProps = {
  audio: null, music: null, lead: 0.3, handle: "", duration: 22, hero: "boy", style: "comic", place: "bedroom", emoji: "sob",
  segments: [
    { kind: "hook", text: "दो साल कंप्यूटर कोर्स किया, आज तक एक दिन काम नहीं आया।", title: "Computer Course", face: "deadpan", gesture: "type", look: "screen", start: 0, end: 4 },
    { kind: "scene", text: "सर बोले थे, पंद्रह हज़ार की नौकरी पक्की।", face: "smug", gesture: "talk", look: "viewer", speaker: "narrator", visual: "person", who: "teacher", start: 4, end: 8 },
    { kind: "scene", text: "गोलू! कुछ काम-धाम करेगा या नहीं?", face: "angry", gesture: "talk", look: "viewer", speaker: "other", with: "mother", visual: "person", who: "mother", start: 8, end: 11.5 },
    { kind: "scene", text: "चार साल से घर पे बैठे हैं।", face: "sad", gesture: "shrug", look: "viewer", speaker: "narrator", visual: "calendar", visual_text: "4 साल", start: 11.5, end: 15 },
    { kind: "lesson", text: "पूरे कोर्स में बस एक चीज़ सीखी, गाना और फिलम चलाना।", face: "smug", gesture: "point_self", look: "viewer", visual: "screen", screen: "music", visual_text: "गाना.mp3", start: 15, end: 19.5 },
    { kind: "ask", text: "तुमने कौन सा कोर्स किया था?", start: 19.5, end: 22 },
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
    id="ComicReel"
    component={ComicReel}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={Math.ceil(COMIC.duration * 30)}
    defaultProps={COMIC}
    calculateMetadata={({ props }) => ({ durationInFrames: Math.ceil(props.duration * 30) })}
  />
  <Composition
    id="StickReel"
    component={Reel}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={Math.ceil(DEMO.duration * 30)}
    defaultProps={DEMO}
    calculateMetadata={({ props }) => ({ durationInFrames: Math.ceil(props.duration * 30) })}
  />
  </>
);
