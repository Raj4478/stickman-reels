# Seekh Sketch brand

**Seekh Sketch** (सीख स्केच), *छोटी कहानियाँ, बड़ी सीख*: short Hindi life lessons acted out by a stick figure.

**The mark:** a speech bubble (a story being told) with a stick figure raising its arm to a spark (the moment a lesson clicks). It uses two colours, so it stays sharp from a 32 px icon to a banner.

| File | Use |
| --- | --- |
| `avatar-800.png` | YouTube profile picture (800×800). Everything sits inside the circle YouTube shows. |
| `avatar-1080.png` | Instagram profile picture, Telegram bot photo |
| `logo-light.png` | Mark + name on cream (2400×800): YouTube banner art, thumbnails, documents |
| `logo-dark.png` | Mark + name on ink, for dark backgrounds |
| `logo-transparent.png` | Mark + name, transparent background |
| `mark-transparent.png` | The mark alone, transparent (1000×1000): video watermark, favicon, stickers |

| Colour | Hex |
| --- | --- |
| Ink | `#15151c` |
| Saffron | `#ffb000` |
| Cream | `#fffaf0` |

**Fonts:** Poppins ExtraBold for the name, Noto Sans Devanagari Bold for the Hindi. Both are already in `remotion/public/fonts`.

**Regenerating:** the logo is code (`remotion/src/Logo.tsx`), so a change there renders new files:

```bash
cd remotion
npx remotion still src/index.ts LogoAvatar ../brand/avatar-1080.png
npx remotion still src/index.ts LogoLockup ../brand/logo-light.png
npx remotion still src/index.ts LogoLockup ../brand/logo-dark.png --props='{"dark":true}'
npx remotion still src/index.ts LogoLockup ../brand/logo-transparent.png --props='{"transparent":true}'
npx remotion still src/index.ts LogoMark ../brand/mark-transparent.png
```
