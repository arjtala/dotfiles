#!/usr/bin/env python3
"""The coding agents running on this machine and what each is doing.

    agent_registry.py       print what it found, to debug

Shared by SketchyBar (plugins/agents.py) and Waybar (scripts/agents.py,
through scripts/agent_registry.py, a symlink to this file), so both bars
read the agents the same way.

Every agent is one of three states:
    working   it is running a turn
    waiting   it is blocked on you: a permission prompt or a dialog
    idle      neither; its session is open, waiting for a next prompt
and the bar shows one for them all: waiting if any agent is, else working
if any is, else sleeping.  Waiting comes first because it is the one that
needs you.

Three harnesses, each read where it already publishes itself:
    Claude Code  ~/.claude/sessions/<pid>.json, written by Claude itself
                 with `status' busy, waiting or idle.  Only `cli' sessions
                 carry a status; SDK ones (agent-shell) are listed without.
    Pi           ~/.pi/agent/registry/<pid>.json, written by the
                 agent-muster-registry extension in the same words.
    Codex        no registry of its own: a running `codex' process, which
                 counts as working while it is writing a rollout under
                 ~/.codex/sessions.  It cannot tell waiting from idle.
A file outlives a crash, so an entry counts only while its pid is running
and, where the file records it, started when the file says it did; a
recycled pid is a different process.  Nothing here writes anything.

Runs under whichever python3 the bar's PATH finds, which may be the
system's 3.9, so nothing newer than 3.9 is used.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HOME = Path.home()
CLAUDE_SESSIONS = Path(os.environ.get('CLAUDE_CONFIG_DIR') or HOME / '.claude') / 'sessions'
PI_REGISTRY = Path(os.environ.get('PI_CODING_AGENT_DIR') or HOME / '.pi/agent') / 'registry'
CODEX_SESSIONS = Path(os.environ.get('CODEX_HOME') or HOME / '.codex') / 'sessions'
# Claude's and Pi's words for a session's status.  Anything else is no
# status at all, rather than a guess.
STATUSES = {'busy': 'working', 'waiting': 'waiting', 'idle': 'idle'}
ORDER = ['waiting', 'working', 'idle', None]  # how the list is sorted
START_SLACK = 3  # seconds a recorded start may differ from the process's
CODEX_ACTIVE = 10  # seconds since a rollout was written that count as working
# The native binary, as Homebrew installs it or npm's wrapper starts it.
CODEX_COMMAND = re.compile(r'^codex(-[a-z0-9_]+-(apple-darwin|unknown-linux-(gnu|musl)))?$')
LSTART = '%a %b %d %H:%M:%S %Y'  # `ps -o lstart', in the C locale


# ---- Pure parts, covered by sketchybar/tests/test_agents.py ----

def parse_processes(text):
    """Return {pid: {ppid, start, command}} from `ps -axo pid=,ppid=,lstart=,args=' TEXT.

    START is epoch seconds, from local time; COMMAND the basename of the
    first word of the command line.
    """
    table = {}
    for line in text.splitlines():
        parts = line.split(None, 7)
        if len(parts) < 7:
            continue
        try:
            pid, ppid = int(parts[0]), int(parts[1])
            start = time.mktime(time.strptime(' '.join(parts[2:7]), LSTART))
        except ValueError:
            continue
        args = parts[7] if len(parts) > 7 else ''
        command = os.path.basename(args.split()[0]) if args.split() else ''
        table[pid] = {'ppid': ppid, 'start': start, 'command': command}
    return table


def started_as_recorded(process, recorded):
    """Return whether PROCESS started at RECORDED epoch seconds, or RECORDED is unknown."""
    return recorded is None or abs(process['start'] - recorded) <= START_SLACK


def claude_start(value):
    """Return Claude's `procStart', a UTC date like `Fri Oct 23 16:52:32 2026', as epoch seconds."""
    try:
        return datetime.strptime(value, LSTART).replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


def milliseconds(value):
    return value / 1000 if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def text(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def claude_agent(data, processes):
    """Return the agent Claude's session file DATA describes, or None if it is not running."""
    pid = data.get('pid')
    process = processes.get(pid) if isinstance(pid, int) else None
    if process is None or not started_as_recorded(process, claude_start(data.get('procStart'))):
        return None
    # SDK sessions never update their status; only the CLI's means anything.
    status = STATUSES.get(data.get('status')) if data.get('entrypoint') == 'cli' else None
    return {'harness': 'Claude', 'pid': pid, 'cwd': text(data.get('cwd')),
            'name': text(data.get('name')), 'state': status, 'detail': None,
            'since': milliseconds(data.get('statusUpdatedAt') or data.get('updatedAt'))}


def pi_agent(data, processes):
    """Return the agent Pi's registry file DATA describes, or None if it is not running."""
    pid = data.get('pid')
    process = processes.get(pid) if isinstance(pid, int) else None
    if (data.get('version') != 1 or process is None
            or not started_as_recorded(process, milliseconds(data.get('procStart')))):
        return None
    return {'harness': 'Pi', 'pid': pid, 'cwd': text(data.get('cwd')),
            'name': text(data.get('name')) or text(data.get('title')),
            'state': STATUSES.get(data.get('status')), 'detail': text(data.get('waitingFor')),
            'since': milliseconds(data.get('updatedAt'))}


def codex_processes(processes):
    """Return the pids of PROCESSES that are Codex sessions, one per session.

    npm's `codex' is a node script that starts the native binary, so only
    the binary is matched, and a Codex started by another is the first's.
    """
    found = {pid for pid, process in processes.items() if CODEX_COMMAND.match(process['command'])}
    return sorted(pid for pid in found if processes[pid]['ppid'] not in found)


def codex_agent(pid, process, cwd, rollouts, now):
    """Return the agent for Codex process PID, which runs in CWD.

    ROLLOUTS is [(mtime, cwd)] for recent rollout files.  The newest one
    for CWD written since the process started says whether it is working.
    """
    written = [mtime for mtime, where in rollouts
               if mtime >= process['start'] - START_SLACK and (cwd is None or where == cwd)]
    last = max(written, default=None)
    working = last is not None and now - last <= CODEX_ACTIVE
    return {'harness': 'Codex', 'pid': pid, 'cwd': cwd, 'name': None,
            'state': 'working' if working else 'idle', 'detail': None, 'since': last}


def label(agent):
    """Return the name to show for AGENT: its own, else its directory's, else its pid."""
    if agent['name']:
        return agent['name']
    if agent['cwd']:
        return os.path.basename(agent['cwd'].rstrip('/')) or agent['cwd']
    return f"pid {agent['pid']}"


def overall(agents):
    """Return the bar's state for AGENTS: waiting, working or sleeping."""
    states = {agent['state'] for agent in agents}
    return 'waiting' if 'waiting' in states else 'working' if 'working' in states else 'sleeping'


def ordered(agents):
    """Return AGENTS with the ones needing you first, then by harness and name."""
    return sorted(agents, key=lambda a: (ORDER.index(a['state']), a['harness'], label(a).lower()))


def counts(agents):
    """Return a summary like `1 waiting · 2 working · 1 idle', or `none running'."""
    parts = []
    for state in ORDER:
        number = sum(1 for agent in agents if agent['state'] == state)
        if number:
            parts.append(f"{number} {state or 'unknown'}")
    return ' · '.join(parts) or 'none running'


# ---- The process table and the files ----

def process_table():
    try:
        done = subprocess.run(['ps', '-axo', 'pid=,ppid=,lstart=,args='], capture_output=True,
                              text=True, timeout=5, env={**os.environ, 'LC_ALL': 'C'})
    except (OSError, subprocess.TimeoutExpired):
        return {}
    return parse_processes(done.stdout)


def read_json(path):
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def registry(directory, reader, processes):
    agents = []
    # Only `.json': Claude keeps a `.key' file per session beside each one.
    for path in sorted(directory.glob('*.json')) if directory.is_dir() else []:
        data = read_json(path)
        agent = data and reader(data, processes)
        if agent:
            agents.append(agent)
    return agents


def process_cwd(pid):
    proc = Path(f'/proc/{pid}/cwd')
    if proc.exists():
        try:
            return os.readlink(proc)
        except OSError:
            return None
    try:
        done = subprocess.run(['lsof', '-a', '-p', str(pid), '-d', 'cwd', '-Fn'],
                              capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return next((line[1:] for line in done.stdout.splitlines() if line.startswith('n')), None)


def rollout_cwd(path):
    """Return the cwd from a rollout's first line, its session_meta, or None."""
    try:
        with open(path) as handle:
            first = json.loads(handle.readline())
    except (OSError, ValueError):
        return None
    payload = first.get('payload') if isinstance(first, dict) else None
    return text(payload.get('cwd')) if isinstance(payload, dict) else None


def recent_rollouts(since):
    """Return [(mtime, cwd)] for rollouts written since SINCE.  They are filed
    by the day they began, so a long session's may be in an older folder."""
    found = []
    for path in CODEX_SESSIONS.glob('*/*/*/rollout-*.jsonl') if CODEX_SESSIONS.is_dir() else []:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime >= since:
            found.append((mtime, rollout_cwd(path)))
    return found


def codex(processes, now):
    pids = codex_processes(processes)
    if not pids:
        return []
    rollouts = recent_rollouts(min(processes[pid]['start'] for pid in pids) - START_SLACK)
    return [codex_agent(pid, processes[pid], process_cwd(pid), rollouts, now) for pid in pids]


def collect():
    """Return every running agent, the ones needing you first."""
    processes, now = process_table(), time.time()
    agents = (registry(CLAUDE_SESSIONS, claude_agent, processes)
              + registry(PI_REGISTRY, pi_agent, processes)
              + codex(processes, now))
    return ordered(agents)


def main():
    agents = collect()
    print(f'{overall(agents)}: {counts(agents)}')
    for agent in agents:
        detail = f"  ({agent['detail']})" if agent['detail'] else ''
        print(f"  {agent['harness']:<7}{label(agent):<24}{agent['state'] or '-':<9}"
              f"pid {agent['pid']:<7}{agent['cwd'] or ''}{detail}")


if __name__ == '__main__':
    sys.exit(main())
