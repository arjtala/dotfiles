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
    Codex        running `codex' processes and their open rollout files.
                 Turn lifecycle events keep a session working until its
                 turn and its subagents finish, even while logs are quiet.
                 It cannot identify permission prompts as waiting.
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
# Claude's and Pi's words for a session's status.  Anything else is no
# status at all, rather than a guess.
STATUSES = {'busy': 'working', 'waiting': 'waiting', 'idle': 'idle'}
ORDER = ['waiting', 'working', 'idle', None]  # how the list is sorted
START_SLACK = 3  # seconds a recorded start may differ from the process's
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


def codex_agent(pid, cwd, rollouts):
    """Summarize the rollouts owned by a live process, including its subagents.

    Ownership comes from open files, not directory names or write times.
    None means discovery failed; an unreadable rollout also has unknown state.
    """
    states = [r['state'] if r else None for r in rollouts] if rollouts is not None else [None]
    state = 'working' if 'working' in states else None if None in states else 'idle'
    active_children = sum(bool(r and r['parent'] and r['state'] == 'working')
                          for r in rollouts or [])
    last = max((r['since'] for r in rollouts or [] if r and r['since'] is not None), default=None)
    detail = (f'{active_children} active subagent' + ('s' if active_children != 1 else '')
              if active_children else None)
    return {'harness': 'Codex', 'pid': pid, 'cwd': cwd, 'name': None,
            'state': state, 'detail': detail, 'since': last}


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


def is_rollout(path):
    return path.name.startswith('rollout-') and path.suffix == '.jsonl'


def process_rollouts(pid):
    """Find the logs this process actually owns, including child-agent writers.

    /proc is available on Linux; macOS exposes the same open files via lsof.
    Returning None on failure avoids reporting a guessed idle state.
    """
    if sys.platform.startswith('linux'):
        try:
            paths = set()
            for fd in Path(f'/proc/{pid}/fd').iterdir():
                try:
                    path = Path(os.readlink(fd))
                except FileNotFoundError:  # a descriptor closed during the scan
                    continue
                if is_rollout(path):
                    paths.add(path)
            return sorted(paths)
        except OSError:
            return None
    try:
        done = subprocess.run(['lsof', '-a', '-p', str(pid), '-Fn'],
                              capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode:
        return None
    return sorted({Path(line[1:]) for line in done.stdout.splitlines()
                   if line.startswith('n') and is_rollout(Path(line[1:]))})


def reverse_lines(handle):
    """Read complete JSONL records backwards without loading the whole history.

    Ignore the unfinished final line while the Codex writer is appending it.
    """
    handle.seek(0, os.SEEK_END)
    position, pending, at_end = handle.tell(), b'', True
    while position:
        size = min(position, 65536)
        position -= size
        handle.seek(position)
        lines = (handle.read(size) + pending).split(b'\n')
        pending = lines[0]
        for line in reversed(lines[1:]):
            if at_end:
                at_end = False
            elif line:
                yield line
    if pending and not at_end:
        yield pending


def iso_timestamp(value):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except (AttributeError, TypeError, ValueError):
        return None


def read_rollout(path, process_start):
    """Read identity and the latest turn, ignoring copied and pre-restart turns.

    Child logs begin with their own metadata, followed by copied parent history
    (including more metadata). Only the first identity belongs to this file.
    started_at retains the original time even when copied records are restamped.
    """
    try:
        with path.open('rb') as handle:
            first = json.loads(handle.readline())
            meta = first.get('payload') if isinstance(first, dict) else None
            if not isinstance(meta, dict) or first.get('type') != 'session_meta':
                return None
            source = meta.get('source')
            subagent = source.get('subagent') if isinstance(source, dict) else None
            spawn = subagent.get('thread_spawn') if isinstance(subagent, dict) else None
            parent = text(spawn.get('parent_thread_id')) if isinstance(spawn, dict) else None
            result = {'id': text(meta.get('id')), 'parent': parent, 'cwd': text(meta.get('cwd')),
                      'state': None, 'since': None}
            born = iso_timestamp(meta.get('timestamp')) if parent else None
            cutoff = max(process_start - START_SLACK, int(born) if born is not None else 0)
            finished = set()
            for line in reverse_lines(handle):
                try:
                    record = json.loads(line)
                except (ValueError, UnicodeError):
                    continue
                if not isinstance(record, dict) or record.get('type') != 'event_msg':
                    continue
                event = record.get('payload')
                if not isinstance(event, dict):
                    continue
                kind = event.get('type')
                if kind not in ('task_started', 'task_complete', 'turn_aborted'):
                    continue
                timestamp = iso_timestamp(record.get('timestamp'))
                started = event.get('started_at')
                if not isinstance(started, (int, float)) or isinstance(started, bool):
                    started = timestamp
                # No new turn in this process (or only a child's copied history).
                if started is None or started < cutoff:
                    if kind == 'task_started':
                        result['state'] = 'idle'
                        return result
                    continue
                turn = text(event.get('turn_id'))
                if result['since'] is None:
                    result['since'] = timestamp
                if kind == 'task_started':
                    result['state'] = 'idle' if turn in finished or None in finished else 'working'
                    return result
                finished.add(turn)
            if finished:
                result['state'] = 'idle'
            return result
    except (OSError, ValueError, UnicodeError):
        return None


def codex(processes):
    agents = []
    for pid in codex_processes(processes):
        paths = process_rollouts(pid)
        rollouts = ([read_rollout(path, processes[pid]['start']) for path in paths]
                    if paths is not None else None)
        agents.append(codex_agent(pid, process_cwd(pid), rollouts))
    return agents


def collect():
    """Return every running agent, the ones needing you first."""
    processes = process_table()
    agents = (registry(CLAUDE_SESSIONS, claude_agent, processes)
              + registry(PI_REGISTRY, pi_agent, processes)
              + codex(processes))
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
