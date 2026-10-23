#!/usr/bin/env python3
"""Coding agents for the custom/agents module, and the rows of its popup.

One icon for every Claude, Pi and Codex session: a bell when any is waiting
for you, a robot when any is working, a sleeping face otherwise; the CSS
class is that state.  Click for each session (popup.py agents).  How
sessions are found is agent_registry.py's, shared with SketchyBar.
"""
import html
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_registry as registry  # noqa: E402

ICONS = {'waiting': '\U000F009E', 'working': '\U000F06A9', 'sleeping': '\U000F04B2'}


def row(agent):
    """Return AGENT's (harness, name, state, detail) for the popup and tooltip."""
    return (agent['harness'], registry.label(agent), agent['state'] or 'unknown',
            agent['detail'] or agent['cwd'] or '')


def bar_output(agents):
    state = registry.overall(agents)
    tooltip = [f'Agents · {registry.counts(agents)}']
    tooltip += [f'{harness}  {name}  {status}' for harness, name, status, _ in map(row, agents)]
    return {'text': ICONS[state], 'class': state, 'tooltip': html.escape('\n'.join(tooltip))}


if __name__ == '__main__':
    print(json.dumps(bar_output(registry.collect())))
