"""The 22 exercise animations: key poses, tempo and highlighted muscles.

Side-view key pose fields (see rig.solve_side):
  hip | shoulder   anchor point (shoulder keeps the shoulder fixed, e.g. glute bridge)
  torso            world angle hip -> shoulder (-90 = upright, facing right)
  neck             head tilt relative to the torso (+ = chin to chest)
  legn / legf      {ankle|ball, bend, foot} for IK, or {ang: (thigh, shin), foot}
  armn / armf      {ang: (upper, fore), k}, {hand|rel, bend, k} for IK,
                   or {jel, jhand}: elbow and hand in the torso frame (along, front)
  dbn / dbf        dumbbell placement {mode: abs|fa|torso, ang, shift}
Each seq step: (seconds, target key or None to hold, label, effort 0..1).
The sequence always returns to key 0.
"""
import math
from rig import (FLOOR, PAD_TOP, UA, FA, THIGH, SHIN, add, vec, rot, angle, dist, seg2,
                 bench_flat, bench_incline, bench_end, line, pad, f1)

EXERCISES = []


def ex(**kw):
    kw["uid"] = len(EXERCISES)
    EXERCISES.append(kw)


def hang(extra=None):
    d = {"ang": (90, 90)}
    if extra:
        d.update(extra)
    return d


STAND_ANK = (112, 156)

# ---------------- Day 1 ----------------
press_legs = {"legn": {"ankle": (178, 156), "bend": -1, "foot": 0},
              "legf": {"ankle": (173, 156), "bend": -1, "foot": 0}}
ex(id="incline-press", aria="Incline dumbbell press op een bank van 30 graden",
   caption="Schuin drukken vanaf de bovenborst", tempo="1 s drukken · 2 s zakken · 1 s pauze",
   scene=bench_incline(130, 210, -15), hl=["chest", "delts", "triceps"],
   db_kind={"n": "end", "f": "end"},
   keys=[
       dict(hip=(134, 120), torso=-150, **press_legs,
            armn={"jel": (0.5, 23.5), "jhand": (1.5, 45)}, armf={"jel": (0.5, 23.5), "jhand": (1.5, 45)},
            dbn={}, dbf={}),
       dict(hip=(134, 120), torso=-150, **press_legs,
            armn={"jel": (-2, -12), "jhand": (-1, 8)}, armf={"jel": (-2, -12), "jhand": (-1, 8)},
            dbn={}, dbf={}),
   ],
   seq=[(0.3, None, "boven", 0.5), (2.0, 1, "zakken · 2 s", 0.45), (1.0, None, "pauze · 1 s", 0.6),
        (1.0, 0, "drukken · 1 s", 1.0)])

ex(id="one-arm-row", aria="One-arm dumbbell row met knie en hand op de bank",
   caption="Elleboog richting heup trekken", tempo="1 s trekken · ½ s knijpen · 2 s zakken",
   scene=bench_flat(48, 162), hl=["lats", "upperback", "biceps"],
   db_kind={"n": "side"},
   keys=[
       dict(hip=(92, 89), torso=-6,
            legn={"ankle": (100, 156), "bend": -1, "foot": 0},
            legf={"ang": (88, 180), "foot": 180},
            armf={"hand": (133, 125), "bend": 1},
            armn={"ang": (91, 90)}, dbn={"mode": "abs"}),
       dict(hip=(92, 89), torso=-8,
            legn={"ankle": (100, 156), "bend": -1, "foot": 0},
            legf={"ang": (88, 180), "foot": 180},
            armf={"hand": (133, 125), "bend": 1},
            armn={"ang": (200, 94)}, dbn={"mode": "abs"}),
   ],
   seq=[(1.0, 1, "trekken · 1 s", 1.0), (0.5, None, "knijpen", 1.0), (2.0, 0, "zakken · 2 s", 0.45),
        (0.4, None, "onder", 0.2)])

flat_legs = {"legn": {"ankle": (170, 156), "bend": -1, "foot": 0},
             "legf": {"ankle": (165, 156), "bend": -1, "foot": 0}}
ex(id="flat-press", aria="Flat dumbbell press liggend op een vlakke bank",
   caption="Vlak drukken boven de borst", tempo="1 s drukken · 2 s zakken",
   scene=bench_flat(46, 168), hl=["chest", "delts", "triceps"],
   keys=[
       dict(hip=(135, 119), torso=180, **flat_legs,
            armn={"jel": (0.5, 23.5), "jhand": (1.5, 45)}, armf={"jel": (0.5, 23.5), "jhand": (1.5, 45)},
            dbn={}, dbf={}),
       dict(hip=(135, 119), torso=180, **flat_legs,
            armn={"jel": (-2.5, -12), "jhand": (-1.5, 8)}, armf={"jel": (-2.5, -12), "jhand": (-1.5, 8)},
            dbn={}, dbf={}),
   ],
   seq=[(0.3, None, "boven", 0.5), (2.0, 1, "zakken · 2 s", 0.45), (0.4, None, "onder", 0.6),
        (1.0, 0, "drukken · 1 s", 1.0)])

cs_common = dict(hip=(70, 111), torso=-40,
                 legn={"ankle": (54, 156), "bend": -1, "foot": 0},
                 legf={"ankle": (50, 156), "bend": -1, "foot": 0})
ex(id="cs-row", aria="Chest-supported row met de borst tegen een schuine bank",
   caption="Borst op de bank, beide armen", tempo="1 s trekken · 1 s vast · 2 s zakken",
   scene=bench_incline(66, -40, 180, back_len=64, seat_len=24), hl=["upperback", "lats", "biceps"],
   keys=[
       dict(**cs_common, armn={"ang": (90, 90)}, armf={"ang": (90, 90)}, dbn={}, dbf={}),
       dict(**cs_common, armn={"ang": (200, 92)}, armf={"ang": (200, 92)}, dbn={}, dbf={}),
   ],
   seq=[(1.0, 1, "trekken · 1 s", 1.0), (1.0, None, "vasthouden", 1.0), (2.0, 0, "zakken · 2 s", 0.45),
        (0.3, None, "onder", 0.2)])


# --- front-view helpers ---
def front_stand(f, cx=120, hip_y=90, torso_k=1.0, legs=True):
    f["torsoF"] = (cx, hip_y, -90, torso_k, 1)
    neck = (cx, hip_y - 40 * torso_k)
    f["headF"] = (neck[0], neck[1], -90, 1, 1)
    if legs:
        for s, sg in (("l", -1), ("r", 1)):
            hp = (cx + 6.5 * sg, hip_y + 2)
            kn = (cx + 7.5 * sg, hip_y + 36)
            an = (cx + 9 * sg, 156)
            f["thighF_" + s] = seg2(hp, kn, THIGH)
            f["shinF_" + s] = seg2(kn, an, SHIN)
            f["footF_" + s] = (an[0], an[1], 90, 1, 1)
    return [(cx - 13, hip_y - 36 * torso_k), (cx + 13, hip_y - 36 * torso_k)]


def arms_2d(f, shoulders, ua_l, fa_l, db=True, size=1.0):
    """Mirror-symmetric arms in the picture plane. Angles for the left arm."""
    for s, sh, a1, a2 in (("l", shoulders[0], ua_l, fa_l), ("r", shoulders[1], 180 - ua_l, 180 - fa_l)):
        el = add(sh, vec(a1, UA))
        hand = add(el, vec(a2, FA + 0.5))
        f["ua_" + s] = (sh[0], sh[1], a1, 1, 1)
        f["fa_" + s] = (el[0], el[1], a2, 1, 1)
        if db:
            f["db_" + s] = (hand[0], hand[1], 0, 1, 1)


FRONT_ORDER = ["thighF_l", "shinF_l", "footF_l", "thighF_r", "shinF_r", "footF_r", "@scene",
               "torsoF", "headF", "headTop", "ua_l", "fa_l", "db_l", "ua_r", "fa_r", "db_r", "@front"]


def lateral_solver(p):
    f = {}
    sh = front_stand(f)
    r = p["raise"]
    arms_2d(f, sh, 100 + 76 * r, 94 + 72 * r)
    return f


ex(id="lateral-raise", aria="Lateral raise van voren gezien: armen zijwaarts tot schouderhoogte",
   caption="Zijwaarts heffen tot schouderhoogte (vooraanzicht)", tempo="1 s heffen · ½ s vast · 2 s zakken",
   solver=lateral_solver, order=FRONT_ORDER, hl=["delts"], hl_all=True,
   keys=[{"raise": 0.0}, {"raise": 1.0}],
   seq=[(1.0, 1, "heffen · 1 s", 1.0), (0.5, None, "vasthouden", 1.0), (2.0, 0, "zakken · 2 s", 0.45),
        (0.3, None, "onder", 0.2)])

curl_seat = dict(hip=(135, 122), torso=-125,
                 legn={"ankle": (180, 156), "bend": -1, "foot": 0},
                 legf={"ankle": (175, 156), "bend": -1, "foot": 0})
ex(id="incline-curl", aria="Incline dumbbell curl op een bank van 55 graden",
   caption="Elleboog blijft achter het lichaam", tempo="1 s curlen · 2 s zakken",
   scene=bench_incline(128, 235, -15), hl=["biceps", "forearm"],
   keys=[
       dict(**curl_seat, armn={"ang": (93, 93)}, armf={"ang": (93, 93)}, dbn={}, dbf={}),
       dict(**curl_seat, armn={"ang": (93, -48)}, armf={"ang": (93, -48)}, dbn={}, dbf={}),
   ],
   seq=[(1.0, 1, "curlen · 1 s", 1.0), (0.4, None, "knijpen", 1.0), (2.0, 0, "zakken · 2 s", 0.45),
        (0.3, None, "onder", 0.2)])

# ---------------- Day 2 ----------------
ex(id="bulgarian", aria="Bulgarian split squat met de achterste voet op de bank",
   caption="Achterste voet op de bank, recht zakken", tempo="2 s zakken · 1 s omhoog",
   scene=bench_flat(22, 92), hl=["quads", "glutes"],
   db_kind={"n": "side", "f": "side"},
   keys=[
       dict(hip=(116, 92), torso=-82,
            legn={"ankle": (138, 156), "bend": -1, "foot": 0},
            legf={"ankle": (66, 124), "bend": -1, "foot": 180},
            armn=hang(), armf=hang(), dbn={"mode": "abs"}, dbf={"mode": "abs"}),
       dict(hip=(106, 120), torso=-78,
            legn={"ankle": (138, 156), "bend": -1, "foot": 0},
            legf={"ankle": (66, 124), "bend": -1, "foot": 180},
            armn=hang(), armf=hang(), dbn={"mode": "abs"}, dbf={"mode": "abs"}),
   ],
   seq=[(0.4, None, "boven", 0.3), (2.0, 1, "zakken · 2 s", 0.5), (0.3, None, "onder", 0.7),
        (1.0, 0, "omhoog · 1 s", 1.0)])

gob_legs = {"legn": {"ankle": (114, 156), "bend": -1, "foot": 0},
            "legf": {"ankle": (111, 156), "bend": -1, "foot": 0}}
gob_arms = {"armn": {"jel": (-21, 8), "jhand": (-5, 12)}, "armf": {"jel": (-21, 8), "jhand": (-5, 12)},
            "dbn": {"mode": "torso", "ang": 0, "shift": -6}}
ex(id="goblet", aria="Goblet squat met één dumbbell rechtop voor de borst",
   caption="Dumbbell voor de borst, diep zakken", tempo="2 s zakken · 1 s omhoog",
   hl=["quads", "glutes"], db_kind={"n": "side"}, db_size=1.15,
   keys=[
       dict(hip=(110, 88), torso=-88, **gob_legs, **gob_arms),
       dict(hip=(90, 126), torso=-62, **gob_legs, **gob_arms),
   ],
   seq=[(0.4, None, "boven", 0.3), (2.0, 1, "zakken · 2 s", 0.5), (0.4, None, "onder", 0.7),
        (1.0, 0, "omhoog · 1 s", 1.0)])


def rdl(id_, aria, caption, size):
    legs = {"legn": {"ankle": (112, 156), "bend": -1, "foot": 0},
            "legf": {"ankle": (109, 156), "bend": -1, "foot": 0}}
    ex(id=id_, aria=aria, caption=caption, tempo="2 s zakken · 1 s omhoog",
       hl=["hams", "glutes"], db_size=size,
       keys=[
           dict(hip=(108, 88), torso=-86, **legs, armn=hang(), armf=hang(), dbn={}, dbf={}),
           dict(hip=(86, 94), torso=-16, **legs, armn=hang(), armf=hang(), dbn={}, dbf={}),
       ],
       seq=[(0.5, None, "boven", 0.3), (2.0, 1, "heupen naar achteren · 2 s", 0.55), (0.3, None, "rek", 0.7),
            (1.0, 0, "heupen naar voren · 1 s", 1.0)])


rdl("rdl", "Romanian deadlift: heupen naar achteren met rechte rug", "Heupen naar achteren duwen", 1.0)


def calf(id_, aria, caption, single):
    def key(foot):
        k = dict(hip=(109, 88), torso=-89, carry="n",
                 legn={"ball": (124, 160), "bend": -1, "foot": foot},
                 armn=hang(), dbn={"mode": "abs"})
        if single:
            k["legf"] = {"ang": (96, 172), "foot": 120}
            k["armf"] = {"hand": (150, 66), "bend": 1}
        else:
            k["legf"] = {"ball": (121, 160), "bend": -1, "foot": foot}
            k["armf"] = hang()
            k["dbf"] = {"mode": "abs"}
        return k
    scene = '<rect class="wall" x="152" y="20" width="10" height="140" rx="2"/>' if single else ""
    ex(id=id_, aria=aria, caption=caption, tempo="1 s omhoog · 1½ s vast · 2 s zakken",
       hl=["calves"], db_kind={"n": "side", "f": "side"}, scene=scene,
       keys=[key(0), key(36)],
       seq=[(1.0, 1, "omhoog · 1 s", 1.0), (1.5, None, "vasthouden", 1.0), (2.0, 0, "zakken · 2 s", 0.45),
            (0.3, None, "onder", 0.2)])


calf("calf", "Staande calf raise: hoog op de tenen", "Hoog op de tenen duwen", False)

decline_scene = (line((122, 124), (122, 158)) + line((62, 140), (62, 158)) + line((52, 158), (160, 158))
                 + line((128, 122), (150, 129)) + line((150, 129), (150, 158))
                 + pad((126, 116), 165, 74)
                 + '<circle class="pad" cx="153" cy="136" r="5.5"/>')
sit_legs = {"legn": {"ankle": (150, 145), "bend": -1, "foot": 10},
            "legf": {"ankle": (147, 145), "bend": -1, "foot": 10}}
sit_arms = {"armn": {"jel": (-15, 13), "jhand": (-1, 11)}, "armf": {"jel": (-15, 13), "jhand": (-1, 11)},
            "dbn": {}}
ex(id="situp", aria="Decline sit-up op een schuine bank met de voeten onder de rol",
   caption="Gecontroleerd oprollen", tempo="1 s op · 2½ s terug",
   scene=decline_scene, hl=["abs"], db_size=0.8,
   order=["thigh_f", "shin_f", "foot_f", "ua_f", "fa_f", "db_f", "@scene",
          "torso", "head", "thigh_n", "shin_n", "foot_n", "ua_n", "fa_n", "db_n"],
   keys=[
       dict(hip=(120, 109), torso=165, neck=12, **sit_legs, **sit_arms),
       dict(hip=(120, 109), torso=250, neck=18, **sit_legs, **sit_arms),
   ],
   seq=[(1.2, 1, "oprollen · 1 s", 1.0), (0.3, None, "boven", 0.8), (2.5, 0, "terug · 2½ s", 0.5),
        (0.3, None, "onder", 0.2)])

# ---------------- Day 3 ----------------
seat80 = dict(hip=(131, 120), torso=-100,
              legn={"ankle": (170, 156), "bend": -1, "foot": 0},
              legf={"ankle": (166, 156), "bend": -1, "foot": 0})
ex(id="shoulder-press", aria="Seated dumbbell shoulder press op een bank van 80 graden",
   caption="Recht boven het hoofd drukken", tempo="1 s drukken · 2 s zakken",
   scene=bench_incline(123, 260, -15, back_len=54), hl=["delts", "triceps"],
   keys=[
       dict(**seat80, armn={"jel": (-13, 4), "jhand": (6, 2.5)}, armf={"jel": (-13, 4), "jhand": (6, 2.5)},
            dbn={}, dbf={}),
       dict(**seat80, armn={"jel": (22, 3), "jhand": (44, 2)}, armf={"jel": (22, 3), "jhand": (44, 2)},
            dbn={}, dbf={}),
   ],
   seq=[(1.0, 1, "drukken · 1 s", 1.0), (0.3, None, "boven", 0.6), (2.0, 0, "zakken · 2 s", 0.45),
        (0.4, None, "onder", 0.3)])

po_legs = {"legn": {"ankle": (162, 156), "bend": -1, "foot": 0},
           "legf": {"ankle": (158, 156), "bend": -1, "foot": 0}}
ex(id="pullover", aria="Dumbbell pullover dwars over de bank",
   caption="Grote boog achter het hoofd", tempo="2 s zakken · 1 s terug",
   scene=bench_end(90, top=126), hl=["lats", "chest"], db_kind={"n": "side"},
   keys=[
       dict(shoulder=(92, 118), torso=190, neck=-8, **po_legs,
            armn={"ang": (-86, -90)}, armf={"ang": (-86, -90)}, dbn={"mode": "fa", "shift": 6}),
       dict(shoulder=(92, 118), torso=190, neck=-8, **po_legs,
            armn={"ang": (-172, -180)}, armf={"ang": (-172, -180)}, dbn={"mode": "fa", "shift": 6}),
   ],
   seq=[(0.3, None, "boven", 0.4), (2.0, 1, "achter hoofd · 2 s", 0.5), (0.4, None, "rek", 0.7),
        (1.2, 0, "terugtrekken · 1 s", 1.0)])


def fly_solver(p):
    f = {}
    cx, hip_y = 120, 124
    f["torsoF"] = (cx, hip_y, -90, 1, 1)
    f["headF"] = (cx, hip_y - 40, -90, 1, 1)
    for s, sg in (("l", -1), ("r", 1)):
        hp = (cx + 6.5 * sg, hip_y + 2)
        f["thighF_" + s] = seg2(hp, (cx + 8 * sg, hip_y + 20), THIGH)
    th = p["open"]
    for s, sg in (("l", -1), ("r", 1)):
        sh = (cx + 13 * sg, hip_y - 36)
        def proj(theta, ydir):
            d3 = (sg * math.sin(math.radians(theta)), ydir, -math.cos(math.radians(theta)))
            n = math.sqrt(sum(c * c for c in d3))
            return (d3[0] / n, d3[1] / n)
        u = proj(th, 0.22)
        el = add(sh, u, UA)
        v = proj(th - 22, 0.18)
        hand = add(el, v, FA + 0.5)
        f["ua_" + s] = seg2(sh, el, UA)
        f["fa_" + s] = seg2(el, add(el, v, FA), FA)
        f["db_" + s] = (hand[0], hand[1], 90, 1, 1)
    return f


ex(id="incline-fly", aria="Incline dumbbell fly van boven gezien: armen in een wijde boog",
   caption="Wijde boog, alsof je een boom omhelst (bovenaanzicht)", tempo="2 s openen · 1 s sluiten",
   solver=fly_solver, order=["thighF_l", "thighF_r", "@scene", "torsoF", "headF",
                             "ua_l", "fa_l", "db_l", "ua_r", "fa_r", "db_r"],
   scene='<rect class="pad" x="98" y="50" width="44" height="84" rx="7"/>', no_floor=True,
   hl=["pecsF"], db_kind={"l": "side", "r": "side"},
   keys=[{"open": 0.0}, {"open": 82.0}],
   seq=[(0.3, None, "dicht", 0.6), (2.0, 1, "openen · 2 s", 0.5), (0.3, None, "rek", 0.7),
        (1.0, 0, "sluiten · 1 s", 1.0)])


def rear_solver(p):
    f = {}
    sh = front_stand(f, hip_y=104, torso_k=0.5, legs=False)
    del f["headF"]
    f["headTop"] = (120, 86, -90, 1, 1)
    r = p["raise"]
    arms_2d(f, sh, 94 + 74 * r, 92 + 66 * r)
    return f


ex(id="rear-delt", aria="Rear delt fly met de borst op een schuine bank, van voren gezien",
   caption="Armen wijd omhoog heffen (vooraanzicht)", tempo="1 s heffen · ½ s vast · 2 s zakken",
   solver=rear_solver, order=FRONT_ORDER, hl=["delts", "upperback"], hl_all=True,
   scene=('<polygon class="pad" points="101,90 139,90 133,128 107,128"/>'
          + line((120, 128), (120, 158)) + line((100, 158), (140, 158))),
   keys=[{"raise": 0.0}, {"raise": 1.0}],
   seq=[(1.0, 1, "heffen · 1 s", 1.0), (0.5, None, "vasthouden", 1.0), (2.0, 0, "zakken · 2 s", 0.45),
        (0.3, None, "onder", 0.2)])

ex(id="tricep-ext", aria="Seated overhead tricep extension met één dumbbell achter het hoofd",
   caption="Vanuit de nek recht omhoog strekken", tempo="2 s zakken · 1 s strekken",
   scene=bench_incline(123, 260, -15, back_len=48), hl=["triceps"], db_kind={"n": "side"},
   keys=[
       dict(**seat80, armn={"ang": (-100, -98)}, armf={"ang": (-100, -98)}, dbn={"mode": "fa", "shift": 6}),
       dict(**seat80, armn={"ang": (-100, -232)}, armf={"ang": (-100, -232)}, dbn={"mode": "fa", "shift": 6}),
   ],
   seq=[(0.3, None, "boven", 0.5), (2.0, 1, "zakken · 2 s", 0.5), (0.3, None, "rek", 0.7),
        (1.0, 0, "strekken · 1 s", 1.0)])

ham_legs = {"legn": {"ankle": (112, 156), "bend": -1, "foot": 0},
            "legf": {"ankle": (109, 156), "bend": -1, "foot": 0}}
ex(id="hammer", aria="Staande hammer curl met de duimen omhoog",
   caption="Duimen wijzen omhoog (hamergreep)", tempo="1 s curlen · 2 s zakken",
   hl=["biceps", "forearm"], db_kind={"n": "side", "f": "side"},
   keys=[
       dict(hip=(109, 88), torso=-89, **ham_legs, armn={"ang": (93, 90)}, armf={"ang": (93, 90)},
            dbn={"mode": "fa", "ang": 90}, dbf={"mode": "fa", "ang": 90}),
       dict(hip=(109, 88), torso=-89, **ham_legs, armn={"ang": (96, -52)}, armf={"ang": (96, -52)},
            dbn={"mode": "fa", "ang": 90}, dbf={"mode": "fa", "ang": 90}),
   ],
   seq=[(1.0, 1, "curlen · 1 s", 1.0), (0.4, None, "knijpen", 1.0), (2.0, 0, "zakken · 2 s", 0.45),
        (0.3, None, "onder", 0.2)])

# ---------------- Day 4 ----------------
rdl("rdl-heavy", "Zwaardere Romanian deadlift: heupen naar achteren met rechte rug",
    "Zwaardere RDL, focus op hamstrings", 1.2)


def lunge_key(hip, torso, ball, foot):
    return dict(hip=hip, torso=torso,
                legn={"ankle": (128, 156), "bend": -1, "foot": 0},
                legf={"ball": ball, "bend": -1, "foot": foot},
                armn=hang(), armf=hang(), dbn={"mode": "abs"}, dbf={"mode": "abs"})


ex(id="reverse-lunge", aria="Reverse lunge: grote stap naar achteren en zakken",
   caption="Grote pas achterwaarts zetten", tempo="2 s stap en zakken · 1 s terug",
   hl=["glutes", "quads"], db_kind={"n": "side", "f": "side"},
   keys=[
       lunge_key((124, 88), -88, (139, 160), 0),
       lunge_key((114, 100), -84, (96, 146), 25),
       lunge_key((100, 118), -80, (64, 160), 50),
   ],
   seq=[(0.4, None, "staan", 0.3), (0.7, 1, "stap terug", 0.4), (1.3, 2, "zakken", 0.55),
        (0.3, None, "onder", 0.7), (0.6, 1, "terug duwen · 1 s", 1.0), (0.5, 0, "terug duwen · 1 s", 0.9)])

gb_arms = {"armn": {"jel": (-14, 16), "jhand": (-33, 12)}, "armf": {"jel": (-14, 16), "jhand": (-33, 12)},
           "dbn": {}}
gb_legs = {"legn": {"ankle": (159, 126), "bend": -1, "foot": -65},
           "legf": {"ankle": (156, 126), "bend": -1, "foot": -65}}
ex(id="glute-bridge", aria="Glute bridge op de grond met de hielen op de bank en een dumbbell op de heupen",
   caption="Hielen op de bank, heupen omhoog", tempo="1 s omhoog · 1 s knijpen · 2 s zakken",
   scene=bench_end(162, top=PAD_TOP), hl=["glutes", "hams"], db_size=1.15,
   keys=[
       dict(shoulder=(66, 150), torso=180, neck=0, **gb_legs, **gb_arms),
       dict(shoulder=(66, 150), torso=150, neck=30, **gb_legs, **gb_arms),
   ],
   seq=[(1.0, 1, "omhoog · 1 s", 1.0), (1.0, None, "billen knijpen", 1.0), (2.0, 0, "zakken · 2 s", 0.45),
        (0.3, None, "onder", 0.2)])

calf("single-calf", "Single-leg calf raise met één hand steun tegen de muur", "Eén been tegelijk op de tenen", True)


def twist_solver(p):
    f = {}
    cx = 120
    s = math.sin(math.pi / 2 * p["tw"])
    hip = (cx, 146)
    neck = (cx + 8 * s, 104)
    k = dist(hip, neck) / 40
    sy = 1 - 0.3 * abs(s)
    f["torsoF"] = (hip[0], hip[1], angle(hip, neck), k, sy)
    f["headF"] = (neck[0], neck[1], -90 + 8 * s, 1, 1)
    for side, sg in (("l", -1), ("r", 1)):
        hp = (cx + 7 * sg, 148)
        kn = (cx + 15 * sg, 121)
        an = (cx + 18 * sg, 152)
        f["thighF_" + side] = seg2(hp, kn, THIGH)
        f["shinF_" + side] = seg2(kn, an, SHIN)
        f["footF_" + side] = (an[0], an[1], 90, 1, 1)
    u = ((neck[0] - hip[0]) / (40 * k), (neck[1] - hip[1]) / (40 * k))
    w = (-u[1], u[0])
    top = add(hip, u, 36 * k)
    hand = (cx + 38 * s, 116 + 28 * s * s)
    for side, sg in (("l", -1), ("r", 1)):
        sh = add(top, w, 13 * sy * sg)
        mid = ((sh[0] + hand[0]) / 2, (sh[1] + hand[1]) / 2)
        el = add(mid, (sg * 9, 6))
        f["ua_" + side] = seg2(sh, el, UA)
        f["fa_" + side] = seg2(el, hand, FA)
    f["db_n"] = (hand[0], hand[1] + 1, 0, 1, 1)
    return f


ex(id="russian-twist", aria="Russian twist van voren gezien: romp draait van links naar rechts",
   caption="Romp rustig van links naar rechts draaien (vooraanzicht)", tempo="rustig: ±1 s per kant",
   solver=twist_solver, hl=["obliques"], db_kind={"n": "side"}, db_size=0.9,
   order=["torsoF", "headF", "thighF_l", "shinF_l", "footF_l", "thighF_r", "shinF_r", "footF_r",
          "ua_l", "fa_l", "ua_r", "fa_r", "db_n"],
   keys=[{"tw": 0.0}, {"tw": -1.0}, {"tw": 1.0}],
   seq=[(0.9, 1, "draai links", 1.0), (0.2, None, "draai links", 1.0), (1.8, 2, "draai rechts", 1.0),
        (0.2, None, "draai rechts", 1.0), (0.9, 0, "midden", 0.8)])

BY_ID = {e["id"]: e for e in EXERCISES}
