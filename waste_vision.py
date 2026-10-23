"""
waste_vision.py - finds waste items in a photo and says which waste stream each one belongs to.

The model is YOLOv8 (from HrutikAdsare/waste-detection-yolov8 on Hugging Face, MIT licence),
exported to ONNX so the server does not need PyTorch. The weights are stored in half precision
(about 52 MB, under GitHub's 100 MB file limit), and Cast nodes inside the model turn them into
full precision while it runs. Tested: scores match the full-precision model within 0.002.

Run `python waste_vision.py photo.jpg` to test it in the terminal.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).parent
MODEL_FILE = ROOT / "models" / "waste_yolov8m_fp16w.onnx"
IMG_SIZE = 512                 # the size the model was trained at
MIN_SCORE = 0.30               # below this, a box is not shown at all
SURE_SCORE = 0.55              # below this, the page asks the user to confirm
IOU_LIMIT = 0.5                # boxes that overlap more than this are treated as the same item

CLASSES = ["cardboard", "e-waste", "glass", "medical", "metal", "organic", "paper", "plastic"]

# What the page shows for each class. "stream" follows the three streams of the
# Solid Waste Management Rules 2016: wet (biodegradable), dry (non-biodegradable)
# and domestic hazardous. E-waste has its own rules (E-Waste Management Rules 2022).
STREAMS = {
    "wet": {"name": "Wet waste", "colour": "#1E8F55", "short": "Wet"},
    "dry": {"name": "Dry waste", "colour": "#2E6FD8", "short": "Dry"},
    "hazardous": {"name": "Domestic hazardous", "colour": "#D3263E", "short": "Hazardous"},
    "ewaste": {"name": "E-waste", "colour": "#6C4AB6", "short": "E-waste"},
}
LABELS = {
    "organic": ("Food or garden waste", "wet"),
    "paper": ("Paper", "dry"),
    "cardboard": ("Cardboard", "dry"),
    "plastic": ("Plastic", "dry"),
    "metal": ("Metal", "dry"),
    "glass": ("Glass", "dry"),
    "medical": ("Medical waste", "hazardous"),
    "e-waste": ("Electronic waste", "ewaste"),
}
# The question the "Why?" button asks the rules assistant for each class.
WHY_QUESTIONS = {
    "organic": "How should household food and garden waste be segregated and disposed of?",
    "paper": "How should waste paper be segregated and disposed of by a household?",
    "cardboard": "How should cardboard and packaging waste be segregated by a household?",
    "plastic": "How should plastic waste be segregated and disposed of by a household?",
    "metal": "How should metal waste like cans be segregated by a household?",
    "glass": "How should glass waste be segregated and handed over by a household?",
    "medical": "How should a household dispose of expired medicines, used syringes and other domestic hazardous waste?",
    "e-waste": "Who should e-waste like old phones, chargers and cables be handed over to?",
}


@dataclass
class Item:
    cls: str
    score: float
    box: tuple[float, float, float, float]      # x1, y1, x2, y2 in the original photo

    @property
    def label(self) -> str:
        return LABELS[self.cls][0]

    @property
    def stream(self) -> str:
        return LABELS[self.cls][1]

    @property
    def sure(self) -> bool:
        return self.score >= SURE_SCORE


class WasteDetector:
    def __init__(self, model_file: Path = MODEL_FILE, threads: int = 2):
        import onnxruntime as ort

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads               # keeps memory and CPU use small
        opts.inter_op_num_threads = 1
        # The weights stay in half precision in memory and are turned into full precision
        # inside the model (Cast nodes) while it runs. Basic optimisation and no memory arena
        # keep the model at about 200 MB of memory instead of about 400 MB.
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        opts.enable_cpu_mem_arena = False
        self.session = ort.InferenceSession(str(model_file), opts, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name

    @staticmethod
    def _letterbox(img: Image.Image):
        """Resize the photo to fit 512 x 512 without stretching, padding the rest with grey."""
        w, h = img.size
        r = min(IMG_SIZE / w, IMG_SIZE / h)
        nw, nh = round(w * r), round(h * r)
        canvas = Image.new("RGB", (IMG_SIZE, IMG_SIZE), (114, 114, 114))
        dx, dy = (IMG_SIZE - nw) // 2, (IMG_SIZE - nh) // 2
        canvas.paste(img.resize((nw, nh), Image.BILINEAR), (dx, dy))
        x = np.asarray(canvas, dtype=np.float32).transpose(2, 0, 1)[None] / 255.0
        return x, r, dx, dy

    def detect(self, img: Image.Image) -> list[Item]:
        img = ImageOps.exif_transpose(img).convert("RGB")
        x, r, dx, dy = self._letterbox(img)
        out = self.session.run(None, {self.input_name: x})[0][0]     # (4 + classes, boxes)
        out = out.T
        scores = out[:, 4:]
        cls = scores.argmax(1)
        conf = scores.max(1)
        keep = conf >= MIN_SCORE
        boxes, cls, conf = out[keep, :4], cls[keep], conf[keep]
        if not len(conf):
            return []
        cx, cy, bw, bh = boxes.T                                     # centre format -> corners
        xyxy = np.stack([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], 1)
        idx = _nms(xyxy, conf, IOU_LIMIT)
        W, H = img.size
        items = []
        for i in idx[:20]:
            x1, y1, x2, y2 = xyxy[i]
            x1, x2 = [float(np.clip((v - dx) / r, 0, W)) for v in (x1, x2)]
            y1, y2 = [float(np.clip((v - dy) / r, 0, H)) for v in (y1, y2)]
            items.append(Item(CLASSES[int(cls[i])], float(conf[i]), (x1, y1, x2, y2)))
        return items


def _nms(xyxy: np.ndarray, conf: np.ndarray, limit: float) -> list[int]:
    """Keep the best box, remove boxes that overlap it too much, repeat."""
    order = conf.argsort()[::-1]
    areas = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
    kept = []
    while len(order):
        i = order[0]
        kept.append(int(i))
        rest = order[1:]
        xx1 = np.maximum(xyxy[i, 0], xyxy[rest, 0]); yy1 = np.maximum(xyxy[i, 1], xyxy[rest, 1])
        xx2 = np.minimum(xyxy[i, 2], xyxy[rest, 2]); yy2 = np.minimum(xyxy[i, 3], xyxy[rest, 3])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        iou = inter / (areas[i] + areas[rest] - inter + 1e-9)
        order = rest[iou < limit]
    return kept


def draw(img: Image.Image, items: list[Item]) -> Image.Image:
    """Draw numbered boxes in each item's stream colour. Unsure items get a dashed look."""
    img = ImageOps.exif_transpose(img).convert("RGB")
    out = img.copy()
    d = ImageDraw.Draw(out)
    W, H = out.size
    lw = max(3, round(min(W, H) / 160))
    try:
        font = ImageFont.load_default(size=max(18, round(min(W, H) / 22)))
    except TypeError:
        font = ImageFont.load_default()
    for n, it in enumerate(items, start=1):
        colour = STREAMS[it.stream]["colour"]
        x1, y1, x2, y2 = it.box
        if it.sure:
            d.rectangle([x1, y1, x2, y2], outline=colour, width=lw)
        else:                                          # dashed box for "not sure"
            dash = lw * 4
            for x in np.arange(x1, x2, dash * 2):
                d.line([x, y1, min(x + dash, x2), y1], fill=colour, width=lw)
                d.line([x, y2, min(x + dash, x2), y2], fill=colour, width=lw)
            for y in np.arange(y1, y2, dash * 2):
                d.line([x1, y, x1, min(y + dash, y2)], fill=colour, width=lw)
                d.line([x2, y, x2, min(y + dash, y2)], fill=colour, width=lw)
        tag = f" {n} "
        tb = d.textbbox((0, 0), tag, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        ty = y1 - th - 2 * lw if y1 - th - 2 * lw > 0 else y1
        d.rectangle([x1, ty, x1 + tw + lw, ty + th + 2 * lw], fill=colour)
        d.text((x1 + lw // 2, ty + lw // 2 - tb[1]), tag, fill="white", font=font)
    return out


if __name__ == "__main__":
    import sys
    import time
    det = WasteDetector()
    for p in sys.argv[1:]:
        t = time.time()
        found = det.detect(Image.open(p))
        print(f"{Path(p).name}: {time.time() - t:.2f}s",
              [(i.cls, round(i.score, 2), i.stream, "sure" if i.sure else "unsure") for i in found])
