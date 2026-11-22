"""Sets, reps and rest per exercise, from the training plan.

sets: number of sets shown; optional: the last set is optional ("2-3 sets").
reps: (min, max) target reps; rest: (min, max) rest in seconds.
side: True when the reps are per side (rest after both sides).
"""

TRAINING = {
    # Day 1: Upper A
    "incline-press": dict(sets=3, reps=(8, 10), rest=(120, 120)),
    "one-arm-row": dict(sets=3, reps=(8, 10), rest=(90, 90), side=True),
    "flat-press": dict(sets=3, reps=(10, 12), rest=(120, 120)),
    "cs-row": dict(sets=3, reps=(10, 12), rest=(90, 90)),
    "lateral-raise": dict(sets=3, reps=(12, 15), rest=(60, 90)),
    "incline-curl": dict(sets=3, optional=True, reps=(10, 12), rest=(60, 60)),
    # Day 2: Lower A
    "bulgarian": dict(sets=3, reps=(8, 10), rest=(90, 120), side=True),
    "goblet": dict(sets=3, reps=(10, 12), rest=(90, 90)),
    "rdl": dict(sets=3, reps=(10, 12), rest=(90, 90)),
    "calf": dict(sets=3, reps=(12, 15), rest=(60, 60)),
    "situp": dict(sets=3, reps=(12, 15), rest=(60, 60), bodyweight=True),
    # Day 3: Upper B
    "shoulder-press": dict(sets=3, reps=(8, 10), rest=(120, 120)),
    "pullover": dict(sets=3, reps=(10, 12), rest=(90, 90)),
    "incline-fly": dict(sets=3, reps=(12, 15), rest=(90, 90)),
    "rear-delt": dict(sets=3, reps=(12, 15), rest=(60, 90)),
    "tricep-ext": dict(sets=3, reps=(10, 12), rest=(60, 90)),
    "hammer": dict(sets=3, optional=True, reps=(10, 12), rest=(60, 60)),
    # Day 4: Lower B
    "rdl-heavy": dict(sets=3, reps=(8, 10), rest=(120, 120)),
    "reverse-lunge": dict(sets=3, reps=(10, 10), rest=(90, 90), side=True),
    "glute-bridge": dict(sets=3, reps=(12, 15), rest=(90, 90)),
    "single-calf": dict(sets=3, reps=(12, 15), rest=(60, 60), side=True),
    "russian-twist": dict(sets=3, reps=(15, 20), rest=(60, 60)),
}


def rest_text(t):
    lo, hi = t["rest"]
    return f"{lo} s" if lo == hi else f"{lo}–{hi} s"


def reps_text(t):
    lo, hi = t["reps"]
    return str(lo) if lo == hi else f"{lo}–{hi}"


def rest_badge(ex_id):
    t = TRAINING[ex_id]
    return f'<span class="badge rest">⏱ Rust {rest_text(t)}</span>'


def log_block(ex_id, name):
    t = TRAINING[ex_id]
    lo, hi = t["reps"]
    rows = []
    for i in range(1, t["sets"] + 1):
        opt = t.get("optional") and i == t["sets"]
        label = f"Set {i}" + (" <small>(optioneel)</small>" if opt else "")
        kg = ('<span class="bw">eigen gewicht</span>' if t.get("bodyweight") else
              f'<input class="kg" type="text" inputmode="decimal" placeholder="kg" aria-label="{name} set {i} gewicht in kg">')
        rows.append(
            f'<div class="set-row" data-set="{i}">'
            f'<span class="set-name">{label}</span>{kg}'
            f'<input class="reps" type="text" inputmode="numeric" placeholder="{reps_text(t)}" aria-label="{name} set {i} herhalingen">'
            f'<button type="button" class="set-done" aria-pressed="false">✓ Klaar</button></div>')
    side = " per kant" if t.get("side") else ""
    return (f'<div class="log" data-ex="{ex_id}" data-name="{name}" data-min="{lo}" data-max="{hi}" '
            f'data-rest="{t["rest"][0]}" data-rest-max="{t["rest"][1]}" data-sets="{t["sets"]}" '
            f'data-optional="{1 if t.get("optional") else 0}">'
            f'<div class="log-head"><strong>Vandaag</strong>'
            f'<span class="log-target">{t["sets"] - (1 if t.get("optional") else 0)}{"–" + str(t["sets"]) if t.get("optional") else ""} × {reps_text(t)}{side} · rust {rest_text(t)}</span>'
            f'<button type="button" class="rest-btn">⏱ Start rust</button></div>'
            f'<p class="log-prev"></p>'
            + "".join(rows) +
            '<p class="log-hint" aria-live="polite"></p></div>')
