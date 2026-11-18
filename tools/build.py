#!/usr/bin/env python3
"""Build index.html from src/template.html and the exercise animations.

    python3 tools/build.py          # writes index.html
    python3 tools/build.py --debug  # also writes debug.html with still frames per exercise
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from rig import build  # noqa: E402
from exercises import EXERCISES, BY_ID  # noqa: E402
from training import rest_badge, log_block  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def anim_box(ex, svg):
    return (f'<label class="anim-box">\n'
            f'                <input type="checkbox" class="pause" aria-label="Animatie {ex["caption"]} pauzeren">\n'
            f'                <span class="anim-state" aria-hidden="true"></span>\n'
            f'                {svg}\n'
            f'                <span class="anim-label">{ex["caption"]}</span>\n'
            f'                <span class="anim-tempo">Tempo: {ex["tempo"]}</span>\n'
            f'            </label>')


def main():
    template = (ROOT / "src" / "template.html").read_text()
    css_all = []

    def fill(m):
        ex = BY_ID[m.group(1)]
        svg, css = build(ex)
        css_all.append(css)
        return anim_box(ex, svg)

    names = {m.group(1): re.sub(r"^\d+\.\s*", "", m.group(2))
             for m in re.finditer(r"\{\{anim:([a-z0-9-]+)\}\}.*?<h3>(.*?)</h3>", template, re.S)}
    html = re.sub(r"\{\{anim:([a-z0-9-]+)\}\}", fill, template)
    html = re.sub(r"\{\{rest:([a-z0-9-]+)\}\}", lambda m: rest_badge(m.group(1)), html)
    html = re.sub(r"\{\{log:([a-z0-9-]+)\}\}", lambda m: log_block(m.group(1), names[m.group(1)]), html)
    html = html.replace("/*{{keyframes}}*/", "\n".join(css_all))
    (ROOT / "index.html").write_text(html)
    print(f"index.html: {len(html) / 1024:.0f} KB, {len(css_all)} animations")

    if "--debug" in sys.argv:
        from rig import sample
        style = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
        out = ROOT / "debug"
        out.mkdir(exist_ok=True)
        for ex in EXERCISES:
            total, frames, _, _ = sample(ex)
            n = len(frames) - 1
            cells = "".join(f'<div class="cell">{build(ex, round(n * i / 8))[0]}<small>{total * i / 8:.1f}s</small></div>'
                            for i in range(8))
            (out / f'{ex["id"]}.html').write_text(
                f'<!doctype html><meta charset="utf-8"><style>{style}'
                '.row{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;padding:4px}'
                '.cell{background:var(--stage);border:1px solid var(--border);text-align:center}'
                f'</style><body><div class="row">{cells}</div>')
        print("debug/*.html written")


if __name__ == "__main__":
    main()
