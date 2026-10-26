"""Turn a raw MultiViewer circuit payload into a render-ready map.

MultiViewer (the source FastF1's `get_circuit_info` wraps) provides a track outline
(`x`/`y`), numbered corners in the same coordinate space, and a display rotation.
It is unofficial and approximate, so every output is validated and anything that
cannot be supported by the data is left out rather than guessed:

* corners farther than MAX_CORNER_OFFSET from the outline are dropped,
* the start marker is only kept if the first corner follows it closely,
* no sector information is produced (the source only has marshal sectors).

Output coordinates are rotated for display and already flipped for SVG (y down).
"""
import math

MAX_CORNER_OFFSET = 0.03   # corner must lie within 3% of the track's longest side
FIRST_CORNER_WINDOW = 0.25  # corner 1 must come within the first 25% of the outline
LABEL_OFFSET = 0.035        # label distance from its corner, as a fraction of track size
MIN_POINTS = 50


def _rotate(x, y, angle):
    """Counter-clockwise rotation in a y-up frame (FastF1's documented convention)."""
    c, s = math.cos(angle), math.sin(angle)
    return x * c - y * s, x * s + y * c


def _finite_pair(x, y):
    return isinstance(x, (int, float)) and isinstance(y, (int, float)) and math.isfinite(x) and math.isfinite(y)


def build_circuit_map(raw):
    """Return (map_dict, None) on success or (None, reason) when no trustworthy map exists."""
    if not raw:
        return None, "no_data"
    xs, ys = raw.get("x") or [], raw.get("y") or []
    if len(xs) != len(ys) or len(xs) < MIN_POINTS:
        return None, "invalid_outline"
    points = [(float(x), float(y)) for x, y in zip(xs, ys) if _finite_pair(x, y)]
    if len(points) != len(xs):
        return None, "invalid_outline"

    span = max(max(p[0] for p in points) - min(p[0] for p in points),
               max(p[1] for p in points) - min(p[1] for p in points))
    if span <= 0:
        return None, "invalid_outline"

    try:
        rotation = float(raw.get("rotation") or 0.0)
    except (TypeError, ValueError):
        rotation = 0.0
    angle = math.radians(rotation)

    def nearest(cx, cy):
        best_i, best_d = 0, float("inf")
        for i, (px, py) in enumerate(points):
            d = math.hypot(px - cx, py - cy)
            if d < best_d:
                best_i, best_d = i, d
        return best_i, best_d

    corners = []
    for c in raw.get("corners") or []:
        pos = c.get("trackPosition") or {}
        cx, cy = pos.get("x"), pos.get("y")
        if not _finite_pair(cx, cy) or c.get("number") is None:
            continue
        index, dist = nearest(cx, cy)
        if dist > MAX_CORNER_OFFSET * span:
            continue  # unsupported by the outline: do not draw a misplaced label
        a = math.radians(float(c.get("angle") or 0.0))
        lx, ly = cx + LABEL_OFFSET * span * math.cos(a), cy + LABEL_OFFSET * span * math.sin(a)
        corners.append({"number": int(c["number"]), "letter": str(c.get("letter") or ""),
                        "index": index, "xy": (cx, cy), "label": (lx, ly)})

    # Start marker: the outline starts at the reference lap's start. Trust that only if
    # corners then appear in increasing order, beginning soon after the start.
    indices = [c["index"] for c in corners]
    start_ok = bool(corners) and indices == sorted(indices) and indices[0] <= FIRST_CORNER_WINDOW * len(points)

    def to_svg(x, y):
        rx, ry = _rotate(x, y, angle)
        return rx, -ry  # y-up -> SVG y-down

    outline = [to_svg(x, y) for x, y in points]
    outline.append(outline[0])  # source outlines are open by up to ~1%: close the loop
    all_xy = outline + [to_svg(*c["xy"]) for c in corners] + [to_svg(*c["label"]) for c in corners]
    min_x, min_y = min(p[0] for p in all_xy), min(p[1] for p in all_xy)
    max_x, max_y = max(p[0] for p in all_xy), max(p[1] for p in all_xy)

    def norm(p):  # shift so the bounding box starts at 0,0
        return [round(p[0] - min_x, 1), round(p[1] - min_y, 1)]

    result = {
        "circuit_name": raw.get("circuitName"),
        "rotation": rotation,
        "year": raw.get("year"),
        "width": round(max_x - min_x, 1),
        "height": round(max_y - min_y, 1),
        "outline": [norm(p) for p in outline],
        "corners": [
            {"number": c["number"], "letter": c["letter"],
             "x": norm(to_svg(*c["xy"]))[0], "y": norm(to_svg(*c["xy"]))[1],
             "label_x": norm(to_svg(*c["label"]))[0], "label_y": norm(to_svg(*c["label"]))[1]}
            for c in corners
        ],
        "start": None,
    }
    if start_ok:
        ahead = outline[min(8, len(outline) - 2)]  # a few points on, for direction of travel
        result["start"] = {"x": norm(outline[0])[0], "y": norm(outline[0])[1],
                           "ahead_x": norm(ahead)[0], "ahead_y": norm(ahead)[1]}
    return result, None
