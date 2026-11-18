# Trainingsgids

4-day Upper / Lower split with dumbbells and an adjustable bench, with exercise animations and instructions (in Dutch).

View it on GitHub Pages: https://timbloembergen.github.io/trainingsgids/

## How it is built

`index.html` is generated. Do not edit it by hand.

- `src/template.html`: the page text and styles, with an `{{anim:<id>}}` placeholder per exercise.
- `tools/exercises.py`: the key poses, tempo and highlighted muscles of each exercise.
- `tools/rig.py`: the figure (shapes, joints, inverse kinematics) and the SVG/CSS output.

```bash
python3 tools/build.py            # writes index.html
python3 tools/build.py --debug    # also writes debug/<id>.html with still frames
tools/shoot.sh <id> ...           # renders debug/<id>.png with headless Chrome
```

The animations are plain SVG with CSS keyframes, without JavaScript, so the page also works offline and in the iOS Files preview. Tap an animation to pause it. With "reduce motion" turned on, animations start paused.

## Logbook and spreadsheet

The guide keeps a per-set logbook in the browser (localStorage) and can export it as CSV. That export is leading: `tools/update_sheet.py` writes it into the Week columns of the training spreadsheet.

```bash
python3 tools/update_sheet.py              # newest trainingslogboek-*.csv from private/ or ~/Downloads
python3 tools/update_sheet.py --dry-run    # show the changes without saving
```

The spreadsheet, its backups and the week mapping live in `private/`, which is not in git.
