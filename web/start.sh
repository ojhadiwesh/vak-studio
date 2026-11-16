#!/bin/sh
# Container entry point (Dockerfile CMD). With a volume (Railway sets RAILWAY_VOLUME_MOUNT_PATH; else VAK_DATA), the
# film library, art pieces, studio films and jobs live there and survive redeploys; the first boot fills it from the
# seed archive in Supabase Storage, and every boot adds new extra packs (python -m web.seed pull).
set -e
cd /app
DATA="${RAILWAY_VOLUME_MOUNT_PATH:-${VAK_DATA:-}}"
if [ -n "$DATA" ]; then
  mkdir -p "$DATA/chants" "$DATA/art" "$DATA/web_data"
  for pair in "chants:$DATA/chants" "art:$DATA/art" "web/data:$DATA/web_data"; do
    src="${pair%%:*}"; dst="${pair#*:}"
    if [ ! -L "$src" ]; then
      [ -d "$src" ] && cp -an "$src/." "$dst/" 2>/dev/null || true    # anything baked into the image moves to the volume once
      rm -rf "$src"; ln -s "$dst" "$src"
    fi
  done
  if [ "${VAK_SEED:-1}" != "0" ]; then                # the base pack on first boot, then any new extra packs
    python -m web.seed pull "$DATA" || echo "seed: skipped (the Studio starts with what is on the volume)"
  fi
fi
exec python -m web --no-browser
