"""Figure rig: shapes, kinematics, timeline sampling and SVG/CSS output.

Coordinates are SVG user units in a 240 x 170 viewBox, y pointing down.
Angles are degrees, 0 = pointing right, positive = clockwise on screen.
Every body segment is drawn in its own local frame along +x, starting at
its joint. Side-view figures face right; local +y is the front of the
torso and the back of a hanging limb.
"""
import math

FPS = 40
W, H = 240, 170
FLOOR = 160
PAD_TOP = 128

TORSO, UA, FA, THIGH, SHIN = 40, 24, 22, 35, 34
SHOULDER = (38, 1)
NECK = (40, -1)
BALL = (11, 4)          # ball of the foot, relative to the ankle
FAR_OFF = (-1.5, -1.5)  # far-side limbs sit slightly up/back for depth

TOL = (0.25, 0.25, 0.8, 0.012, 0.012)  # x, y, angle, sx, sy


# ---------- vector helpers ----------
def rad(a):
    return math.radians(a)


def vec(a, l=1.0):
    return (l * math.cos(rad(a)), l * math.sin(rad(a)))


def add(p, q, s=1.0):
    return (p[0] + s * q[0], p[1] + s * q[1])


def sub(p, q):
    return (p[0] - q[0], p[1] - q[1])


def rot(p, a):
    c, s = math.cos(rad(a)), math.sin(rad(a))
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


def angle(p, q):
    return math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))


def dist(p, q):
    return math.hypot(q[0] - p[0], q[1] - p[1])


def ik(root, target, l1, l2, bend):
    """Two-bone IK. Returns world angles of both bones. bend=+1/-1 picks the side."""
    d = dist(root, target)
    d = max(abs(l1 - l2) + 1e-3, min(l1 + l2 - 1e-3, d))
    a = angle(root, target)
    c = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    alpha = math.degrees(math.acos(max(-1.0, min(1.0, c))))
    a1 = a + bend * alpha
    j = add(root, vec(a1, l1))
    return a1, angle(j, target)


def seg2(a, b, length):
    """Segment from joint a to joint b, scaled along x to fit."""
    return (a[0], a[1], angle(a, b), max(dist(a, b) / length, 0.02), 1.0)


# ---------- shapes ----------
def f1(v):
    s = f"{v:.1f}"
    return "0" if s in ("-0.0", "0.0") else s.rstrip("0").rstrip(".") if "." in s else s


def capsule(length, w0, w1, b0=0.0, b1=0.0, cls="skin"):
    """Tapered limb along +x. b0 bulges the -y side, b1 the +y side."""
    L, h0, h1 = length, w0 / 2, w1 / 2
    d = (f"M0,{f1(-h0)} C{f1(L*.33)},{f1(-h0-b0)} {f1(L*.66)},{f1(-h1-b0)} {f1(L)},{f1(-h1)} "
         f"A{f1(h1)},{f1(h1)} 0 0 1 {f1(L)},{f1(h1)} "
         f"C{f1(L*.66)},{f1(h1+b1)} {f1(L*.33)},{f1(h0+b1)} 0,{f1(h0)} "
         f"A{f1(h0)},{f1(h0)} 0 0 1 0,{f1(-h0)}Z")
    return f'<path class="{cls}" d="{d}"/>'


SHAPES = {
    "torso": (
        '<path class="shirt" d="M-4,-8 C8,-10 24,-11 34,-10 C41,-9 44,-4 43,2 C42,8 37,11.5 31,11 '
        'C24,10.5 18,8 13,8 C6,8.5 0,10 -4,6 C-7,2 -7,-5 -4,-8Z"/>'
        '<path class="shorts" d="M-4,-8.5 C2,-10 8,-9.6 12,-9.6 L12,8.2 C6,8.5 0,10 -4,6 C-7.5,2 -7.5,-5 -4,-8.5Z"/>'
    ),
    "head": (
        capsule(8, 7, 6.5)
        + '<path class="skin" d="M3,3.5 C5,4 5.5,6 7,7.5 C8,8.5 9.5,8.4 10.2,8.2 L11.6,8.3 L13.2,9.9 L15.6,7.8 '
        'C17.6,7.4 19.6,6.8 20.6,4.5 C22.6,0 21.6,-5 18,-7.6 C14,-9.9 8,-9.6 5.5,-6 C4.5,-5 4,-4.5 4,-4Z"/>'
        '<path class="hair" d="M13,-9.4 C17,-9.6 21,-6.6 22,-1 C22.3,2 21.6,4 20.6,5.6 C19.6,3.6 18,1 15,-0.5 '
        'C11,-2 8,-4 5,-5.6 C7,-8.6 10,-9.5 13,-9.4Z"/>'
        '<ellipse class="feat" cx="12.5" cy="-2" rx="2.4" ry="1.8"/>'
        '<circle fill="#1f2937" cx="16.6" cy="5.4" r="0.9"/>'
    ),
    "thigh": capsule(35, 14, 9.5, 1.2, 0.8) + capsule(19, 15.5, 13.5, 0.4, 0.4, "shorts"),
    "shin": capsule(34, 9.5, 6, 0, 1.8),
    "foot": '<path class="shoe" d="M-4.5,-2 C-5.5,3 -3.5,4.2 0,4.2 L13,4.2 C15.5,4.2 15.5,1 12,0 C8,-1.8 4,-4 0,-4 C-3,-4 -4.5,-3.2 -4.5,-2Z"/>',
    "ua": capsule(24, 9.5, 7.5, 0.8, 1.0) + capsule(9, 11, 10, 0.3, 0.3, "shirt"),
    "fa": capsule(22, 7.5, 5.5, 0.6, 0.3) + '<circle class="skin" cx="22.5" cy="0" r="3.7"/>',
    # front view
    "torsoF": (
        '<path class="shirt" d="M-3,-11 C6,-11 12,-10.5 15,-10 C22,-11 28,-13 34,-14.5 C38.5,-15 41,-12 41,-5 '
        'L41,5 C41,12 38.5,15 34,14.5 C28,13 22,11 15,10 C12,10.5 6,11 -3,11 C-6,6 -6,-6 -3,-11Z"/>'
        '<path class="shorts" d="M-3.5,-11.5 C3,-11.6 8,-11.2 11,-10.8 L11,10.8 C8,11.2 3,11.6 -3.5,11.5 C-6.5,6 -6.5,-6 -3.5,-11.5Z"/>'
    ),
    "headF": (
        capsule(8, 8, 7)
        + '<ellipse class="feat" cx="12" cy="-8" rx="2.2" ry="1.6"/><ellipse class="feat" cx="12" cy="8" rx="2.2" ry="1.6"/>'
        '<ellipse class="skin" cx="13" cy="0" rx="9.5" ry="7.6"/>'
        '<path class="hair" d="M13,-7.7 C19,-8.2 23,-4 23,0 C23,4 19,8.2 13,7.7 C17,4 17.5,-4 13,-7.7Z"/>'
        '<circle fill="#1f2937" cx="13.2" cy="-3" r="0.9"/><circle fill="#1f2937" cx="13.2" cy="3" r="0.9"/>'
        '<path d="M8.3,-2 Q7.4,0 8.3,2" fill="none" stroke="#9a5b3f" stroke-width="0.8" stroke-linecap="round"/>'
    ),
    "headTop": (
        capsule(5, 8, 7)
        + '<ellipse class="skin" cx="9" cy="0" rx="8" ry="7.6"/>'
        '<path class="hair" d="M4,-6 C10,-9 18,-8 18,0 C18,8 10,9 4,6 C7,3 7,-3 4,-6Z"/>'
    ),
    "footF": '<ellipse class="shoe" cx="3" cy="0" rx="4.5" ry="5.5"/>',
}
SHAPES["thighF"] = capsule(35, 13, 9, 0.6, 0.6) + capsule(17, 14.5, 12.5, 0.3, 0.3, "shorts")
SHAPES["shinF"] = capsule(34, 8.5, 6, 0.8, 0.8)


def dumbbell(kind, size=1.0):
    s = size
    if kind == "end":  # handle axis points into the screen: we see a hex plate
        def hexagon(r):
            return " ".join(f"{f1(r*math.cos(rad(30+60*i)))},{f1(r*math.sin(rad(30+60*i)))}" for i in range(6))
        return (f'<polygon class="db" points="{hexagon(7.5*s)}"/>'
                f'<polygon class="db-hi" points="{hexagon(4.2*s)}"/>'
                f'<circle class="db-bar" r="{f1(1.8*s)}"/>')
    # handle axis in the picture plane, along local x
    return (f'<rect class="db-bar" x="{f1(-7*s)}" y="{f1(-1.7*s)}" width="{f1(14*s)}" height="{f1(3.4*s)}" rx="1"/>'
            f'<rect class="db" x="{f1(-13.5*s)}" y="{f1(-7.5*s)}" width="{f1(6.5*s)}" height="{f1(15*s)}" rx="1.5"/>'
            f'<rect class="db" x="{f1(7*s)}" y="{f1(-7.5*s)}" width="{f1(6.5*s)}" height="{f1(15*s)}" rx="1.5"/>')


HIGHLIGHTS = {
    # name: (segment kind, ellipses (cx, cy, rx, ry))
    "chest": ("torso", [(31, 7.5, 8, 3.6)]),
    "lats": ("torso", [(23, -8, 10, 2.8)]),
    "upperback": ("torso", [(35, -7, 6, 3)]),
    "abs": ("torso", [(17, 7, 10, 2.6)]),
    "glutes": ("torso", [(0, -7, 6.5, 3.6)]),
    "quads": ("thigh", [(17, -4.6, 12, 2.6)]),
    "hams": ("thigh", [(18, 4.4, 12, 2.6)]),
    "calves": ("shin", [(11, 3.4, 8, 2.2)]),
    "delts": ("ua", [(2.5, 0, 5.5, 5)]),
    "biceps": ("ua", [(14, -2.6, 7.5, 2.2)]),
    "triceps": ("ua", [(13, 2.8, 8, 2.2)]),
    "forearm": ("fa", [(7, -1.8, 6, 1.8)]),
    "pecsF": ("torsoF", [(31, -6.5, 5, 5.5), (31, 6.5, 5, 5.5)]),
    "obliques": ("torsoF", [(16, -8, 7, 2.4), (16, 8, 7, 2.4)]),
}


# ---------- benches and scenery (static SVG) ----------
def pad(p0, a, length, th=7):
    n_y = math.cos(rad(a))  # y of local +y axis
    y0 = 0 if n_y > 0 else -th
    return (f'<rect class="pad" x="0" y="{y0}" width="{f1(length)}" height="{th}" rx="3" '
            f'transform="translate({f1(p0[0])} {f1(p0[1])}) rotate({f1(a)})"/>')


def line(*pts, cls="frame"):
    return f'<polyline class="{cls}" points="{" ".join(f"{f1(x)},{f1(y)}" for x, y in pts)}"/>'


def floor():
    return f'<line class="floor" x1="6" y1="{FLOOR}" x2="234" y2="{FLOOR}"/>'


def bench_flat(x0, x1, top=PAD_TOP):
    b = FLOOR - 2
    return (line((x0 + 14, top + 8), (x0 + 14, b)) + line((x1 - 14, top + 8), (x1 - 14, b))
            + line((x0 + 4, b), (x0 + 26, b)) + line((x1 - 26, b), (x1 - 4, b))
            + line((x0 + 14, top + 11), (x1 - 14, top + 11)) + pad((x0, top), 0, x1 - x0))


def bench_incline(hx, back_a, seat_a, back_len=56, seat_len=30, top=PAD_TOP):
    """back_a / seat_a are world angles of the pads, starting at the hinge."""
    h = (hx, top)
    b = FLOOR - 2
    mid = add(h, vec(back_a, back_len * 0.55))
    awayn = rot((0, 1), back_a)
    if awayn[1] < 0:
        awayn = (-awayn[0], -awayn[1])
    m2 = add(mid, awayn, 9)
    seat_end = add(h, vec(seat_a, seat_len * 0.8))
    lo = min(m2[0], seat_end[0]) - 6
    hi = max(m2[0], seat_end[0]) + 6
    return (line((hx, top + 8), (hx, b)) + line((lo, b), (hi, b))
            + line(m2, (m2[0], b)) + line(add(seat_end, (0, 8)), (seat_end[0], b))
            + pad(h, back_a, back_len) + pad(h, seat_a, seat_len))


def bench_end(cx, top=PAD_TOP, w=24):
    b = FLOOR - 2
    return (line((cx, top + 6), (cx, b)) + line((cx - 15, b), (cx + 15, b))
            + f'<rect class="pad" x="{f1(cx - w/2)}" y="{f1(top)}" width="{w}" height="8" rx="3"/>')


# ---------- side-view solver ----------
CONST_KEYS = {"bend", "mode", "kind", "carry", "size"}


def lerp(a, b, u, key=None):
    if key in CONST_KEYS:
        return a
    if isinstance(a, dict):
        return {k: lerp(a[k], b[k], u, k) for k in a}
    if isinstance(a, (tuple, list)):
        return tuple(lerp(x, y, u) for x, y in zip(a, b))
    if isinstance(a, (int, float)):
        return a + (b - a) * u
    return a


def solve_side(p):
    t = p["torso"]
    hip = sub(p["shoulder"], rot(SHOULDER, t)) if "shoulder" in p else p["hip"]
    ankles = {}
    for s in "nf":
        L = p.get("leg" + s)
        if not L or "ang" in L:
            continue
        if "ball" in L:
            ankles[s] = sub(L["ball"], rot(BALL, L.get("foot", 0)))
        else:
            ankles[s] = L["ankle"]
    if "carry" in p:  # calf raise: body rises with the ankle
        L = p["leg" + p["carry"]]
        hip = add(hip, sub(ankles[p["carry"]], sub(L["ball"], BALL)))

    f = {"torso": (hip[0], hip[1], t, 1, 1)}
    nk = add(hip, rot(NECK, t))
    f["head"] = (nk[0], nk[1], t + p.get("neck", 0), 1, 1)
    sh = add(hip, rot(SHOULDER, t))

    for s in "nf":
        L = p.get("leg" + s)
        if not L:
            continue
        root = hip if s == "n" else add(hip, FAR_OFF)
        if "ang" in L:
            a1, a2 = L["ang"]
        else:
            a1, a2 = ik(root, ankles[s], THIGH, SHIN, L["bend"])
        knee = add(root, vec(a1, THIGH))
        ank = add(knee, vec(a2, SHIN))
        f["thigh_" + s] = (root[0], root[1], a1, 1, 1)
        f["shin_" + s] = (knee[0], knee[1], a2, 1, 1)
        f["foot_" + s] = (ank[0], ank[1], L.get("foot", 0), 1, 1)

    for s in "nf":
        A = p.get("arm" + s)
        if not A:
            continue
        root = sh if s == "n" else add(sh, FAR_OFF)
        k = A.get("k", 1.0)
        if "ang" in A:
            a1, a2 = A["ang"]
            el = add(root, vec(a1, UA * k))
            hand = add(el, vec(a2, FA))
            f["ua_" + s] = (root[0], root[1], a1, k, 1)
            f["fa_" + s] = (el[0], el[1], a2, 1, 1)
        elif "jel" in A:
            el = add(root, rot(A["jel"], t))
            hand = add(root, rot(A["jhand"], t))
            f["ua_" + s] = seg2(root, el, UA)
            f["fa_" + s] = seg2(el, hand, FA)
            a2 = f["fa_" + s][2]
        else:
            tgt = A["hand"] if "hand" in A else add(root, rot(A["rel"], t))
            if "hand" in A and s == "f":
                tgt = add(tgt, FAR_OFF)
            a1, a2 = ik(root, tgt, UA * k, FA, A["bend"])
            el = add(root, vec(a1, UA * k))
            hand = add(el, vec(a2, FA))
            f["ua_" + s] = (root[0], root[1], a1, k, 1)
            f["fa_" + s] = (el[0], el[1], a2, 1, 1)
        # the hand sits at the end of the (possibly scaled) forearm
        fa = f["fa_" + s]
        hand = add((fa[0], fa[1]), vec(fa[2], FA * fa[3] + 0.5))
        D = p.get("db" + s)
        if D is not None:
            base = {"abs": 0, "fa": a2, "torso": t}[D.get("mode", "abs")]
            da = base + D.get("ang", 0)
            pos = add(hand, vec(da, D.get("shift", 0)))
            f["db_" + s] = (pos[0], pos[1], da, 1, 1)
    return f


SIDE_ORDER = ["thigh_f", "shin_f", "foot_f", "ua_f", "fa_f", "db_f", "@scene",
              "torso", "head", "thigh_n", "shin_n", "foot_n", "ua_n", "fa_n", "db_n", "@front"]


def shape_for(seg, ex):
    kind = seg.split("_")[0]
    if kind == "db":
        side = seg.split("_")[1] if "_" in seg else "n"
        d = ex.get("db_kind", {}).get(side, "end")
        return dumbbell(d, ex.get("db_size", 1.0))
    return SHAPES[kind]


# ---------- timeline ----------
def ease(u):
    return 0.5 - 0.5 * math.cos(math.pi * u)


def sample(ex):
    """Returns (total seconds, list of frames, list of effort, label spans)."""
    keys, seq = ex["keys"], ex["seq"]
    solver = ex.get("solver", solve_side)
    total = sum(s[0] for s in seq)
    n = max(2, round(total * FPS))
    steps, t0, cur = [], 0.0, 0
    for dur, tgt, lab, eff in seq:
        to = cur if tgt is None else tgt
        steps.append((t0, t0 + dur, cur, to, lab, eff))
        t0 += dur
        cur = to
    assert cur == 0, f"{ex['id']}: sequence must end at key 0"
    frames, effort = [], []
    for i in range(n + 1):
        t = total * i / n
        st = next((s for s in steps if s[0] <= t < s[1]), steps[-1])
        u = 1.0 if st[1] == st[0] else min(1.0, (t - st[0]) / (st[1] - st[0]))
        spec = lerp(keys[st[2]], keys[st[3]], ease(u))
        frames.append(solver(spec))
        effort.append(st[5])
    # smooth effort (circular moving average, 0.3 s)
    w = int(0.15 * FPS)
    sm = []
    for i in range(n + 1):
        vals = [effort[(i + j) % n] for j in range(-w, w + 1)]
        sm.append(sum(vals) / len(vals))
    labels = []
    for st in steps:
        if labels and labels[-1][2] == st[4]:
            labels[-1][1] = st[1]
        else:
            labels.append([st[0], st[1], st[4]])
    if len(labels) > 1 and labels[0][2] == labels[-1][2]:
        last = labels.pop()
        labels[0][0] = last[0] - total  # wraps around the cycle start
    return total, frames, sm, labels


def unwrap(vals):
    out, prev = [], None
    for v in vals:
        x, y, a, sx, sy = v
        if prev is not None:
            while a - prev > 180:
                a -= 360
            while a - prev < -180:
                a += 360
        prev = a
        out.append((x, y, a, sx, sy))
    return out


def simplify(vals, tols):
    keep = {0, len(vals) - 1}

    def rec(i, j):
        if j - i < 2:
            return
        worst, wi = 0.0, None
        for k in range(i + 1, j):
            u = (k - i) / (j - i)
            err = max(abs(vals[k][d] - (vals[i][d] + (vals[j][d] - vals[i][d]) * u)) / tols[d]
                      for d in range(len(tols)))
            if err > worst:
                worst, wi = err, k
        if worst > 1:
            keep.add(wi)
            rec(i, wi)
            rec(wi, j)

    rec(0, len(vals) - 1)
    return sorted(keep)


def tf(v, scale):
    x, y, a, sx, sy = v
    s = f"translate({f1(x)}px,{f1(y)}px) rotate({f1(a)}deg)"
    if scale:
        s += f" scale({sx:.3f},{sy:.3f})"
    return s


def pct(i, n):
    return f"{100 * i / n:.2f}".rstrip("0").rstrip(".") + "%"


# ---------- SVG / CSS output ----------
def build(ex, frame_index=None):
    """Returns (svg markup, css keyframes). With frame_index, renders one static frame."""
    total, frames, effort, labels = sample(ex)
    n = len(frames) - 1
    uid = ex["uid"]
    css = []
    parts = []
    order = ex.get("order", SIDE_ORDER)
    hl_by_seg = {}
    for name in ex.get("hl", []):
        kind, ells = HIGHLIGHTS[name]
        for seg in frames[0]:
            if seg.split("_")[0] == kind and (seg.endswith("_n") or "_" not in seg or ex.get("hl_all")):
                hl_by_seg.setdefault(seg, []).extend(ells)

    # effort -> highlight opacity keyframes (shared by all highlight groups)
    hl_anim = ""
    if hl_by_seg and frame_index is None:
        ev = [(e * 0.8, 0, 0, 0, 0) for e in effort]
        keep = simplify(ev, (0.03, 1, 1, 1, 1))
        name = f"h{uid}"
        css.append(f"@keyframes {name}{{" + "".join(f"{pct(i, n)}{{opacity:{ev[i][0]:.2f}}}" for i in keep) + "}")
        hl_anim = f' style="animation-name:{name};animation-duration:{total:.2f}s"'

    for seg in order:
        if seg == "@scene":
            parts.append(ex.get("scene", ""))
            continue
        if seg == "@front":
            parts.append(ex.get("front", ""))
            continue
        if seg not in frames[0]:
            continue
        vals = unwrap([fr[seg] for fr in frames])
        scale = any(abs(v[3] - 1) > 1e-3 or abs(v[4] - 1) > 1e-3 for v in vals)
        far = " far" if seg.endswith("_f") else ""
        inner = shape_for(seg, ex)
        if seg in hl_by_seg:
            if frame_index is None:
                hl = f'<g class="hl"{hl_anim}>'
            else:
                hl = f'<g class="hl" opacity="{effort[frame_index] * 0.8:.2f}">'
            inner += hl + "".join(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"/>' for cx, cy, rx, ry in hl_by_seg[seg]) + "</g>"
        if frame_index is not None:
            x, y, a, sx, sy = vals[frame_index]
            t = f"translate({f1(x)} {f1(y)}) rotate({f1(a)})" + (f" scale({sx:.3f} {sy:.3f})" if scale else "")
            parts.append(f'<g class="{("far" if far else "")}" transform="{t}">{inner}</g>')
            continue
        keep = simplify(vals, TOL)
        if len(keep) == 2 and all(max(abs(vals[0][d] - v[d]) for v in vals) < 1e-6 for d in range(5)):
            x, y, a, sx, sy = vals[0]
            t = f"translate({f1(x)} {f1(y)}) rotate({f1(a)})" + (f" scale({sx:.3f} {sy:.3f})" if scale else "")
            parts.append(f'<g class="{far.strip()}" transform="{t}">{inner}</g>')
            continue
        name = f"k{uid}{seg.replace('_', '')}"
        css.append(f"@keyframes {name}{{" + "".join(f"{pct(i, n)}{{transform:{tf(vals[i], scale)}}}" for i in keep) + "}")
        parts.append(f'<g class="s{far}" style="animation-name:{name};animation-duration:{total:.2f}s">{inner}</g>')

    # phase labels: step opacity, sampled on the same frame grid
    t_of = [total * i / n for i in range(n + 1)]
    for li, (a, b, text) in enumerate(labels):
        on = [1 if (a <= t < b or a <= t - total < b) else 0 for t in t_of]
        on[-1] = on[0]
        if frame_index is not None:
            if on[frame_index]:
                parts.append(f'<text class="ph" x="10" y="16">{text}</text>')
            continue
        kf = [(0, on[0])]
        for i in range(1, n + 1):
            if on[i] != on[i - 1]:
                kf += [(i - 1, on[i - 1]), (i, on[i])]
        kf.append((n, on[n]))
        name = f"p{uid}l{li}"
        css.append(f"@keyframes {name}{{" + "".join(f"{pct(i, n)}{{opacity:{o}}}" for i, o in sorted(set(kf))) + "}")
        parts.append(f'<text class="ph" x="10" y="16" style="animation-name:{name};animation-duration:{total:.2f}s">{text}</text>')
    svg = (f'<svg viewBox="0 0 {W} {H}" class="fig" role="img" aria-label="{ex["aria"]}">'
           + ("" if ex.get("no_floor") else floor()) + "".join(parts) + "</svg>")
    return svg, "\n".join(css)
