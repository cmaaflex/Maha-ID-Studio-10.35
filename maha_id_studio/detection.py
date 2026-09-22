"""Bounded-resolution detection of the printed portrait rectangle, not a face."""
import cv2
import numpy as np
from PIL import Image

PRESETS = {
    'MAHA ID / MahaSarathi': (.02, .07, .40, .72),
    'Aadhaar': (.02, .15, .37, .90),
    'ABHA': (.02, .12, .42, .92),
    'NSDL PAN': (.02, .20, .38, .94),
    'eShram': (.01, .15, .42, .95),
    'Ayushman': (.01, .12, .45, .94),
    'Voter ID': (.02, .15, .65, .94),
    'UDID': (.02, .12, .48, .94),
}


def infer_preset(label):
    text = str(label).casefold()
    for key in PRESETS:
        if any(word in text for word in key.lower().replace('/', ' ').split()):
            return key
    return 'Auto Detect'


def detect_photo(image, front, preset='MAHA ID / MahaSarathi', custom=None):
    bounds = (custom or PRESETS).get(preset, (.01, .05, .97, .96))
    fx, fy, fr, fb = front
    width, height = fr - fx, fb - fy
    if min(width, height) <= 8:
        raise ValueError('Front card boundary is too small.')
    crop = image.crop(front).convert('RGB')
    crop.thumbnail((1000, 700), Image.Resampling.BILINEAR)
    sx, sy = width / crop.width, height / crop.height
    rgb = np.asarray(crop)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    x0, y0, x1, y1 = [round(v * (crop.width if n % 2 == 0 else crop.height)) for n, v in enumerate(bounds)]
    roi = rgb[y0:y1, x0:x1]
    if not roi.size:
        raise ValueError('Invalid photo search region.')
    g = gray[y0:y1, x0:x1]
    # Border candidates retain the entire photo. No face-box crop is used.
    edges = cv2.Canny(g, 35, 100)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(closed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    # Colour density can locate borderless portraits, but sparse name/DOB text
    # cannot qualify as a dense rectangular photograph.
    hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
    mask = ((hsv[:, :, 1] > 30) & (hsv[:, :, 2] < 245)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    colour_contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for contour in contours + colour_contours:
        x, y, w, h = cv2.boundingRect(contour)
        if not (.10 * crop.width <= w <= .38 * crop.width and .19 * crop.height <= h <= .72 * crop.height and .42 <= w / h <= 1.1):
            continue
        patch = g[y:y+h, x:x+w]
        colour_density = float((hsv[y:y+h, x:x+w, 1] > 25).mean())
        texture = float(cv2.Laplacian(patch, cv2.CV_32F).var())
        # Require evidence along all four edges, avoiding a textured face-only box.
        edge = edges[y:y+h, x:x+w] > 0
        band = max(2, min(w, h) // 25)
        support = min(edge[:band].any(axis=0).mean(), edge[-band:].any(axis=0).mean(),
                      edge[:, :band].any(axis=1).mean(), edge[:, -band:].any(axis=1).mean())
        if texture < 15 or (support < .45 and colour_density < .4):
            continue
        confidence = 92 if support > .7 and (colour_density > .15 or texture > 120) else 78
        score = w * h * (1 + support) * (1 + min(colour_density, .6))
        box = (round(fx + (x0+x)*sx), round(fy + (y0+y)*sy),
               round(fx + (x0+x+w)*sx), round(fy + (y0+y+h)*sy))
        candidates.append((score, confidence, box))
    if candidates:
        _, confidence, box = max(candidates, key=lambda value:value[0])
        return box, confidence
    # Conservative fallback is always review-required.
    return (round(fx+width*.05), round(fy+height*.135), round(fx+width*.295), round(fy+height*.555)), 40
