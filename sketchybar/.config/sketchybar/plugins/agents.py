#!/usr/bin/env python3
"""The coding agents running on this machine, for the agents item.

    agents.py update     the item's script
    agents.py toggle     its click: the popup

The bar shows one icon for every Claude, Pi and Codex session: an orange
bell when any is waiting for you, a yellow robot when any is working, and
a dim sleeping face when none is doing anything.  The popup lists each
session, the ones waiting first, with its harness, name and state.  What
counts as which state, and how sessions are found, is agent_registry.py's.

Runs under whichever python3 SketchyBar's PATH finds, which may be the
system's 3.9, so nothing newer than 3.9 is used.
"""
import math
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_registry as registry  # noqa: E402
import popup as p  # noqa: E402  (shares the popups' helpers and layout)

ITEM = p.AGENTS
MAX_AGENTS = 12  # popup rows for sessions; any more are counted in the last row
WIDTH = 56  # characters across the popup
LABEL_WIDTH = math.ceil(WIDTH * p.CHAR) + 2
NAME_WIDTH = 22
ROWS = ['title'] + [f'agent{i}' for i in range(MAX_AGENTS)] + ['more']
# State -> (Nerd Font glyph, palette colour name).  md-bell_ring, md-robot, md-sleep.
ICONS = {'waiting': ('\U000F009E', 'BR_ORANGE'),
         'working': ('\U000F06A9', 'BR_YELLOW'),
         'sleeping': ('\U000F04B2', 'FG2')}
STATE_COLORS = {'waiting': 'BR_ORANGE', 'working': 'BR_YELLOW', 'idle': 'FG', None: 'FG2'}
TOOLTIPS = {'waiting': 'An agent is waiting for you', 'working': 'Agents are working',
            'sleeping': 'No agent is doing anything'}


# ---- Pure parts, covered by sketchybar/tests/test_agents.py ----

def clip(text, length):
    """Return TEXT cut to LENGTH characters, ending in an ellipsis if cut."""
    return text if len(text) <= length else text[:length - 1].rstrip() + '…'


def agent_text(agent):
    """Return AGENT's popup row: harness, name and state in columns.
    A Pi dialog's title replaces the bare `waiting'."""
    state = agent['state'] or 'unknown'
    if agent['state'] == 'waiting' and agent['detail']:
        state = f"waiting · {agent['detail']}"
    name = clip(registry.label(agent), NAME_WIDTH)
    return clip(f"{agent['harness']:<7}{name:<{NAME_WIDTH + 1}}{state}", WIDTH)


def rows(agents):
    """Return the popup's rows as (item name, text or None, palette colour name).
    A row with no text is hidden."""
    shown = agents[:MAX_AGENTS]
    result = [('title', f'Agents · {registry.counts(agents)}', ICONS[registry.overall(agents)][1])]
    for index in range(MAX_AGENTS):
        agent = shown[index] if index < len(shown) else None
        result.append((f'agent{index}', agent and agent_text(agent),
                       STATE_COLORS[agent['state']] if agent else 'FG'))
    extra = len(agents) - len(shown)
    result.append(('more', extra and f'and {extra} more', 'FG2'))
    return result


# ---- SketchyBar ----

def create():
    palette = p.colors()
    args = ['--remove', f'/{ITEM}\\.i\\..*/',
            '--set', ITEM, 'popup.align=right', f'popup.background.color={palette["BG1"]}',
            f'popup.background.corner_radius={p.RADIUS}', 'popup.background.border_width=0']
    for name in ROWS:
        args += p.row_settings(f'{ITEM}.i.{name}', ITEM)
        args += ['--set', f'{ITEM}.i.{name}', f'label.width={LABEL_WIDTH}']
    p.bar(*args)


def render(agents, popup_open):
    palette = p.colors()
    state = registry.overall(agents)
    glyph, color = ICONS[state]
    args = ['--set', ITEM, f'icon={glyph}', f'icon.color={palette[color]}',
            'label.drawing=off', f'tooltip={TOOLTIPS[state]}']
    if popup_open:
        bold = 'JetBrainsMono Nerd Font:Bold:13.0'
        for name, text, key in rows(agents):
            item = f'{ITEM}.i.{name}'
            if not text:
                args += p.hide(item)
            else:
                extra = {'label.font': bold} if name == 'title' else {}
                args += p.show(item, text, palette[key], **extra)
    p.bar(*args)


def update():
    if os.environ.get('SENDER') == 'mouse.exited.global':
        p.close(ITEM)
        return
    render(registry.collect(), p.is_open(ITEM))


def toggle():
    p.toggle(ITEM, create, lambda: render(registry.collect(), True))


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'update'
    {'update': update, 'toggle': toggle}[action]()


if __name__ == '__main__':
    main()
