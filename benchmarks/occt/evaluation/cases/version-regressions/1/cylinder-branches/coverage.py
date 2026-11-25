"""Continuous positional coverage for the registered M30082 intersect fixture."""
import bisect
import math
from pathlib import Path
import sys


RADIUS = 0.25
LARGE_RADIUS = 3.0
CENTER_Y = -64.3442185874231
CENTER_Z = -19.25
LARGE_X = -124.971129473161
LIMIT = 1e-4
# Allow for arithmetic and the DRAW stream's decimal rounding.
NUMERIC_MARGIN = 1e-9
# Bounds for the branch speed and acceleration with respect to theta.
# x = sin(theta/2)*sqrt(3-0.25*sin(theta/2)^2) on [0, 2*pi].
SPEED = 2
ACCELERATION = 2


def mix(a, b, t):
    return tuple(x + t * (y - x) for x, y in zip(a, b))


def read_spans(path):
    lines = path.read_text().splitlines()
    if not lines or lines[0] != "DrawTrSurf_BSplineCurve":
        raise ValueError("unsupported curve type")
    tokens = lines[1].split()
    kind, rational, periodic, degree, count, knot_count = map(int, tokens[:6])
    poles = list(map(float, tokens[6:]))
    tokens = lines[2].split()
    knots = list(map(float, tokens[::2]))
    multiplicities = list(map(int, tokens[1::2]))
    if (kind != 7 or rational or periodic or not 1 <= degree <= 12
            or len(poles) != 3 * count or len(knots) != knot_count
            or len(multiplicities) != knot_count or len(knots) < 2
            or any(not math.isfinite(x) or abs(x) > 10**4 for x in (*poles, *knots))
            or any(a >= b for a, b in zip(knots, knots[1:]))
            or multiplicities[0] != degree + 1 or multiplicities[-1] != degree + 1
            or any(not 1 <= m <= degree for m in multiplicities[1:-1])
            or sum(multiplicities) != count + degree + 1):
        raise ValueError("unsupported spline basis or discontinuous domain")
    points = [tuple(poles[i:i+3]) for i in range(0, len(poles), 3)]
    expanded = [t for t, m in zip(knots, multiplicities) for _ in range(m)]
    for knot, mult in zip(knots[1:-1], multiplicities[1:-1]):
        for current_mult in range(mult, degree):
            i = bisect.bisect_right(expanded, knot) - 1
            left = i - degree
            right = i - current_mult
            inserted = [mix(points[j-1], points[j],
                            (knot - expanded[j]) / (expanded[j+degree] - expanded[j]))
                        for j in range(left + 1, right + 1)]
            points = points[:left+1] + inserted + points[right:]
            expanded.insert(i + 1, knot)
    if len(points) != (knot_count - 1) * degree + 1:
        raise ValueError("incomplete Bezier spans")
    return [points[i:i+degree+1] for i in range(0, len(points)-1, degree)]


def angle(point):
    _, y, z = point
    if math.hypot(y - CENTER_Y, z - CENTER_Z) < RADIUS / 2:
        raise ValueError("point cannot be assigned an angle on the small cylinder")
    return math.atan2(z - CENTER_Z, y - CENTER_Y)


def reference(theta, sign):
    half = abs(math.sin(theta / 2))
    return (LARGE_X + sign * half * math.sqrt(LARGE_RADIUS - RADIUS * half**2),
            CENTER_Y + RADIUS * math.cos(theta), CENTER_Z + RADIUS * math.sin(theta))


def bisect_bezier(poles):
    left, right = [], []
    while len(poles) > 1:
        left.append(poles[0])
        right.append(poles[-1])
        poles = [mix(a, b, 0.5) for a, b in zip(poles, poles[1:])]
    return left + poles, poles + right[::-1]


def certify(spans):
    # The control points of C(u) minus its chord bound the deviation from that chord
    # by convexity. The analytic branch is compared at theta(u), linear in u.
    leaves = []
    stack = [(span, 0) for span in reversed(spans)]
    while stack:
        poles, depth = stack.pop()
        first, last = poles[0], poles[-1]
        theta0 = angle(first)
        theta1 = theta0 + math.remainder(angle(last) - theta0, math.tau)
        dt = abs(theta1 - theta0)
        interval = tuple(sorted((theta0, theta1)))
        crosses_seam = interval[0] < 0 < interval[1]
        curvature = SPEED * dt if crosses_seam else ACCELERATION * dt**2 / 8
        degree = len(poles) - 1
        hull = max(math.dist(point, mix(first, last, i / degree))
                   for i, point in enumerate(poles))
        for sign in (-1, 1):
            ends = max(math.dist(first, reference(theta0, sign)), math.dist(last, reference(theta1, sign)))
            bound = hull + ends + curvature + NUMERIC_MARGIN
            if bound <= LIMIT / 2:
                leaves.append((sign, interval, bound))
                break
        else:
            if depth >= 20 or dt > math.pi:
                raise ValueError("whole-span geometric error not certified")
            left, right = bisect_bezier(poles)
            stack.extend(((right, depth + 1), (left, depth + 1)))
    return leaves


def circular_intervals(interval):
    low, high = interval
    width = high - low
    first = low % math.tau
    last = first + width
    if last > math.tau:
        return [(first, math.tau), (0, last - math.tau)]
    return [(first, last)]


def gaps(intervals):
    if not intervals:
        return math.tau
    spans = sorted(intervals)
    merged = [list(spans[0])]
    for first, last in spans[1:]:
        if first > merged[-1][1]:
            merged.append([first, last])
        else:
            merged[-1][1] = max(merged[-1][1], last)
    interior = [b[0] - a[1] for a, b in zip(merged, merged[1:])]
    return max([merged[0][0] + math.tau - merged[-1][1], *interior])


def coverage(paths):
    if not paths:
        return False
    intervals = {-1: [], 1: []}
    maximum = 0
    for index, path in enumerate(paths, 1):
        spans = read_spans(path)
        leaves = certify(spans)
        peak = max(leaf[2] for leaf in leaves)
        maximum = max(maximum, peak)
        print(f"CURVE {index} spans={len(spans)} certified_pieces={len(leaves)} upper_error={peak:.12g}")
        for sign, interval, _ in leaves:
            intervals[sign].extend(circular_intervals(interval))
    passed = True
    for sign, ranges in intervals.items():
        gap = gaps(ranges)
        # Every missing angle is within half a gap of an attained analytic angle.
        forward_bound = maximum + SPEED * gap / 2 + NUMERIC_MARGIN
        print(f"BRANCH {sign} maximum_angular_gap={gap:.12g} forward_upper_error={forward_bound:.12g}")
        passed &= forward_bound <= LIMIT
    return passed


def main(argv):
    role, *files = argv
    if role in ("far", "false-far"):
        # The two infinite cylinder axes are respectively X- and Z-directed, so
        # their minimum distance is the absolute world Y displacement.
        clearance = abs(600.0 - CENTER_Y) - RADIUS - LARGE_RADIUS
        if clearance <= LIMIT:
            raise ValueError("the fixture does not certify separation")
        if role == "false-far":
            circle, = files
            lines = Path(circle).read_text().splitlines()
            canonical = (2, -106.471129473161, CENTER_Y, CENTER_Z, 1, 0, 0,
                         0, 0, 1, 0, -1, 0, RADIUS)
            actual = tuple(map(float, lines[1].split()))
            if lines[0] != "DrawTrSurf_Curve" or actual != canonical:
                raise ValueError("no actual false intersection circle on the first cylinder")
        print(f"SEPARATED clearance={clearance:.12g} curves={len(files)}")
        return len(files) == 0
    if role != "regular":
        raise ValueError("unknown fixture role")
    return coverage(list(map(Path, files)))


if __name__ == "__main__":
    try:
        sys.exit(0 if main(sys.argv[1:]) else 1)
    except (ArithmeticError, IndexError, OSError, ValueError) as exc:
        print(f"UNVERIFIED {exc}", file=sys.stderr)
        sys.exit(2)
