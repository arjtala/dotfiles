import fcntl
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

PLUGINS = Path(__file__).resolve().parents[1] / '.config/sketchybar/plugins'
sys.path.insert(0, str(PLUGINS))
spec = importlib.util.spec_from_file_location('tailscale', PLUGINS / 'tailscale.py')
tailscale = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tailscale)

# `scutil --nc list' as macOS prints it, with the Tailscale line's state filled in.
LIST = '''Available network connection services in the current set (*=enabled):
  (Invalid)        11111111-2222-3333-4444-555555555555 VPN (com.apple.example.ikev2) "Corporate (IKEv2)"              [VPN:com.apple.example.ikev2]
* (Disconnected)   22222222-3333-4444-5555-666666666666 VPN (com.apple.example.anyconnect) "Corporate"                      [VPN:com.apple.example.anyconnect]
* ({state})   33333333-4444-5555-6666-777777777777 VPN (io.tailscale.ipn.macsys) "Tailscale"                      [VPN:io.tailscale.ipn.macsys]
'''

# `tailscale status --json', shaped like the real one, with invented machines.
SELF = {'HostName': "Test's MacBook", 'DNSName': 'testbook.example.ts.net.',
        'TailscaleIPs': ['100.64.0.1', 'fd7a:115c:a1e0::1'], 'Online': True, 'OS': 'macOS'}
PEERS = {
    'nodekey:aa': {'HostName': 'nas', 'DNSName': 'nas.example.ts.net.', 'TailscaleIPs': ['100.64.0.2'],
                   'Online': True, 'ExitNode': False, 'ExitNodeOption': False},
    'nodekey:bb': {'HostName': 'phone', 'DNSName': 'phone.example.ts.net.', 'TailscaleIPs': ['100.64.0.3'],
                   'Online': False},
    'nodekey:cc': {'HostName': 'gateway', 'DNSName': 'gateway.example.ts.net.', 'TailscaleIPs': ['100.64.0.4'],
                   'Online': True, 'ExitNode': False, 'ExitNodeOption': True},
}
RUNNING = {'Version': '1.80.0', 'BackendState': 'Running', 'AuthURL': '', 'Health': [],
           'TailscaleIPs': ['100.64.0.1', 'fd7a:115c:a1e0::1'], 'Self': SELF, 'MagicDNSSuffix': 'example.ts.net',
           'CurrentTailnet': {'Name': 'tester@example.com', 'MagicDNSSuffix': 'example.ts.net',
                              'MagicDNSEnabled': True},
           'Peer': PEERS}
STOPPED = {'Version': '1.80.0', 'BackendState': 'Stopped', 'Health': ['Tailscale is stopped.']}
NEEDS_LOGIN = {'BackendState': 'NeedsLogin', 'AuthURL': 'https://login.example.com/a/abc123'}


def with_exit_node():
    data = json.loads(json.dumps(RUNNING))
    data['Peer']['nodekey:cc']['ExitNode'] = True
    data['ExitNodeStatus'] = {'ID': 'n1', 'Online': True, 'TailscaleIPs': ['100.64.0.4/32']}
    return data


def snapshot(data=None, state=None):
    """What `take' returns, built from a status DATA and a VPN list STATE."""
    summary = tailscale.summarize(data) if data else None
    service = {'state': state, 'name': 'Tailscale'} if state else None
    kind, headline = tailscale.resolve(service, summary)
    return {'kind': kind, 'headline': headline, 'summary': summary, 'service': service, 'cli': '/fake/tailscale'}


class ServiceTests(unittest.TestCase):
    def test_tailscale_is_found_among_other_vpns(self):
        self.assertEqual(tailscale.tailscale_service(LIST.format(state='Disconnected')),
                         {'state': 'Disconnected', 'name': 'Tailscale'})

    def test_every_state_is_read(self):
        for state in ('Connected', 'Connecting', 'Reasserting', 'Disconnecting', 'Disconnected', 'Invalid'):
            self.assertEqual(tailscale.tailscale_service(LIST.format(state=state))['state'], state)

    def test_other_vpns_alone_are_not_tailscale(self):
        text = '\n'.join(LIST.format(state='Connected').splitlines()[:3])
        self.assertIsNone(tailscale.tailscale_service(text))

    def test_the_app_store_build_is_found_too_and_a_name_may_have_brackets(self):
        text = LIST.format(state='Connected').replace('io.tailscale.ipn.macsys', 'io.tailscale.ipn.macos') \
                                             .replace('"Tailscale"', '"Tailscale (work)"')
        self.assertEqual(tailscale.tailscale_service(text), {'state': 'Connected', 'name': 'Tailscale (work)'})

    def test_rubbish_is_nothing(self):
        for text in ('', 'No services', '* (Connected) not-a-uuid VPN (io.tailscale.x) "T" [VPN:x]'):
            self.assertIsNone(tailscale.tailscale_service(text))


class SummaryTests(unittest.TestCase):
    def test_a_running_tailnet(self):
        summary = tailscale.summarize(RUNNING)
        self.assertEqual(summary['backend'], 'Running')
        self.assertEqual(summary['device'], 'testbook')            # the tailnet name, not "Test's MacBook"
        self.assertEqual(summary['ip'], '100.64.0.1')              # IPv4 before IPv6
        self.assertEqual(summary['tailnet'], 'tester@example.com')
        self.assertEqual((summary['peers'], summary['online']), (3, 2))
        self.assertIsNone(summary['exit'])
        self.assertEqual(summary['health'], [])
        self.assertIsNone(summary['auth_url'])

    def test_an_exit_node_in_use_is_named(self):
        self.assertEqual(tailscale.summarize(with_exit_node())['exit'], {'name': 'gateway', 'online': True})

    def test_an_exit_node_without_a_peer_entry_is_named_by_address(self):
        data = with_exit_node()
        data['Peer'] = {}
        data['ExitNodeStatus']['Online'] = False
        self.assertEqual(tailscale.summarize(data)['exit'], {'name': '100.64.0.4', 'online': False})

    def test_stopped_has_little_to_say(self):
        summary = tailscale.summarize(STOPPED)
        self.assertEqual((summary['device'], summary['ip'], summary['tailnet'], summary['peers']), (None, None, None, 0))
        self.assertEqual(summary['health'], ['Tailscale is stopped.'])

    def test_a_login_page_is_kept(self):
        self.assertEqual(tailscale.summarize(NEEDS_LOGIN)['auth_url'], 'https://login.example.com/a/abc123')

    def test_fallbacks_for_the_tailnet_and_the_address(self):
        data = {'BackendState': 'Running', 'MagicDNSSuffix': 'x.ts.net', 'TailscaleIPs': ['100.64.9.9'], 'Self': {}}
        summary = tailscale.summarize(data)
        self.assertEqual((summary['tailnet'], summary['ip']), ('x.ts.net', '100.64.9.9'))

    def test_a_host_name_is_used_when_there_is_no_dns_name(self):
        self.assertEqual(tailscale.short_name({'HostName': 'plainhost'}), 'plainhost')
        self.assertIsNone(tailscale.short_name({}))

    def test_wrong_types_are_not_a_crash(self):
        data = {'BackendState': 'Running', 'Self': 'me', 'Peer': ['x'], 'Health': [1, 'ok', None],
                'CurrentTailnet': None, 'ExitNodeStatus': 5, 'TailscaleIPs': 'nope'}
        summary = tailscale.summarize(data)
        self.assertEqual((summary['peers'], summary['health'], summary['ip'], summary['exit']), (0, ['ok'], None, None))


class ResolveTests(unittest.TestCase):
    def kind(self, state, data):
        service = {'state': state, 'name': 'Tailscale'} if state else None
        return tailscale.resolve(service, tailscale.summarize(data) if data else None)

    def test_the_cli_decides_when_it_answers(self):
        self.assertEqual(self.kind(None, RUNNING), ('on', 'Connected'))
        self.assertEqual(self.kind('Disconnected', STOPPED), ('off', 'Off'))
        self.assertEqual(self.kind('Disconnected', RUNNING), ('on', 'Connected'))
        self.assertEqual(self.kind('Connected', NEEDS_LOGIN), ('login', 'Needs login'))
        self.assertEqual(self.kind(None, {'BackendState': 'NeedsMachineAuth'}), ('login', 'Waiting for approval'))
        self.assertEqual(self.kind(None, {'BackendState': 'Starting'}), ('busy', 'Starting…'))
        self.assertEqual(self.kind(None, {'BackendState': 'SomethingNew'}), ('busy', 'SomethingNew'))

    def test_the_vpn_list_decides_when_it_does_not(self):
        self.assertEqual(self.kind('Disconnected', None), ('off', 'Off'))
        self.assertEqual(self.kind('Invalid', None), ('off', 'Off'))
        self.assertEqual(self.kind('Connected', None), ('on', 'Connected'))
        self.assertEqual(self.kind('Connecting', None), ('busy', 'Connecting…'))
        self.assertEqual(self.kind('Disconnecting', None), ('busy', 'Turning off…'))

    def test_with_neither_tailscale_is_not_running(self):
        self.assertEqual(self.kind(None, None), ('down', 'Not running'))


class RowsTests(unittest.TestCase):
    def rows(self, snap, note=None):
        return {name: (text, color) for name, text, color in tailscale.rows(snap, note)}

    def test_connected(self):
        rows = self.rows(snapshot(RUNNING))
        self.assertEqual(rows['title'], ('Tailscale · Connected', 'BR_GREEN'))
        self.assertEqual(rows['switch'], ('\U000F0521  Turn off', 'BR_GREEN'))
        self.assertEqual(rows['device'][0], 'Device   testbook · 100.64.0.1')
        self.assertEqual(rows['tailnet'][0], 'Tailnet  tester@example.com')
        self.assertEqual(rows['exit'][0], 'Exit     none')
        self.assertEqual(rows['peers'][0], 'Peers    2 of 3 online')
        self.assertIsNone(rows['note'][0])
        self.assertEqual(rows['app'][0], 'Open Tailscale…')

    def test_an_exit_node_in_use(self):
        snap = snapshot(with_exit_node())
        self.assertEqual(self.rows(snap)['exit'][0], 'Exit     gateway')
        self.assertEqual(self.rows(snap)['title'][1], 'BR_AQUA')
        offline = with_exit_node()
        offline['Peer']['nodekey:cc']['Online'] = False
        self.assertEqual(self.rows(snapshot(offline))['exit'][0], 'Exit     gateway (offline)')

    def test_tailscale_complaints_show_when_connected(self):
        data = dict(RUNNING, Health=['The DNS is slow', 'another'])
        self.assertEqual(self.rows(snapshot(data))['note'], ('The DNS is slow', 'FG2'))

    def test_off_offers_the_switch_and_hides_the_rest(self):
        rows = self.rows(snapshot(STOPPED, 'Disconnected'))
        self.assertEqual(rows['title'], ('Tailscale · Off', 'FG2'))
        self.assertEqual(rows['switch'][0], '\U000F0522  Turn on')
        for name in ('device', 'tailnet', 'exit', 'peers', 'note', 'more'):
            self.assertIsNone(rows[name][0], name)       # "Tailscale is stopped." says nothing new
        self.assertEqual(rows['app'][0], 'Open Tailscale…')

    def test_off_with_no_answer_from_the_cli_looks_the_same(self):
        rows = self.rows(snapshot(None, 'Disconnected'))
        self.assertEqual(rows['switch'][0], '\U000F0522  Turn on')

    def test_login_and_not_running_open_the_app_instead(self):
        login = self.rows(snapshot(NEEDS_LOGIN))
        self.assertEqual((login['title'][0], login['switch'][0]), ('Tailscale · Needs login', '\U000F03CC  Log in…'))
        self.assertEqual(login['title'][1], 'BR_ORANGE')
        self.assertIsNone(login['app'][0])               # the switch row already does that
        down = self.rows(snapshot(None, None))
        self.assertEqual(down['switch'][0], '\U000F03CC  Open Tailscale')
        self.assertIsNone(down['app'][0])

    def test_starting_shows_progress(self):
        rows = self.rows(snapshot({'BackendState': 'Starting'}))
        self.assertEqual((rows['title'][0], rows['switch'][0]), ('Tailscale · Starting…', '\U000F0521  Starting…'))
        self.assertEqual(rows['title'][1], 'BR_YELLOW')

    def test_a_message_replaces_the_warning_and_is_orange(self):
        rows = self.rows(snapshot(dict(RUNNING, Health=['slow'])), note="Couldn't turn Tailscale off")
        self.assertEqual(rows['note'], ("Couldn't turn Tailscale off", 'BR_ORANGE'))

    def test_a_long_message_goes_on_over_a_second_row_and_the_second_is_clipped(self):
        one = self.rows(snapshot(RUNNING), note="Started, but the Tailscale command isn't answering")
        self.assertEqual((one['note'][0], one['more'][0]), ('Started, but the Tailscale command', "isn't answering"))
        self.assertEqual((one['note'][1], one['more'][1]), ('BR_ORANGE', 'BR_ORANGE'))
        huge = self.rows(snapshot(RUNNING), note='word ' * 40)
        self.assertLessEqual(len(huge['note'][0]), tailscale.WIDTH)
        self.assertTrue(huge['note'][0].endswith('word'))     # cut between words, not in one
        self.assertTrue(huge['more'][0].endswith('…'))
        self.assertLessEqual(len(huge['more'][0]), tailscale.WIDTH)
        warning = self.rows(snapshot(dict(RUNNING, Health=['A long warning from Tailscale about your DNS setup'])))
        self.assertEqual(warning['note'], ('A long warning from Tailscale', 'FG2'))
        self.assertEqual(warning['more'][0], 'about your DNS setup')
        self.assertIsNone(self.rows(snapshot(RUNNING))['more'][0])
        self.assertEqual(len(self.rows(snapshot(RUNNING), note='x' * 100)['note'][0]), tailscale.WIDTH)  # one long word

    def test_rows_match_the_ones_the_popup_creates_and_fit_in_it(self):
        long = dict(RUNNING, Health=['x' * 200], CurrentTailnet={'Name': 'n' * 100})
        long['Self'] = dict(SELF, DNSName='d' * 80 + '.ts.net.')
        for snap in (snapshot(long), snapshot(STOPPED, 'Disconnected'), snapshot(None, None)):
            result = tailscale.rows(snap, note='m' * 90)
            self.assertEqual([name for name, _, _ in result], tailscale.ROWS)
            for name, text, _ in result:
                self.assertLessEqual(len(text or ''), tailscale.WIDTH, name)


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        patcher = mock.patch.object(tailscale.p, 'bar', lambda *args: self.calls.append(list(args)))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.palette = tailscale.p.colors()

    def test_not_installed_means_hidden_with_no_popup(self):
        tailscale.render(None, False)
        self.assertEqual(self.calls, [['--set', 'tailscale', 'drawing=off', 'popup.drawing=off']])

    def test_the_icon_takes_the_colour_of_the_state(self):
        for snap, name in ((snapshot(RUNNING), 'BR_GREEN'), (snapshot(with_exit_node()), 'BR_AQUA'),
                           (snapshot(STOPPED, 'Disconnected'), 'FG2'), (snapshot(NEEDS_LOGIN), 'BR_ORANGE'),
                           (snapshot(None, 'Connecting'), 'BR_YELLOW'), (snapshot(None, None), 'FG2')):
            self.calls.clear()
            tailscale.render(snap, False)
            (args,) = self.calls
            self.assertEqual(args[:4], ['--set', 'tailscale', 'drawing=on', f'icon={tailscale.ICON}'])
            self.assertIn(f'icon.color={self.palette[name]}', args)
            self.assertIn('label.drawing=off', args)
            self.assertFalse([a for a in args if a.startswith('tailscale.i.')])  # popup closed: untouched

    def test_an_open_popup_fills_in_every_row_once(self):
        tailscale.render(snapshot(RUNNING), True)
        (args,) = self.calls
        items = [args[i + 1] for i, a in enumerate(args) if a == '--set' and i > 0]
        self.assertEqual(items, [f'tailscale.i.{name}' for name in tailscale.ROWS])
        self.assertIn('label=Tailscale · Connected', args)
        self.assertIn('label.font=JetBrainsMono Nerd Font:Bold:13.0', args)        # the title only
        self.assertEqual(sum(a.startswith('label.font=') for a in args), 1)
        hidden = [args[i + 1] for i, a in enumerate(args[:-2]) if a == '--set' and args[i + 2] == 'drawing=off']
        self.assertEqual(hidden, ['tailscale.i.note', 'tailscale.i.more'])

    def test_create_adds_the_rows_and_wires_only_the_two_clicks(self):
        tailscale.create()
        (args,) = self.calls
        self.assertEqual(args[:2], ['--remove', '/tailscale\\.i\\..*/'])
        added = [args[i + 2] for i, a in enumerate(args) if a == '--add']
        self.assertEqual(added, [f'tailscale.i.{name}' for name in tailscale.ROWS])
        clicks = [a for a in args if a.startswith('click_script=')]
        self.assertEqual(clicks, [f'click_script={tailscale.SELF} switch', f'click_script={tailscale.SELF} open'])
        self.assertIn('popup.align=right', args)


class World:
    """Stand-in tailscale, scutil and open programs that share a state directory.

    `backend' exists while the stand-in CLI can answer.  The stand-ins write
    what they were asked to do to `calls', so a test can read the order back.
    """
    CLI = r'''#!/bin/sh
d="$FAKE_DIR"
echo "cli $*" >> "$d/calls"
if [ -e "$d/cli_broken" ]; then echo "The Tailscale CLI failed to start: Failed to load preferences."; exit 0; fi
[ -e "$d/backend" ] || { echo "failed to connect to local Tailscale service" >&2; exit 1; }
case "$1" in
  status) cat "$d/status.json" ;;
  up)
    [ -e "$d/up_fails" ] && { echo "up: simulated failure" >&2; exit 1; }
    cp "$d/running.json" "$d/status.json"; echo Connected > "$d/ne" ;;
  down)
    [ -e "$d/down_does_nothing" ] && exit 0
    cp "$d/stopped.json" "$d/status.json"; echo Disconnected > "$d/ne"
    if [ -e "$d/down_kills_backend" ]; then rm -f "$d/backend"; fi ;;
esac
'''
    SCUTIL = r'''#!/bin/sh
d="$FAKE_DIR"
case "$2" in
  list)
    state=$(cat "$d/ne" 2>/dev/null || echo Disconnected)
    [ -e "$d/no_service" ] && { echo "Available network connection services in the current set (*=enabled):"; exit 0; }
    printf 'Available network connection services in the current set (*=enabled):\n'
    printf '* (%s)   33333333-4444-5555-6666-777777777777 VPN (io.tailscale.ipn.macsys) "Tailscale"   [VPN:io.tailscale.ipn.macsys]\n' "$state" ;;
  start)
    echo "scutil start $3" >> "$d/calls"
    [ -e "$d/start_fails" ] && exit 0
    echo Connected > "$d/ne"; touch "$d/backend"; cp "$d/stopped.json" "$d/status.json" ;;
  stop)
    echo "scutil stop $3" >> "$d/calls"
    [ -e "$d/stop_does_nothing" ] && exit 0
    echo Disconnected > "$d/ne"; rm -f "$d/backend" ;;
esac
'''
    OPEN = '#!/bin/sh\necho "open $*" >> "$FAKE_DIR/calls"\n'

    def __init__(self, directory, state='off-backend-up'):
        self.dir = Path(directory)
        bin_dir = self.dir / 'bin'
        bin_dir.mkdir()
        for name, text in (('tailscale', self.CLI), ('scutil', self.SCUTIL), ('open', self.OPEN)):
            path = bin_dir / name
            path.write_text(text)
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
        self.cli, self.scutil, self.open = (str(bin_dir / n) for n in ('tailscale', 'scutil', 'open'))
        for name, data in (('running', RUNNING), ('stopped', STOPPED), ('login', NEEDS_LOGIN)):
            (self.dir / f'{name}.json').write_text(json.dumps(data))
        (self.dir / 'calls').write_text('')
        self.set(state)

    def set(self, state):
        """Put the world in STATE: on, off-backend-up, off-backend-down, login or busy."""
        for name in ('backend', 'ne', 'status.json', 'no_service'):
            (self.dir / name).unlink(missing_ok=True)
        if state == 'on':
            (self.dir / 'backend').touch()
            (self.dir / 'ne').write_text('Connected')
            shutil.copy(self.dir / 'running.json', self.dir / 'status.json')
        elif state == 'off-backend-up':       # `tailscale down' left the backend running
            (self.dir / 'backend').touch()
            (self.dir / 'ne').write_text('Disconnected')
            shutil.copy(self.dir / 'stopped.json', self.dir / 'status.json')
        elif state == 'off-backend-down':     # Tailscale was turned off in the app and nothing answers
            (self.dir / 'ne').write_text('Disconnected')
        elif state == 'login':
            (self.dir / 'backend').touch()
            (self.dir / 'ne').write_text('Connected')
            shutil.copy(self.dir / 'login.json', self.dir / 'status.json')
        elif state == 'busy':
            (self.dir / 'ne').write_text('Connecting')
        elif state == 'not-running':
            (self.dir / 'no_service').touch()

    def flag(self, name):
        (self.dir / name).touch()

    @property
    def calls(self):
        return (self.dir / 'calls').read_text().splitlines()

    def actions(self):
        """The calls that change something, in order (the questions left out)."""
        return [c for c in self.calls if c != 'cli status --json']


class WorldTest(unittest.TestCase):
    """A test with the stand-ins in place of the real programs, the bar recorded, and no waiting."""
    state = 'off-backend-up'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.world = World(self.tmp.name, self.state)
        self.bar_calls = []
        for target, value in (('CLI_CANDIDATES', (self.world.cli,)), ('SCUTIL', self.world.scutil),
                              ('OPEN', self.world.open), ('LOCK_FILE', Path(self.tmp.name) / 'lock'),
                              ('POLL', 0.01), ('START_WAIT', 0.3), ('STATUS_TIMEOUT', 5)):
            patcher = mock.patch.object(tailscale, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(tailscale.p, 'bar', lambda *args: self.bar_calls.append(list(args)))
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.dict(os.environ, {'FAKE_DIR': self.tmp.name})
        patcher.start()
        self.addCleanup(patcher.stop)

    def last_popup(self):
        """The newest bar call that filled the popup in, as {row: text or None}."""
        for args in reversed(self.bar_calls):
            if any(a.startswith('tailscale.i.') for a in args):
                rows, i = {}, 0
                while i < len(args):
                    if args[i] == '--set' and args[i + 1].startswith('tailscale.i.'):
                        name = args[i + 1].split('.')[-1]
                        j = i + 2
                        text = None
                        while j < len(args) and args[j] != '--set':
                            if args[j].startswith('label='):
                                text = args[j][len('label='):]
                            if args[j] == 'drawing=off':
                                text = None
                            j += 1
                        rows[name] = text
                        i = j
                    else:
                        i += 1
                return rows
        return None


class TakeTests(WorldTest):
    def test_connected(self):
        self.world.set('on')
        snap = tailscale.take()
        self.assertEqual((snap['kind'], snap['headline']), ('on', 'Connected'))
        self.assertEqual(snap['summary']['online'], 2)

    def test_off_whether_or_not_the_backend_survives(self):
        for state in ('off-backend-up', 'off-backend-down'):
            self.world.set(state)
            snap = tailscale.take()
            self.assertEqual((snap['kind'], snap['headline']), ('off', 'Off'), state)

    def test_login_and_busy(self):
        self.world.set('login')
        self.assertEqual(tailscale.take()['kind'], 'login')
        self.world.set('busy')
        self.assertEqual(tailscale.take()['kind'], 'busy')

    def test_the_vpn_list_alone_is_enough_without_a_cli(self):
        self.world.set('on')
        with mock.patch.object(tailscale, 'CLI_CANDIDATES', ()), mock.patch.object(tailscale.shutil, 'which', return_value=None):
            snap = tailscale.take()
        self.assertEqual((snap['kind'], snap['summary'], snap['cli']), ('on', None, None))

    def test_a_cli_alone_is_enough_without_the_vpn_list(self):
        self.world.set('not-running')            # no service in the list, and no backend
        snap = tailscale.take()
        self.assertEqual((snap['kind'], snap['headline']), ('down', 'Not running'))

    def test_not_installed_is_nothing(self):
        self.world.set('not-running')
        with mock.patch.object(tailscale, 'CLI_CANDIDATES', ()), mock.patch.object(tailscale.shutil, 'which', return_value=None):
            self.assertIsNone(tailscale.take())

    def test_the_cli_is_asked_for_json_and_its_exit_status_is_ignored(self):
        self.world.set('on')
        Path(self.tmp.name, 'status.json').write_text(json.dumps(STOPPED))
        script = Path(self.world.cli)
        script.write_text(script.read_text().replace('status) cat "$d/status.json" ;;',
                                                     'status) cat "$d/status.json"; exit 1 ;;'))
        self.assertEqual(tailscale.fetch_status(self.world.cli)['BackendState'], 'Stopped')

    def test_rubbish_and_silence_and_hangs_are_no_answer(self):
        self.world.set('on')
        script = Path(self.world.cli)
        for body in ('echo "<html>nope</html>"', 'echo \'["a list"]\'', 'echo \'{"no": "state"}\'', 'exit 3'):
            script.write_text(f'#!/bin/sh\n{body}\n')
            self.assertIsNone(tailscale.fetch_status(self.world.cli), body)
        script.write_text('#!/bin/sh\nexec sleep 10\n')
        with mock.patch.object(tailscale, 'STATUS_TIMEOUT', 0.3):
            self.assertIsNone(tailscale.fetch_status(self.world.cli))

    def test_the_apps_own_binary_comes_before_the_wrapper_and_homebrew(self):
        app, wrapper = Path(self.tmp.name, 'app'), Path(self.tmp.name, 'wrapper')
        for path in (app, wrapper):
            path.write_text('#!/bin/sh\n')
            path.chmod(0o755)
        with mock.patch.object(tailscale, 'CLI_CANDIDATES', (str(Path(self.tmp.name, 'missing')), str(app), str(wrapper))):
            self.assertEqual(tailscale.find_cli(), str(app))


class SwitchTests(WorldTest):
    def note(self):
        """The message in the popup, across the two rows it may take."""
        rows = self.last_popup() or {}
        return ' '.join(text for text in (rows.get('note'), rows.get('more')) if text) or None

    def test_turning_off_when_the_backend_survives(self):
        self.world.set('on')
        tailscale.switch()
        self.assertEqual(self.world.actions(), ['cli down'])
        self.assertEqual(tailscale.take()['kind'], 'off')
        self.assertIsNone(self.note())
        self.assertEqual(self.last_popup()['switch'], '\U000F0522  Turn on')

    def test_turning_off_when_the_backend_goes_with_it(self):
        self.world.set('on')
        self.world.flag('down_kills_backend')
        tailscale.switch()
        self.assertEqual(self.world.actions(), ['cli down'])
        self.assertEqual(tailscale.take()['kind'], 'off')    # the CLI no longer answers; the VPN list says off
        self.assertIsNone(self.note())

    def test_turning_on_when_the_backend_is_there(self):
        tailscale.switch()
        self.assertEqual(self.world.actions(), ['cli up --timeout=20s'])
        self.assertEqual(tailscale.take()['kind'], 'on')
        self.assertEqual(self.last_popup()['switch'], '\U000F0521  Turn off')

    def test_turning_on_when_nothing_answers_starts_the_tunnel_first(self):
        self.world.set('off-backend-down')
        tailscale.switch()
        self.assertEqual(self.world.actions(), ['scutil start Tailscale', 'cli up --timeout=20s'])
        self.assertEqual(tailscale.take()['kind'], 'on')
        self.assertIsNone(self.note())

    def test_a_tunnel_that_will_not_start_says_so(self):
        self.world.set('off-backend-down')
        self.world.flag('start_fails')
        tailscale.switch()
        self.assertEqual(self.world.actions(), ['scutil start Tailscale'])
        self.assertEqual(self.note(), "Tailscale didn't start")
        self.assertEqual(tailscale.take()['kind'], 'off')

    def test_a_failing_up_shows_what_the_cli_said(self):
        self.world.flag('up_fails')
        tailscale.switch()
        self.assertEqual(self.note(), 'up: simulated failure')
        self.assertEqual(tailscale.take()['kind'], 'off')

    def test_a_down_that_does_nothing_is_followed_by_stopping_the_tunnel(self):
        self.world.set('on')
        self.world.flag('down_does_nothing')
        tailscale.switch()
        self.assertEqual(self.world.actions(), ['cli down', 'scutil stop Tailscale'])
        self.assertEqual(tailscale.take()['kind'], 'off')
        self.assertIsNone(self.note())

    def test_when_nothing_can_turn_it_off_the_popup_says_so(self):
        self.world.set('on')
        self.world.flag('down_does_nothing')
        self.world.flag('stop_does_nothing')
        tailscale.switch()
        self.assertEqual(self.world.actions(), ['cli down', 'scutil stop Tailscale'])
        self.assertEqual(self.note(), "Couldn't turn Tailscale off")
        self.assertEqual(tailscale.take()['kind'], 'on')

    def test_a_cli_that_cannot_start_is_worked_around_when_turning_off(self):
        # What the real one did here: it says so on stdout and exits 0.
        self.world.set('on')
        self.world.flag('cli_broken')
        tailscale.switch()
        self.assertEqual(self.world.actions(), ['cli down', 'scutil stop Tailscale'])
        self.assertEqual(tailscale.take()['kind'], 'off')
        self.assertIsNone(self.note())

    def test_a_cli_that_cannot_start_is_reported_when_nothing_else_works_either(self):
        self.world.set('on')
        self.world.flag('cli_broken')
        self.world.flag('stop_does_nothing')
        tailscale.switch()
        self.assertEqual(self.note(), 'The Tailscale CLI failed to start: Failed to load preferences.')

    def test_turning_on_with_a_cli_that_never_answers_says_the_tunnel_started(self):
        self.world.set('off-backend-down')
        self.world.flag('cli_broken')
        tailscale.switch()
        self.assertEqual(self.world.actions(), ['scutil start Tailscale'])
        self.assertEqual(self.note(), "Started, but the Tailscale command isn't answering")
        self.assertEqual(tailscale.take()['kind'], 'on')       # the VPN list is all there is to go on

    def test_up_that_does_nothing_is_reported(self):
        # `up' exits 0 yet the state does not change
        script = Path(self.world.cli)
        script.write_text(script.read_text().replace(
            '    cp "$d/running.json" "$d/status.json"; echo Connected > "$d/ne" ;;', '    exit 0 ;;'))
        tailscale.switch()
        self.assertEqual(self.note(), 'Still off; try again')

    def test_the_row_says_what_is_happening_before_it_finishes(self):
        self.world.set('on')
        tailscale.switch()
        first = self.bar_calls[0]
        self.assertEqual(first, ['--set', 'tailscale.i.switch', 'label=\U000F0521  Turning off…'])

    def test_a_login_opens_the_login_page(self):
        self.world.set('login')
        tailscale.switch()
        self.assertEqual(self.world.actions(), ['open https://login.example.com/a/abc123'])

    def test_tailscale_not_running_opens_the_app(self):
        self.world.set('not-running')
        tailscale.switch()
        self.assertEqual(self.world.actions(), ['open -a Tailscale'])

    def test_a_click_while_it_is_busy_does_nothing(self):
        self.world.set('busy')
        tailscale.switch()
        self.assertEqual(self.world.actions(), [])
        self.assertEqual(self.bar_calls, [])

    def test_a_second_click_while_the_first_is_handled_is_dropped(self):
        self.world.set('on')
        with open(tailscale.LOCK_FILE, 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            tailscale.switch()
        self.assertEqual(self.world.calls, [])
        tailscale.switch()                       # the lock is free again
        self.assertEqual(self.world.actions(), ['cli down'])

    def test_not_installed_does_nothing(self):
        self.world.set('not-running')
        with mock.patch.object(tailscale, 'CLI_CANDIDATES', ()), mock.patch.object(tailscale.shutil, 'which', return_value=None):
            tailscale.switch()
        self.assertEqual(self.bar_calls, [])

    def test_open_runs_the_app(self):
        tailscale.open_app()
        self.assertEqual(self.world.calls, ['open -a Tailscale'])


class UpdateTests(WorldTest):
    def test_update_draws_the_item(self):
        self.world.set('on')
        with mock.patch.object(tailscale.p, 'is_open', return_value=False):
            tailscale.update()
        (args,) = self.bar_calls
        self.assertEqual(args[:3], ['--set', 'tailscale', 'drawing=on'])

    def test_update_refreshes_an_open_popup(self):
        self.world.set('on')
        with mock.patch.object(tailscale.p, 'is_open', return_value=True):
            tailscale.update()
        self.assertEqual(self.last_popup()['peers'], 'Peers    2 of 3 online')

    def test_update_hides_the_item_when_tailscale_is_gone(self):
        self.world.set('not-running')
        with mock.patch.object(tailscale, 'CLI_CANDIDATES', ()), mock.patch.object(tailscale.shutil, 'which', return_value=None), \
                mock.patch.object(tailscale.p, 'is_open', side_effect=AssertionError('asked about the popup')):
            tailscale.update()
        self.assertEqual(self.bar_calls, [['--set', 'tailscale', 'drawing=off', 'popup.drawing=off']])

    def test_clicking_away_closes_the_popup_and_asks_nothing(self):
        closed = []
        with mock.patch.dict(os.environ, {'SENDER': 'mouse.exited.global'}), \
                mock.patch.object(tailscale.p, 'close', lambda item: closed.append(item)):
            tailscale.update()
        self.assertEqual((closed, self.world.calls), (['tailscale'], []))

    def test_toggle_hands_the_popup_to_the_shared_code(self):
        with mock.patch.object(tailscale.p, 'toggle') as toggle:
            tailscale.toggle()
        parent, create, render = toggle.call_args[0]
        self.assertEqual((parent, create), ('tailscale', tailscale.create))
        self.world.set('on')
        render()
        self.assertEqual(self.last_popup()['title'], 'Tailscale · Connected')

    def test_status_prints_what_it_found(self):
        self.world.set('on')
        out = io.StringIO()
        with mock.patch('sys.stdout', out):
            tailscale.status()
        text = out.getvalue()
        for expected in ('Tailscale', 'status     : JSON ok', 'the item   : on (Connected)', 'Peers    2 of 3 online'):
            self.assertIn(expected, text)

    def test_popup_registers_tailscale_so_the_other_popups_close_it(self):
        self.assertEqual(tailscale.p.TAILSCALE, 'tailscale')
        source = (PLUGINS / 'popup.py').read_text()
        self.assertIn('for other in (CAL, PRAYERS, NOWPLAYING, TOKENS, TAILSCALE):', source)


class VpnScriptTests(unittest.TestCase):
    """plugins/vpn.sh must not turn green because Tailscale is: the Tailscale item says that."""

    def run_vpn(self, scutil_output):
        with tempfile.TemporaryDirectory() as tmp:
            shims = Path(tmp)
            # The real script asks Cisco's client first, at a fixed path; point it nowhere so
            # a Cisco client on this machine cannot decide the result.
            text = (PLUGINS / 'vpn.sh').read_text()
            self.assertIn('/opt/cisco/secureclient/bin/vpn', text)
            (shims / 'vpn.sh').write_text(text.replace('/opt/cisco/secureclient/bin/vpn', '/nonexistent/vpn'))
            (shims / 'scutil').write_text(f"#!/bin/sh\ncat <<'EOF'\n{scutil_output}EOF\n")
            (shims / 'sketchybar').write_text(f'#!/bin/sh\necho "$@" >> "{tmp}/bar"\n')
            for name in ('scutil', 'sketchybar'):
                (shims / name).chmod(0o755)
            env = dict(os.environ, PATH=f'{tmp}:/usr/bin:/bin', NAME='vpn', CONFIG_DIR=str(PLUGINS.parent))
            subprocess.run(['bash', str(shims / 'vpn.sh')], env=env, check=True, capture_output=True)
            return (Path(tmp) / 'bar').read_text()

    def lines(self, tailscale_state, corporate_state):
        return (f'* ({corporate_state})   22222222-3333-4444-5555-666666666666 VPN (com.apple.example.anyconnect) "Corporate"   [VPN:com.apple.example.anyconnect]\n'
                f'* ({tailscale_state})   33333333-4444-5555-6666-777777777777 VPN (io.tailscale.ipn.macsys) "Tailscale"   [VPN:io.tailscale.ipn.macsys]\n')

    def test_tailscale_connected_alone_leaves_the_vpn_item_red(self):
        palette = tailscale.p.colors()
        self.assertIn(f"icon.color={palette['BR_RED']}", self.run_vpn(self.lines('Connected', 'Disconnected')))

    def test_a_connected_corporate_vpn_still_turns_it_green(self):
        palette = tailscale.p.colors()
        self.assertIn(f"icon.color={palette['BR_GREEN']}", self.run_vpn(self.lines('Disconnected', 'Connected')))
        self.assertIn(f"icon.color={palette['BR_GREEN']}", self.run_vpn(self.lines('Connected', 'Connected')))


if __name__ == '__main__':
    unittest.main()
