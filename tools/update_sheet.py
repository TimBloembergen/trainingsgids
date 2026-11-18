#!/usr/bin/env python3
"""Write the app's logbook export into the training spreadsheet.

The export from the guide (button "Exporteer CSV") is leading: it holds the
full history, so every run rewrites the Week columns it covers.

    python3 tools/update_sheet.py [export.csv] [--sheet file.xlsx] [--dry-run]

Without a CSV it takes the newest trainingslogboek-*.csv from private/ or
~/Downloads. Without --sheet it takes the only .xlsx in private/.

Week mapping: the Monday of the first exported training goes to the first
Week column that is still empty in the sheet. That anchor is saved in
sheet-weeks.json next to the sheet so later runs map the same dates to the same weeks.
A copy of the sheet is saved in backup/ next to the sheet before every write.
"""
import argparse
import csv
import datetime as dt
import html
import json
import pathlib
import re
import shutil
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
PRIVATE = ROOT / "private"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
SHEET_NAME = "Trainingsschema & Logboek"

# Exercise ids per training day, in the order of the sheet's # column.
DAYS = [
    ["incline-press", "one-arm-row", "flat-press", "cs-row", "lateral-raise", "incline-curl"],
    ["bulgarian", "goblet", "rdl", "calf", "situp"],
    ["shoulder-press", "pullover", "incline-fly", "rear-delt", "tricep-ext", "hammer"],
    ["rdl-heavy", "reverse-lunge", "hip-thrust", "single-calf", "russian-twist"],
]


def col_to_num(col):
    n = 0
    for ch in col:
        n = n * 26 + ord(ch) - 64
    return n


def num_to_col(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def monday(d):
    return d - dt.timedelta(days=d.weekday())


# ---------- reading ----------
def find_csv(arg):
    if arg:
        return pathlib.Path(arg)
    found = sorted(list(PRIVATE.glob("trainingslogboek-*.csv"))
                   + list((pathlib.Path.home() / "Downloads").glob("trainingslogboek-*.csv")),
                   key=lambda p: p.stat().st_mtime)
    if not found:
        sys.exit("Geen trainingslogboek-*.csv gevonden in private/ of ~/Downloads.")
    return found[-1]


def find_sheet(arg):
    if arg:
        return pathlib.Path(arg)
    found = list(PRIVATE.glob("*.xlsx"))
    if len(found) != 1:
        sys.exit(f"Verwacht precies één .xlsx in {PRIVATE}, gevonden: {len(found)}. Gebruik --sheet.")
    return found[0]


def names_to_ids():
    """Map exercise names to ids from index.html, for exports without an ID column."""
    page = (ROOT / "index.html").read_text()
    return {html.unescape(n): i for i, n in re.findall(r'data-ex="([^"]+)" data-name="([^"]+)"', page)}


def read_export(path):
    """Returns {id: {date: [(set, kg, reps)]}}."""
    by_name = names_to_ids()
    out = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            ex = row.get("ID") or by_name.get(row["Oefening"])
            if not ex:
                print(f"  overgeslagen (onbekende oefening): {row['Oefening']}")
                continue
            date = dt.date.fromisoformat(row["Datum"])
            out.setdefault(ex, {}).setdefault(date, []).append(
                (int(row["Set"]), row["Gewicht (kg)"].strip(), row["Reps"].strip()))
    return out


def shared_strings(z):
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])) for si in root.findall("m:si", NS)]


def sheet_path(z):
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    for sh in wb.find("m:sheets", NS):
        if sh.get("name") == SHEET_NAME:
            t = rels[sh.get("{%s}id" % NS["r"])].lstrip("/")
            return t if t.startswith("xl/") else "xl/" + t
    sys.exit(f"Tabblad '{SHEET_NAME}' niet gevonden.")


def cell_values(xml, strings):
    """{cell ref: text} for all cells with a value."""
    vals = {}
    for m in re.finditer(r'<c r="([A-Z]+\d+)"([^>]*?)(?:/>|>(.*?)</c>)', xml, re.S):
        ref, attrs, body = m.group(1), m.group(2), m.group(3) or ""
        v = re.search(r"<v>(.*?)</v>", body, re.S)
        if 't="s"' in attrs and v:
            vals[ref] = strings[int(v.group(1))]
        elif 't="inlineStr"' in attrs:
            vals[ref] = html.unescape("".join(re.findall(r"<t[^>]*>(.*?)</t>", body, re.S)))
        elif v:
            vals[ref] = html.unescape(v.group(1))
    return vals


def layout(vals):
    """Finds the rows per exercise and the (weight, reps) columns per week."""
    week_cols = {}
    for ref, v in vals.items():
        m = re.fullmatch(r"Week (\d+)", v.strip())
        if m:
            col = re.match(r"[A-Z]+", ref).group(0)
            week_cols.setdefault(int(m.group(1)), col)
    weeks = {w: (c, num_to_col(col_to_num(c) + 1)) for w, c in week_cols.items()}
    day_rows = sorted(int(re.sub(r"\D", "", r)) for r, v in vals.items()
                      if r.startswith("B") and re.match(r"DAG \d", v.strip()))
    rows = {}
    for d, start in enumerate(day_rows):
        for ex_i, ex in enumerate(DAYS[d]):
            for r in range(start + 1, start + 12):
                v = vals.get(f"B{r}", "")
                if v.replace(".0", "") == str(ex_i + 1):
                    rows[ex] = r
                    break
    missing = [e for day in DAYS for e in day if e not in rows]
    if missing or len(day_rows) != 4:
        sys.exit(f"Kon de indeling van de sheet niet herkennen (ontbreekt: {missing}).")
    return weeks, rows


# ---------- formatting ----------
def fmt_kg(k):
    k = k.replace(".", ",")
    return k


def describe(sets):
    sets = sorted(sets)
    kgs = [fmt_kg(k) for _, k, _ in sets]
    reps = ", ".join(r or "?" for _, _, r in sets)
    if not any(kgs):
        weight = "Lichaam"
    elif all(k == kgs[0] for k in kgs):
        weight = f"{kgs[0]} kg"
    else:
        weight = " / ".join(k or "–" for k in kgs) + " kg"
    return weight, reps


# ---------- writing ----------
def set_cell(xml, ref, text, style_from=None):
    row = int(re.sub(r"\D", "", ref))
    esc = html.escape(text, quote=False)
    cell_re = re.compile(r'<c r="%s"([^>]*?)(?:/>|>.*?</c>)' % ref, re.S)
    m = cell_re.search(xml)
    style = None
    if style_from:
        sm = re.search(r'<c r="%s"[^>]*?\ss="(\d+)"' % style_from, xml)
        style = sm.group(1) if sm else None
    if m:
        if style is None:
            sm = re.search(r'\ss="(\d+)"', m.group(1))
            style = sm.group(1) if sm else None
        new = f'<c r="{ref}"' + (f' s="{style}"' if style else "") + f' t="inlineStr"><is><t>{esc}</t></is></c>'
        return xml[:m.start()] + new + xml[m.end():]
    # cell missing: insert it in column order within its row
    rm = re.search(r'(<row r="%d"[^>]*>)(.*?)(</row>)' % row, xml, re.S)
    if not rm:
        sys.exit(f"Rij {row} niet gevonden in de sheet.")
    new = f'<c r="{ref}"' + (f' s="{style}"' if style else "") + f' t="inlineStr"><is><t>{esc}</t></is></c>'
    cells = re.findall(r'<c r="([A-Z]+)\d+"[^>]*?(?:/>|>.*?</c>)', rm.group(2), re.S)
    target = col_to_num(re.match(r"[A-Z]+", ref).group(0))
    body = rm.group(2)
    pos = len(body)
    for cm in re.finditer(r'<c r="([A-Z]+)\d+"[^>]*?(?:/>|>.*?</c>)', body, re.S):
        if col_to_num(cm.group(1)) > target:
            pos = cm.start()
            break
    body = body[:pos] + new + body[pos:]
    return xml[:rm.start(2)] + body + xml[rm.end(2):]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--sheet")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    csv_path, xlsx = find_csv(args.csv), find_sheet(args.sheet)
    print(f"Export: {csv_path}\nSheet:  {xlsx}")
    data = read_export(csv_path)
    if not data:
        sys.exit("De export bevat geen afgeronde sets.")

    with zipfile.ZipFile(xlsx) as z:
        spath = sheet_path(z)
        xml = z.read(spath).decode("utf-8")
        vals = cell_values(xml, shared_strings(z))
    weeks, rows = layout(vals)

    cfg_path = xlsx.parent / "sheet-weeks.json"
    all_dates = sorted(d for ex in data.values() for d in ex)
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text())
        anchor, anchor_week = dt.date.fromisoformat(cfg["monday"]), cfg["week"]
    else:
        filled = {w for w, (wc, rc) in weeks.items() for r in rows.values()
                  if vals.get(f"{wc}{r}") or vals.get(f"{rc}{r}")}
        anchor_week = next((w for w in sorted(weeks) if w > max(filled, default=0)), None)
        if anchor_week is None:
            sys.exit("Alle Week-kolommen zijn al gevuld.")
        anchor = monday(all_dates[0])
        cfg = {"monday": anchor.isoformat(), "week": anchor_week}
        print(f"Eerste keer: week van {anchor:%d-%m-%Y} wordt Week {anchor_week} (opgeslagen in {cfg_path.name}).")

    changes = []
    for ex, by_date in data.items():
        per_week = {}
        for d in sorted(by_date):
            w = anchor_week + (monday(d) - anchor).days // 7
            per_week[w] = (d, by_date[d])  # latest session of that week wins
        for w, (d, sets) in sorted(per_week.items()):
            if w not in weeks:
                print(f"  {ex}: training van {d} valt in Week {w}, die staat niet in de sheet; overgeslagen.")
                continue
            wc, rc = weeks[w]
            r = rows[ex]
            weight, reps = describe(sets)
            for ref, text, style in ((f"{wc}{r}", weight, f"H{r}"), (f"{rc}{r}", reps, f"I{r}")):
                if vals.get(ref, "") != text:
                    changes.append((ref, vals.get(ref, ""), text, style, ex, w))

    if not changes:
        print("De sheet is al bijgewerkt; niets te doen.")
        return
    for ref, old, new, _, ex, w in changes:
        print(f"  Week {w} {ex:15} {ref:5} {old or '(leeg)'} -> {new}")
    if args.dry_run:
        print(f"{len(changes)} wijzigingen (dry run, niets opgeslagen).")
        return

    for ref, _, new, style, _, _ in changes:
        xml = set_cell(xml, ref, new, style_from=style)

    backup = xlsx.parent / "backup"
    backup.mkdir(exist_ok=True)
    shutil.copy2(xlsx, backup / f"{xlsx.stem} {dt.datetime.now():%Y-%m-%d %H%M%S}.xlsx")
    tmp = xlsx.with_suffix(".tmp")
    with zipfile.ZipFile(xlsx) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            content = xml.encode("utf-8") if item.filename == spath else zin.read(item.filename)
            zout.writestr(item, content)
    tmp.replace(xlsx)
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"{len(changes)} cellen bijgewerkt. Backup in {backup}/.")


if __name__ == "__main__":
    main()
