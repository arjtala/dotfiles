#!/usr/bin/env python3
"""Apple Claude Code's spend meter, for the tokens item.

    tokens.py update     the item's script
    tokens.py toggle     its click: the popup
    tokens.py status     print what it found and draw nothing, to debug

The bar shows today's spend and how much of the budget that is, as Claude
Code's own status line does -- `Today: $227.65 of $300 · 76% used' -- in a
colour that moves from green to red as the budget runs down.  The popup adds
the tokens, the calls, the rate limit, when the budget resets, and the model
that cost most.

The numbers come from the quota API of Apple Claude Code's local proxy, the
one that status line asks.  Each running session has a proxy, which writes
~/.claude/apple/logs/acc-port-<port>.pid.  The item is drawn only while one
of those processes is alive and answering on loopback, and is hidden the rest
of the time, so with no session running the bar is as if it were not there.
The proxies can differ by a few dollars, so the largest spend is shown: a
meter against a cap should not under-report.  Nothing is written to ~/.claude.

Runs under whichever python3 SketchyBar's PATH finds, which may be the
system's 3.9, so nothing newer than 3.9 is used.
"""
from datetime import datetime, timezone
import http.client
import json
import math
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import popup as p  # noqa: E402  (shares the popups' helpers and layout)

ITEM = p.TOKENS
LOGS = Path.home() / '.claude/apple/logs'
TIMEOUT = 1.5  # seconds a proxy has to answer; it is on loopback
ICON = '\U000F029A'  # Nerd Font: md-gauge
# Palette colour by share of the budget spent: the first row at or below it.
LEVELS = ((90, 'BR_RED'), (75, 'BR_ORANGE'), (50, 'BR_YELLOW'), (0, 'BR_GREEN'))
WIDTH = 34  # characters across the popup
LABEL_WIDTH = math.ceil(WIDTH * p.CHAR) + 2
ROWS = ['today', 'tokens', 'calls', 'limit', 'resets', 'model']


# ---- Pure parts, covered by sketchybar/tests/test_tokens.py ----

def pid_alive(pid):
    """Return whether process PID exists (it need not be ours)."""
    if pid < 2:  # 0 and -1 would signal whole groups
        return False
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def pid_files(directory=LOGS):
    """Return (port, pid, written) for each proxy pid file in DIRECTORY."""
    found = []
    try:
        entries = list(directory.glob('acc-port-*.pid'))
    except OSError:
        return found
    for entry in entries:
        match = re.fullmatch(r'acc-port-(\d+)\.pid', entry.name)
        if not match or not 0 < int(match.group(1)) < 65536:
            continue
        try:
            found.append((int(match.group(1)), int(entry.read_text().strip()),
                          entry.stat().st_mtime))
        except (OSError, ValueError):
            continue
    return found


def instances(directory=LOGS, alive=pid_alive):
    """Return the ports of the proxies whose process is alive, newest first."""
    live = [(written, port) for port, pid, written in pid_files(directory) if alive(pid)]
    return [port for _, port in sorted(live, reverse=True)]


def number(value):
    """Return VALUE as a finite float, or None if it is not a number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def percent(part, whole):
    """Return PART as a whole-number percentage of WHOLE, halves rounded up."""
    return int(100 * part / whole + 0.5)


def model_name(model_id):
    """Return a model id such as `aws:anthropic.claude-opus-5-5' as `Opus 5.5'."""
    match = re.search(r'claude-(opus|sonnet|haiku)-(\d+)(?:-(\d{1,2})(?!\d))?', model_id)
    if not match:
        return model_id.rsplit('.', 1)[-1]
    family, major, minor = match.groups()
    return f"{family.title()} {major}{'.' + minor if minor else ''}"


def top_model(by_model):
    """Return the model that cost most as {name, spend, share}, or None."""
    if not isinstance(by_model, dict):
        return None
    costs = {}
    for model_id, entry in by_model.items():
        spend = number(entry.get('spend')) if isinstance(entry, dict) else None
        if spend is not None and spend > 0:
            costs[model_id] = spend
    if not costs:
        return None
    best = max(costs, key=costs.get)
    return {'name': model_name(best), 'spend': costs[best],
            'share': percent(costs[best], sum(costs.values()))}


def parse(data):
    """Return the meter from the reply DATA of /api/quota as a flat dict, or None."""
    if not isinstance(data, dict) or data.get('status') != 'success':
        return None
    quota = data.get('quota')
    if not isinstance(quota, dict):
        return None
    usage, limits = quota.get('usage') or {}, quota.get('limits') or {}
    given, rate = quota.get('percentages') or {}, quota.get('rateLimit') or {}
    spend, budget = number(usage.get('spend')), number(limits.get('budgetSpend'))
    if spend is None or not budget or budget <= 0:
        return None  # nothing to measure against
    sent, received = number(usage.get('inputTokens')), number(usage.get('outputTokens'))
    tokens = int(sent + received) if sent is not None and received is not None else None
    token_limit = number(limits.get('rateTokens'))
    token_percent = number(given.get('tokensUsed'))
    if token_percent is None and tokens is not None and token_limit:
        token_percent = percent(tokens, token_limit)
    resets = None
    if isinstance(quota.get('budgetResetTime'), str):
        try:
            resets = datetime.fromisoformat(quota['budgetResetTime'].replace('Z', '+00:00'))
        except ValueError:
            resets = None
        if resets is not None and resets.tzinfo is None:
            resets = resets.replace(tzinfo=timezone.utc)
    calls = number(usage.get('calls'))
    remaining, allowed, window = (number(rate.get(key)) for key in ('remaining', 'limit', 'windowSeconds'))
    return {
        'spend': spend, 'budget': budget, 'percent': percent(spend, budget),
        'tokens': tokens, 'token_limit': token_limit,
        'token_percent': None if token_percent is None else int(token_percent),
        'calls': None if calls is None else int(calls),
        'rate_remaining': None if remaining is None else int(remaining),
        'rate_limit': None if allowed is None else int(allowed),
        'rate_window': None if window is None else int(window),
        'resets': resets, 'model': top_model(quota.get('usageByModel')),
    }


def dollars(amount, cents=False):
    """Return AMOUNT as $228, or $227.65 with CENTS."""
    return f'${amount:,.2f}' if cents else f'${amount:,.0f}'


def compact(count):
    """Return COUNT as 999, 1.2K, 34K, 297M or 1.0B."""
    value, units, index = float(count), ['', 'K', 'M', 'B'], 0
    while value >= 999.95 and index < len(units) - 1:
        value /= 1000
        index += 1
    if index == 0:
        return str(int(value))
    return f'{value:.1f}{units[index]}' if value < 9.95 else f'{value:.0f}{units[index]}'


def until(moment, now):
    """Return the time from NOW to MOMENT as `15h 03m', `42m' or `<1m'."""
    seconds = max(0, int((moment - now).total_seconds()))
    hours, minutes = divmod(seconds // 60, 60)
    if hours:
        return f'{hours}h {minutes:02}m'
    return f'{minutes}m' if minutes else '<1m'


def level(share):
    """Return the palette colour name for SHARE percent of the budget spent."""
    return next(name for floor, name in LEVELS if share >= floor)


def clip(text, length):
    """Return TEXT cut to LENGTH characters, ending in an ellipsis if cut."""
    return text if len(text) <= length else text[:length - 1].rstrip() + '…'


def bar_label(meter):
    return f"{dollars(meter['spend'])} · {meter['percent']}%"


def popup_rows(meter, now):
    """Return the popup's rows as (item name, text or None, palette colour).
    A row with no text is hidden: the proxy did not report it."""
    whole = meter['budget'] == int(meter['budget'])
    rows = [('today', f"Today   {dollars(meter['spend'], True)} of "
                      f"{dollars(meter['budget'], not whole)} · {meter['percent']}%",
             level(meter['percent']))]
    tokens = None
    if meter['tokens'] is not None:
        tokens = f"Tokens  {compact(meter['tokens'])}"
        if meter['token_limit']:
            tokens += f" of {compact(meter['token_limit'])}"
        if meter['token_percent'] is not None:
            tokens += f" · {meter['token_percent']}%"
    rows.append(('tokens', tokens, 'FG'))
    rows.append(('calls', None if meter['calls'] is None else f"Calls   {meter['calls']:,}", 'FG'))
    limit = None
    if meter['rate_remaining'] is not None and meter['rate_limit']:
        limit = f"Limit   {meter['rate_remaining']} of {meter['rate_limit']}"
        if meter['rate_window']:
            limit += f" per {meter['rate_window'] / 60:g} min"
    rows.append(('limit', limit, 'FG'))
    resets = None
    if meter['resets'] is not None:
        resets = f"Resets  in {until(meter['resets'], now)} · {meter['resets'].astimezone():%H:%M}"
    rows.append(('resets', resets, 'FG'))
    model = meter['model']
    rows.append(('model', None if model is None else
                 f"Model   {model['name']} {dollars(model['spend'])} · {model['share']}%", 'FG2'))
    return [(name, text and clip(text, WIDTH), color) for name, text, color in rows]


# ---- The proxies and SketchyBar ----

def fetch(port, timeout=TIMEOUT):
    """Return the proxy on PORT's /api/quota reply as parsed JSON, or None."""
    # An empty ProxyHandler: this is loopback, whatever HTTP_PROXY says.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f'http://127.0.0.1:{port}/api/quota', timeout=timeout) as reply:
            return json.loads(reply.read(1 << 20))
    except urllib.error.HTTPError as error:  # a status line, not a reply: close its body
        error.close()
        return None
    except (OSError, ValueError, http.client.HTTPException):
        return None


def read():
    """Return the meter from the live proxy that reports the most spend, or None."""
    meters = [meter for meter in (parse(fetch(port)) for port in instances()) if meter]
    return max(meters, key=lambda meter: meter['spend'], default=None)


def utcnow():
    return datetime.now(timezone.utc)


def create():
    palette = p.colors()
    args = ['--remove', f'/{ITEM}\\.i\\..*/',
            '--set', ITEM, 'popup.align=right', f'popup.background.color={palette["BG1"]}',
            f'popup.background.corner_radius={p.RADIUS}', 'popup.background.border_width=0']
    for name in ROWS:
        item = f'{ITEM}.i.{name}'
        args += ['--add', 'item', item, f'popup.{ITEM}',
                 '--set', item, 'icon.drawing=off', f'label.width={LABEL_WIDTH}',
                 f'label.padding_left={p.LABEL_PAD}', 'label.padding_right=0',
                 f'padding_left={p.PAD}', f'padding_right={p.PAD}']
    p.bar(*args)


def render(meter, popup_open, now):
    palette = p.colors()
    if meter is None:  # no live proxy: not drawn, and no popup left open
        p.bar('--set', ITEM, 'drawing=off', 'popup.drawing=off')
        return
    color = palette[level(meter['percent'])]
    args = ['--set', ITEM, 'drawing=on', f'icon={ICON}', f'label={bar_label(meter)}',
            f'icon.color={color}', f'label.color={color}']
    if popup_open:
        for name, text, row_color in popup_rows(meter, now):
            item = f'{ITEM}.i.{name}'
            args += p.show(item, text, palette[row_color]) if text else p.hide(item)
    p.bar(*args)


def update():
    if os.environ.get('SENDER') == 'mouse.exited.global':
        p.close(ITEM)
        return
    meter = read()
    render(meter, meter is not None and p.is_open(ITEM), utcnow())


def toggle():
    p.toggle(ITEM, create, lambda: render(read(), True, utcnow()))


def status():
    files = pid_files()
    print(f'{LOGS}/acc-port-*.pid: {len(files)} file(s)')
    for port, pid, _ in sorted(files):
        state = 'alive' if pid_alive(pid) else 'not running'
        reply = parse(fetch(port)) if state == 'alive' else None
        shown = bar_label(reply) if reply else ('no usable answer' if state == 'alive' else '-')
        print(f'  :{port}  pid {pid}  {state}  {shown}')
    meter = read()
    print('the item shows:', bar_label(meter) if meter else 'nothing; it is hidden')


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'update'
    if action == 'update':
        update()
    elif action == 'toggle':
        toggle()
    elif action == 'status':
        status()


if __name__ == '__main__':
    main()
