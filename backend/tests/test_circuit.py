import json
import math

import pytest

import circuit


def square_outline(n_per_side=20, size=1000.0):
    """Closed-ish square loop, counter-clockwise from (0, 0)."""
    pts = []
    for i in range(n_per_side):
        pts.append((size * i / n_per_side, 0.0))
    for i in range(n_per_side):
        pts.append((size, size * i / n_per_side))
    for i in range(n_per_side):
        pts.append((size - size * i / n_per_side, size))
    for i in range(n_per_side):
        pts.append((0.0, size - size * i / n_per_side))
    return pts


def raw_payload(corners=None, rotation=0, outline=None):
    pts = outline or square_outline()
    return {
        "circuitName": "Test Circuit",
        "year": 2026,
        "rotation": rotation,
        "x": [p[0] for p in pts],
        "y": [p[1] for p in pts],
        "corners": corners if corners is not None else [
            {"number": 1, "trackPosition": {"x": 1000.0, "y": 0.0}, "angle": 0},   # index 20
            {"number": 2, "trackPosition": {"x": 1000.0, "y": 1000.0 - 50}, "angle": 90, "letter": "A"},
            {"number": 3, "trackPosition": {"x": 0.0, "y": 1000.0}, "angle": 180},
        ],
    }


def test_builds_closed_outline_with_numbered_corners_and_start():
    built, reason = circuit.build_circuit_map(raw_payload())

    assert reason is None
    assert built["circuit_name"] == "Test Circuit"
    assert built["outline"][0] == built["outline"][-1]  # loop closed
    assert [(c["number"], c["letter"]) for c in built["corners"]] == [(1, ""), (2, "A"), (3, "")]
    assert built["start"] is not None
    assert json.loads(json.dumps(built)) == built  # JSON-serialisable


def test_coordinates_are_normalised_to_a_zero_origin_and_size_matches():
    built, _ = circuit.build_circuit_map(raw_payload())
    xs = [p[0] for p in built["outline"]] + [c["label_x"] for c in built["corners"]]
    ys = [p[1] for p in built["outline"]] + [c["label_y"] for c in built["corners"]]

    assert min(xs) == 0 and min(ys) == 0
    assert math.isclose(max(xs), built["width"], abs_tol=0.1)
    assert math.isclose(max(ys), built["height"], abs_tol=0.1)


def test_svg_y_axis_is_flipped():
    built, _ = circuit.build_circuit_map(raw_payload())
    start = built["start"]
    top_right = next(c for c in built["corners"] if c["number"] == 3)  # raw (0, 1000): highest raw y

    # raw y up == smaller svg y, so the highest raw point has the smallest svg y of the outline
    assert top_right["y"] < start["y"]


def test_rotation_is_counter_clockwise():
    flat, _ = circuit.build_circuit_map(raw_payload(rotation=0))
    turned, _ = circuit.build_circuit_map(raw_payload(rotation=90, corners=[]))
    # Raw start->right direction (+x) points to raw +y after a 90 degree CCW rotation, which is svg "up".
    start = flat["start"]
    assert start["ahead_x"] > start["x"]  # unrotated: travelling in +x
    first, second = turned["outline"][0], turned["outline"][5]
    assert second[1] < first[1] and math.isclose(second[0], first[0], abs_tol=0.1)


def test_far_off_corner_is_dropped_instead_of_misplaced():
    corners = raw_payload()["corners"] + [{"number": 9, "trackPosition": {"x": 5000.0, "y": 5000.0}}]

    built, _ = circuit.build_circuit_map(raw_payload(corners=corners))

    assert 9 not in [c["number"] for c in built["corners"]]
    assert len(built["corners"]) == 3


def test_missing_optional_corner_fields_are_tolerated():
    corners = [{"number": 1, "trackPosition": {"x": 1000.0, "y": 0.0}}]  # no letter, no angle

    built, _ = circuit.build_circuit_map(raw_payload(corners=corners))

    assert built["corners"][0]["letter"] == ""


def test_start_marker_is_dropped_when_corners_are_out_of_order():
    corners = [
        {"number": 1, "trackPosition": {"x": 0.0, "y": 1000.0}},     # late on the outline
        {"number": 2, "trackPosition": {"x": 1000.0, "y": 0.0}},     # earlier on the outline
    ]

    built, _ = circuit.build_circuit_map(raw_payload(corners=corners))

    assert built["start"] is None
    assert len(built["corners"]) == 2  # the map itself is still useful


def test_start_marker_is_dropped_when_first_corner_is_far_from_the_start():
    corners = [{"number": 1, "trackPosition": {"x": 0.0, "y": 600.0}}]  # ~3/4 round the loop

    built, _ = circuit.build_circuit_map(raw_payload(corners=corners))

    assert built["start"] is None


def test_no_corners_still_gives_an_outline_without_markers():
    built, reason = circuit.build_circuit_map(raw_payload(corners=[]))

    assert reason is None and built["corners"] == [] and built["start"] is None


def test_produces_no_sector_information():
    built, _ = circuit.build_circuit_map(raw_payload())

    assert not any("sector" in key for key in built)


@pytest.mark.parametrize("raw,reason", [
    (None, "no_data"),
    ({}, "no_data"),
    ({"x": [1, 2, 3], "y": [1, 2, 3]}, "invalid_outline"),  # too few points
    ({"x": list(range(60)), "y": list(range(59))}, "invalid_outline"),  # length mismatch
    ({"x": [float("nan")] * 60, "y": [0.0] * 60}, "invalid_outline"),
    ({"x": [5.0] * 60, "y": [5.0] * 60}, "invalid_outline"),  # zero size
])
def test_invalid_payloads_are_rejected_with_a_reason(raw, reason):
    assert circuit.build_circuit_map(raw) == (None, reason)
