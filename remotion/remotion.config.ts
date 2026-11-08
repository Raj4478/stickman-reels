import { Config } from "@remotion/cli/config";

// three.js needs WebGL. GitHub's runners have no GPU: "swangle" renders on the CPU (Remotion's docs say GitHub
// Actions fails with "angle"). On a desktop with a GPU, "angle" is much faster. GitHub Actions sets CI=true.
Config.setChromiumOpenGlRenderer(process.env.CI ? "swangle" : "angle");
