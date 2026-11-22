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

The home-screen icon (`apple-touch-icon.png`, `icon-192.png`, `icon-512.png`) is drawn by `python3 tools/icon.py` (needs Pillow); `manifest.webmanifest` names the app.

The animations are plain SVG with CSS keyframes, without JavaScript, so the page also works offline and in the iOS Files preview. Tap an animation to pause it. With "reduce motion" turned on, animations start paused.

## Logbook and Google Sheet

The guide keeps a per-set logbook in the browser (localStorage). The logbook is leading: it is written into the Week columns of the training tab in Google Sheets, which is the only copy outside the browser.

**Weeks:** each training goes to the Week column of its calendar week (Monday to Sunday). A training done up to 3 days after its planned day that already falls in the next week (Sunday's Day 4 on Monday) still counts for the previous week, as long as that week has no training of the exercise yet. Per exercise and week the latest training wins.

**Sync:** `tools/apps-script/Code.gs` runs as an Apps Script web app inside the Google Sheet. Run `setup()` once to create the code, deploy it as a web app (execute as me, access anyone) and enter the URL and code in the guide under Instellingen > Sync instellen. The guide then syncs when an exercise is finished, or with the Sync button. The URL and code are stored only in the browser, never in this repo.
