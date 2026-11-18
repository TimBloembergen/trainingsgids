#!/bin/sh
# Render debug/<id>.html to debug/<id>.png with headless Chrome. Usage: tools/shoot.sh id...
cd "$(dirname "$0")/.."
for id in "$@"; do
  google-chrome --headless=new --disable-gpu --hide-scrollbars --window-size=1000,470 \
    --screenshot="debug/$id.png" "file://$PWD/debug/$id.html" >/dev/null 2>&1
done
