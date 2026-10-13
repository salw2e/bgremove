import os, urllib.request
import cv2
import numpy as np
import onnxruntime as ort

HOME = os.path.expanduser(os.environ.get("U2NET_HOME", "~/.u2net"))
FILES = {
    "face_detection_yunet_2023mar.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "faceparse34.onnx": "https://github.com/yakhyo/face-parsing/releases/download/v0.0.1/resnet34.onnx",
}
GLASSES, HAIR = 6, 17
HAIR_NEAR = 9
WALL_NEAR = 30
SKIN = (1, 2, 3, 4, 5, 10, 11, 12, 13)
_nets = {}


def _file(name):
    path = os.path.join(HOME, name)
    if not os.path.isfile(path):
        os.makedirs(HOME, exist_ok=True)
        urllib.request.urlretrieve(FILES[name], path + ".part")
        os.replace(path + ".part", path)
    return path


def _parser():
    if "parse" not in _nets:
        _nets["parse"] = ort.InferenceSession(_file("faceparse34.onnx"), providers=["CPUExecutionProvider"])
    return _nets["parse"]


def faces(bgr):
    h, w = bgr.shape[:2]
    scale = min(1.0, 960 / max(h, w))
    small = cv2.resize(bgr, (max(1, round(w * scale)), max(1, round(h * scale)))) if scale < 1 else bgr
    finder = cv2.FaceDetectorYN.create(_file("face_detection_yunet_2023mar.onnx"), "", (small.shape[1], small.shape[0]), 0.75, 0.3, 20)
    found = finder.detect(small)[1]
    return [] if found is None else [tuple(float(v) / scale for v in f[:4]) for f in found]


def parts(bgr):
    side = bgr.shape[0]
    x = cv2.cvtColor(cv2.resize(bgr, (512, 512), interpolation=cv2.INTER_AREA if side > 512 else cv2.INTER_LINEAR), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    x = ((x - (0.485, 0.456, 0.406)) / (0.229, 0.224, 0.225)).astype(np.float32).transpose(2, 0, 1)[None]
    labels = _parser().run(None, {"input": x})[0][0].argmax(0).astype(np.uint8)
    return cv2.resize(labels, (side, side), interpolation=cv2.INTER_NEAREST)


def _centres(lab, k=6):
    lab = lab[np.random.default_rng(0).choice(len(lab), min(len(lab), 4000), replace=False)].astype(np.float32)
    k = min(k, len(lab))
    return cv2.kmeans(lab, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 2, cv2.KMEANS_PP_CENTERS)[2]


def _nearest(lab, centres):
    d = (lab[:, None, :].astype(np.float32) - centres[None]) * (0.5, 1, 1)
    return np.sqrt((d ** 2).sum(-1)).min(1)


# clears the wall that shows through the part of a lens sticking out past the face
def see_through(bgr, alpha, debug=None):
    out = alpha.copy()
    H, W = alpha.shape
    for (fx, fy, fw, fh) in faces(bgr):
        if min(fw, fh) < 90:
            continue
        side = int(min(1.9 * max(fw, fh), 2 * max(H, W)))
        x0, y0 = int(fx + fw / 2 - side / 2), int(fy + fh / 2 - side / 2)
        pad = max(0, -x0, -y0, x0 + side - W, y0 + side - H)
        big = cv2.copyMakeBorder(bgr, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(127, 127, 127)) if pad else bgr
        labels = parts(big[y0 + pad:y0 + pad + side, x0 + pad:x0 + pad + side])
        cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x0 + side), min(H, y0 + side)
        labels = labels[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
        crop, a = bgr[cy0:cy1, cx0:cx1], out[cy0:cy1, cx0:cx1]

        glasses = labels == GLASSES
        skin = np.isin(labels, SKIN)
        if glasses.sum() < 0.004 * side * side or skin.sum() < 0.02 * side * side:
            continue
        hull = np.zeros(labels.shape, np.uint8)
        cv2.fillConvexPoly(hull, cv2.convexHull(cv2.findNonZero(skin.astype(np.uint8))), 1)
        cand = glasses & (hull == 0) & (a > 127)
        if cand.sum() < 0.03 * glasses.sum():
            continue

        reach = max(3, int(0.06 * side)) | 1
        ring = (cv2.dilate(cand.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (reach, reach))) > 0) & (a < 13)
        if ring.sum() < 300:
            continue
        lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)
        hair = (labels == HAIR) & (a > 240)
        wallish = np.zeros(labels.shape, np.float32)
        wallish[cand] = _nearest(lab[cand], _centres(lab[ring])) < WALL_NEAR
        hairish = np.zeros(labels.shape, np.float32)
        if hair.sum() >= 300:
            hairish[cand] = _nearest(lab[cand], _centres(lab[hair])) < HAIR_NEAR
        blob = lambda m: cv2.GaussianBlur(m, (0, 0), 0.012 * side) > 0.5
        n, comp, stats, _ = cv2.connectedComponentsWithStats(cand.astype(np.uint8))
        gone = np.zeros(labels.shape, bool)
        for i in range(1, n):
            piece = comp == i
            if stats[i, cv2.CC_STAT_AREA] < 0.02 * glasses.sum():
                continue
            share = (wallish * (1 - hairish))[piece].mean()
            if share > 0.6:
                gone |= piece & blob(wallish)
            elif share > 0.25:
                gone |= piece & blob(wallish * (1 - hairish))
        if not gone.any():
            continue

        face = glasses & (hull == 1)
        edge = cv2.distanceTransform(1 - cv2.Canny(hull * 255, 50, 150) // 255, cv2.DIST_L2, 3)
        band = glasses & (a > 127) & (((hull == 1) & (edge < 0.025 * side)) | ((hull == 0) & (edge < 0.05 * side)))
        if (face & ~band).sum() >= 300 and (gone & ~band).sum() >= 300 and band.any():
            lab_band = lab[band]
            wall = np.zeros(labels.shape, np.float32)
            wall[band] = _nearest(lab_band, _centres(lab[gone & ~band])) < _nearest(lab_band, _centres(lab[face & ~band]))
            wall[gone & ~band] = 1
            wall = cv2.GaussianBlur(wall, (0, 0), 0.008 * side) > 0.5
            n, comp = cv2.connectedComponents(wall.astype(np.uint8))
            touching = np.unique(comp[gone & ~band])
            gone = (gone & ~band) | (band & np.isin(comp, touching[touching > 0]))

        grey = lab[..., 0]
        k = max(5, int(0.03 * side)) | 1
        thin = cv2.absdiff(grey, cv2.medianBlur(grey, min(k, 255))) > 16
        outside = (a < 13).astype(np.uint8)
        near = cv2.distanceTransform(1 - outside, cv2.DIST_L2, 3) < 0.035 * side
        rim = (thin & near & gone).astype(np.uint8)
        n, comp, stats, _ = cv2.connectedComponentsWithStats(rim)
        long_ = np.zeros(n, bool)
        long_[1:] = np.maximum(stats[1:, cv2.CC_STAT_WIDTH], stats[1:, cv2.CC_STAT_HEIGHT]) > 0.05 * side
        rim = cv2.dilate((long_[comp]).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0

        factor = np.ones(labels.shape, np.float32)
        factor[gone & ~rim] = 0
        soft = max(1.0, side / 700)
        factor = cv2.GaussianBlur(factor, (0, 0), soft)
        out[cy0:cy1, cx0:cx1] = np.minimum(a, (a.astype(np.float32) * factor).astype(np.uint8))
        if debug is not None:
            debug.append({"box": (cx0, cy0, cx1, cy1), "glasses": glasses, "hull": hull, "cand": cand, "gone": gone, "rim": rim})
    return out
