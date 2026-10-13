#!/bin/sh
# spotify_player's player_event_hook_command: it runs this on every player
# event (Changed, Playing, Paused, EndOfTrack) with the event's details as
# arguments, which are not needed: plugins/spotify.py reads the playback
# afresh on spotify_update.
SKETCHYBAR=$(command -v sketchybar || echo /opt/homebrew/bin/sketchybar)
exec "$SKETCHYBAR" --trigger spotify_update
