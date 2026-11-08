"""Depth maps for the storybook paintings, so the Reel can float a 3D camera through each one ("living paintings").

Depth Anything V2 small (Apache-2.0, the quantized ONNX build from onnx-community, 27 MB) runs on the CPU with
onnxruntime (already installed with faster-whisper) in about a second a picture. The map is a greyscale PNG the same
size as the picture: white is near, black is far. The model is downloaded once and kept in the Actions cache."""
import os
import urllib.request
from pathlib import Path

MODEL_URL = 'https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model_quantized.onnx'
SIDE = 518  # the model's input size (a multiple of 14)
_session = None


def model_path():
    return Path(os.getenv('DEPTH_MODEL', Path.home() / '.cache' / 'seekh-depth' / 'depth-anything-v2-small-q.onnx'))


def session():
    global _session
    if _session is None:
        import onnxruntime as ort
        path = model_path()
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix('.part')
            urllib.request.urlretrieve(MODEL_URL, tmp)
            tmp.replace(path)
        _session = ort.InferenceSession(str(path), providers=['CPUExecutionProvider'])
    return _session


def depth_map(image_path, out_path):
    """Write the depth PNG of one picture (white near, black far); returns out_path."""
    import numpy as np
    from PIL import Image
    img = Image.open(image_path).convert('RGB')
    x = np.asarray(img.resize((SIDE, SIDE), Image.BICUBIC), np.float32) / 255
    x = ((x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]).transpose(2, 0, 1)[None].astype(np.float32)
    s = session()
    d = s.run(None, {s.get_inputs()[0].name: x})[0][0]
    lo, hi = np.percentile(d, 2), np.percentile(d, 98)  # ignore a few extreme pixels
    d = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
    Image.fromarray((d * 255).astype(np.uint8)).resize(img.size, Image.BILINEAR).save(out_path)
    return out_path


def add_depth(folder, names):
    """Depth maps for every painted picture name (relative to folder); returns {name: depth name}. A picture whose map
    fails just stays flat (the Reel moves it like a photo)."""
    maps = {}
    for name in names:
        if not name or name in maps:
            continue
        target = name.rsplit('.', 1)[0] + '-depth.png'
        try:
            depth_map(Path(folder) / name, Path(folder) / target)
            maps[name] = target
        except Exception as exc:  # noqa: BLE001 - depth is a bonus; the picture still moves without it
            print(f'::warning::No depth map for {name}: {exc}')
    return maps
