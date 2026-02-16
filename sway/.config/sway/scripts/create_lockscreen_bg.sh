#!/bin/env bash
# Make bash more sane
set -euo pipefail

WALLPAPERS="$HOME/.wallpapers/"

magick convert \
   -filter Gaussian \
   -blur 0x25.0 \
   $WALLPAPERS/lock.jpg $WALLPAPERS/lock1.jpg
