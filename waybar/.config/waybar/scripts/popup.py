#!/usr/bin/env python3
"""Click-toggle calendar/prayer panels. Requires GTK3 and gtk-layer-shell."""
import argparse
import calendar
from datetime import date, datetime
import fcntl
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
from zoneinfo import ZoneInfo

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gdk, GLib, Gtk, GtkLayerShell

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nowplaying
import tailscale_status

ROOT = Path(__file__).resolve().parent.parent
CLOCK_TZ = ZoneInfo('America/Los_Angeles')
PRAYER_NAMES = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']


def prayer_state(data, now):
    """Highlight today's latest schedule row, starting with Fajr at midnight."""
    today = date.fromisoformat(data['date'])
    if today != now.date():
        raise ValueError('Schedule is out of date')
    prayers = data['prayers']
    if [p['name'] for p in prayers] != PRAYER_NAMES:
        raise ValueError('Expected all five prayers; update athan first')
    current = 'Fajr'
    current_date = today
    following = None
    rows = list(prayers)
    if data.get('sunrise'):
        rows.insert(1, {'name': 'Sunrise', 'time': data['sunrise']})
    for prayer in rows:
        hour, minute = map(int, prayer['time'].split(':'))
        start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if start <= now:
            current, current_date = prayer['name'], today
        elif following is None and prayer['name'] != 'Sunrise':
            minutes = max(1, int((start - now).total_seconds() + 59) // 60)
            hours, remainder = divmod(minutes, 60)
            delay = f'{hours}h {remainder:02}m' if hours else f'{remainder} min'
            following = f"Next: {prayer['name']} in {delay}"
    return current, current_date, following or 'Next: Fajr tomorrow'


def label(text, css=None, xalign=0):
    widget = Gtk.Label(label=text, xalign=xalign)
    if css:
        widget.get_style_context().add_class(css)
    return widget


def clear(box):
    for child in box.get_children():
        box.remove(child)
        child.destroy()


def panel_left(pointer_x, panel_width, output_width, gap=8):
    """Center over the click, keeping the complete panel inside the output."""
    return max(gap, min(round(pointer_x - panel_width / 2),
                        max(gap, output_width - panel_width - gap)))


class ClickAnchor:
    """Brief transparent surfaces obtain surface-local pointer coordinates.

    Wayland doesn't expose global pointer coordinates to a separate process.
    Mapping a surface on each output gives us an enter event on the clicked
    output without hard-coded module widths. Sway additionally needs a
    zero-distance pointer-focus refresh for stationary pointers.
    """
    def __init__(self, callback):
        self.callback = callback
        self.windows = []
        self.done = False
        display = Gdk.Display.get_default()
        for index in range(display.get_n_monitors()):
            monitor = display.get_monitor(index)
            window = Gtk.Window()
            window.set_name('popup-anchor-probe')
            window.set_decorated(False)
            window.set_app_paintable(True)
            visual = window.get_screen().get_rgba_visual()
            if visual:
                window.set_visual(visual)
            GtkLayerShell.init_for_window(window)
            GtkLayerShell.set_namespace(window, 'waybar-popup-anchor')
            GtkLayerShell.set_monitor(window, monitor)
            GtkLayerShell.set_layer(window, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_exclusive_zone(window, -1)
            GtkLayerShell.set_keyboard_mode(window, GtkLayerShell.KeyboardMode.NONE)
            for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                         GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
                GtkLayerShell.set_anchor(window, edge, True)
            window.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
            window.connect('enter-notify-event', self.enter, monitor)
            window.connect('motion-notify-event', self.enter, monitor)
            self.windows.append(window)
            window.show_all()
        self.timeout = GLib.timeout_add(500, self.finish, None, None)
        if os.environ.get('SWAYSOCK'):
            GLib.timeout_add(75, self.refresh_pointer_focus)

    def refresh_pointer_focus(self):
        if self.done:
            return False
        # Sway doesn't send enter for a newly mapped layer until pointer focus
        # is recalculated. Zero-distance motion does that without moving it.
        try:
            subprocess.run(['swaymsg', '-q', 'seat', '-', 'cursor', 'move', '0', '0'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=0.3)
        except (OSError, subprocess.TimeoutExpired):
            pass
        return False

    def enter(self, _window, event, monitor):
        if not self.done:
            # Defer destruction until GTK has finished dispatching the event.
            self.done = True
            GLib.idle_add(self.finish, monitor, event.x)
        return False

    def finish(self, monitor, x):
        if not self.windows:
            return False
        self.done = True
        GLib.source_remove(self.timeout)
        for window in self.windows:
            window.destroy()
        self.windows.clear()
        self.callback(monitor, x)
        return False

    def cancel(self):
        self.callback = lambda *_: None
        self.finish(None, None)


class Popup:
    def __init__(self, mode, bar_height):
        self.mode = mode
        self.data = None
        self.loading = False
        self.error = None
        self.media_key = None
        self.media_error = None
        self.tailscale_state = None
        self.tailscale_loading = False
        self.tailscale_switching = False
        self.tailscale_error = None
        self.anchor = None
        self.anchor_x = None
        self.visible_date = datetime.now(CLOCK_TZ).date()
        self.month = self.visible_date.replace(day=1)
        self.window = Gtk.Window(title='Waybar popup')
        self.window.set_name('waybar-popup')
        self.window.set_decorated(False)
        self.window.set_app_paintable(True)
        visual = self.window.get_screen().get_rgba_visual()
        if visual:
            self.window.set_visual(visual)
        GtkLayerShell.init_for_window(self.window)
        GtkLayerShell.set_namespace(self.window, 'waybar-popup')
        GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self.window, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_exclusive_zone(self.window, -1)
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                     GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self.window, edge, True)
        # Leave the bar available for toggle/switch clicks.
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.BOTTOM, bar_height)
        self.window.connect('key-press-event', self.keypress)
        self.window.connect('destroy', self.destroyed)
        self.window.connect('size-allocate', lambda *_: GLib.idle_add(self.reposition))
        self.window.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.window.connect('button-press-event', self.outside_click)
        self.panel = Gtk.EventBox()
        self.panel.set_name('popup-panel')
        self.panel.set_halign(Gtk.Align.CENTER)
        self.panel.set_valign(Gtk.Align.END)
        self.panel.set_margin_bottom(8)
        self.panel.connect('size-allocate', lambda *_: GLib.idle_add(self.reposition))
        self.panel.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.panel.connect('button-press-event', lambda *_: True)
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.content.set_size_request(272, -1)
        # GtkEventBox does not allocate CSS padding around its child.
        # Inset the content explicitly, including clearance for the border.
        self.content.set_margin_start(15)
        self.content.set_margin_end(15)
        self.content.set_margin_top(15)
        self.content.set_margin_bottom(15)
        self.panel.add(self.content)
        # An overlay child's offset must not increase the surface's minimum
        # width when a wider panel replaces a narrow one near the right edge.
        self.layout = Gtk.Overlay()
        self.layout.add(Gtk.Box())
        self.layout.add_overlay(self.panel)
        self.window.add(self.layout)
        self.render()
        self.locate_click()
        GLib.timeout_add_seconds(15, self.tick)
        GLib.timeout_add_seconds(60, self.refresh)
        GLib.timeout_add_seconds(1, self.media_tick)
        GLib.timeout_add_seconds(5, self.refresh_tailscale)

    def locate_click(self):
        if self.anchor:
            self.anchor.cancel()
        # Hide while locating, so there is no flash at the previous position.
        self.window.hide()
        self.anchor = ClickAnchor(self.anchored)

    def anchored(self, monitor, x):
        self.anchor = None
        if monitor is not None:
            GtkLayerShell.set_monitor(self.window, monitor)
            self.anchor_x = x
        self.window.show_all()
        GLib.idle_add(self.reposition)

    def reposition(self, *_):
        if self.anchor_x is None:
            return
        width = self.window.get_allocated_width()
        if width <= 1:
            return
        panel_width = (self.panel.get_preferred_width().natural_width
                       - self.panel.get_margin_start() - self.panel.get_margin_end())
        left = panel_left(self.anchor_x, panel_width, width)
        self.panel.set_halign(Gtk.Align.START)
        if self.panel.get_margin_start() != left:
            self.panel.set_margin_start(left)
            self.layout.queue_allocate()

    def destroyed(self, *_):
        if self.anchor:
            self.anchor.cancel()
        Gtk.main_quit()

    def outside_click(self, _widget, event):
        # Events from labels may propagate; compare against the actual panel bounds.
        origin = self.panel.translate_coordinates(self.window, 0, 0)
        allocation = self.panel.get_allocation()
        if origin and (origin[0] <= event.x < origin[0] + allocation.width
                       and origin[1] <= event.y < origin[1] + allocation.height):
            return False
        self.window.destroy()
        return True

    def keypress(self, _window, event):
        if event.keyval == Gdk.KEY_Escape:
            self.window.destroy()
            return True
        return False

    def command(self, mode):
        if mode == self.mode:
            self.window.destroy()
        else:
            self.mode = mode
            self.render()
            self.locate_click()
        return False

    def render(self):
        clear(self.content)
        if self.mode == 'calendar':
            self.render_calendar()
        elif self.mode == 'nowplaying':
            self.render_media()
        elif self.mode == 'tailscale':
            self.render_tailscale()
        else:
            self.render_prayers()
            if self.data is None and not self.loading:
                self.refresh()
        self.content.show_all()

    def render_tailscale(self):
        state = self.tailscale_state
        self.content.pack_start(label('Tailscale · ' + (state['headline'] if state else 'Loading…'), 'heading'), False, False, 0)
        button = Gtk.Button(label='Working…' if self.tailscale_switching else tailscale_status.action_label(state))
        button.set_sensitive(bool(state and state['kind'] in ('on', 'exit', 'off', 'login') and not self.tailscale_switching))
        button.connect('clicked', self.switch_tailscale)
        self.content.pack_start(button, False, False, 0)
        for key, value in state['rows'] if state else []:
            row = label(f'{key}  {value}')
            row.set_line_wrap(True)
            row.set_max_width_chars(38)
            self.content.pack_start(row, False, False, 0)
        note = self.tailscale_error or (state['health'] if state else '')
        if note:
            row = label(note, 'muted')
            row.set_line_wrap(True)
            row.set_max_width_chars(38)
            self.content.pack_start(row, False, False, 0)
        if state is None:
            self.refresh_tailscale()

    def refresh_tailscale(self):
        if self.mode != 'tailscale' or self.tailscale_loading or self.tailscale_switching:
            return True
        self.tailscale_loading = True
        def worker():
            GLib.idle_add(self.tailscale_loaded, tailscale_status.snapshot())
        threading.Thread(target=worker, daemon=True).start()
        return True

    def tailscale_loaded(self, state):
        self.tailscale_loading = False
        self.tailscale_state = state or {'kind': 'down', 'headline': 'Not installed', 'rows': [], 'health': '', 'auth_url': None}
        if self.mode == 'tailscale':
            self.render()
        return False

    def switch_tailscale(self, *_):
        if self.tailscale_switching or self.tailscale_loading:
            return
        state = self.tailscale_state
        self.tailscale_switching = True
        self.tailscale_error = None
        self.render()
        def worker():
            error = tailscale_status.switch(state)
            GLib.idle_add(self.tailscale_switched, error, tailscale_status.snapshot())
        threading.Thread(target=worker, daemon=True).start()

    def tailscale_switched(self, error, state):
        self.tailscale_switching = False
        self.tailscale_error = error
        return self.tailscale_loaded(state)

    def media_tick(self):
        if self.mode == 'nowplaying':
            info = nowplaying.read_snapshot()
            key = self.media_signature(info)
            if key != self.media_key:
                self.render()
            elif info:
                self.update_progress(info)
        return True

    @staticmethod
    def media_signature(info):
        if not info:
            return None
        return tuple(info.get(field) for field in (
            'player', 'title', 'artist', 'album', 'playing', 'duration',
            'can_play', 'can_seek', 'can_previous', 'can_next'))

    def render_media(self):
        info = nowplaying.read_snapshot()
        self.media_key = self.media_signature(info)
        self.content.pack_start(label('Now playing', 'heading'), False, False, 0)
        if not info:
            self.content.pack_start(label('No media loaded', 'muted'), False, False, 0)
            return
        title = label(info['title'])
        title.set_line_wrap(True)
        title.set_max_width_chars(32)
        self.content.pack_start(title, False, False, 0)
        by = label(' · '.join(part for part in (info['artist'], info['album']) if part), 'muted')
        by.set_line_wrap(True)
        by.set_max_width_chars(32)
        self.content.pack_start(by, False, False, 0)
        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        self.content.pack_start(self.progress, False, False, 0)
        self.update_progress(info)
        controls = Gtk.Box(homogeneous=True, spacing=4)
        for text, command, enabled in (
            ('⏮', ['previous'], info['can_previous']),
            ('−15s', ['position', '15-'], info['can_seek']),
            ('⏸' if info['playing'] else '▶', ['play-pause'], info['can_play']),
            ('+15s', ['position', '15+'], info['can_seek']),
            ('⏭', ['next'], info['can_next']),
        ):
            button = Gtk.Button(label=text)
            button.set_sensitive(enabled)
            button.connect('clicked', lambda _, cmd=command, player=info['player']: self.media_control(player, cmd))
            controls.pack_start(button, True, True, 0)
        self.content.pack_start(controls, False, False, 0)
        if self.media_error:
            self.content.pack_start(label(self.media_error, 'muted'), False, False, 0)

    def update_progress(self, info):
        position = nowplaying.position(info)
        duration = info['duration']
        self.progress.set_fraction(position / duration if duration else 0)
        self.progress.set_text(f'{nowplaying.clock(position)} / {nowplaying.clock(duration)}' if duration else 'Live / duration unavailable')

    def media_control(self, player, command):
        def worker():
            error = None
            try:
                result = subprocess.run(['playerctl', '--player', player, *command],
                                        capture_output=True, timeout=4)
                if result.returncode:
                    error = 'Player could not perform this action'
            except (OSError, subprocess.TimeoutExpired):
                error = 'Player is unavailable'
            GLib.idle_add(self.media_control_done, error)
        threading.Thread(target=worker, daemon=True).start()

    def media_control_done(self, error):
        self.media_error = error
        if self.mode == 'nowplaying':
            self.render()
        return False

    def move_month(self, delta):
        index = self.month.year * 12 + self.month.month - 1 + delta
        year, month = divmod(index, 12)
        self.month = date(year, month + 1, 1)
        self.render()

    def today(self, *_):
        self.month = datetime.now(CLOCK_TZ).date().replace(day=1)
        self.render()

    def render_calendar(self):
        header = Gtk.Box(spacing=8)
        previous = Gtk.Button(label='‹')
        previous.connect('clicked', lambda *_: self.move_month(-1))
        following = Gtk.Button(label='›')
        following.connect('clicked', lambda *_: self.move_month(1))
        header.pack_start(previous, False, False, 0)
        header.pack_start(label(self.month.strftime('%B %Y'), 'heading', 0.5), True, True, 0)
        header.pack_start(following, False, False, 0)
        self.content.pack_start(header, False, False, 0)
        grid = Gtk.Grid(column_homogeneous=True, row_homogeneous=True)
        for column, name in enumerate(['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']):
            grid.attach(label(name, 'weekday', 0.5), column, 0, 1, 1)
        today = datetime.now(CLOCK_TZ).date()
        for row, week in enumerate(calendar.Calendar().monthdatescalendar(self.month.year, self.month.month), 1):
            for column, day in enumerate(week):
                style = 'today' if day == today else ('muted' if day.month != self.month.month else 'day')
                cell = label(str(day.day), style, 0.5)
                cell.set_size_request(32, 30)
                grid.attach(cell, column, row, 1, 1)
        self.content.pack_start(grid, False, False, 0)
        button = Gtk.Button(label='Today')
        button.connect('clicked', self.today)
        self.content.pack_start(button, False, False, 0)

    def render_prayers(self):
        self.content.pack_start(label('Prayer times', 'heading'), False, False, 0)
        if self.data is None:
            message = label(self.error or 'Loading prayer times…', 'muted')
            message.set_line_wrap(True)
            message.set_max_width_chars(30)
            self.content.pack_start(message, False, False, 0)
            return
        try:
            now = datetime.now(ZoneInfo(self.data['timezone']))
            current, current_date, following = prayer_state(self.data, now)
        except (KeyError, ValueError, TypeError) as error:
            message = label(str(error), 'muted')
            message.set_line_wrap(True)
            self.content.pack_start(message, False, False, 0)
            return
        self.content.pack_start(label(now.strftime('%A, %B %-d'), 'muted'), False, False, 0)
        rows = list(self.data['prayers'])
        if self.data.get('sunrise'):
            rows.insert(1, {'name': 'Sunrise', 'time': self.data['sunrise']})
        for prayer in rows:
            active = prayer['name'] == current and current_date == now.date()
            row = Gtk.Box(spacing=12)
            row.get_style_context().add_class('prayer-row')
            if active:
                row.get_style_context().add_class('current')
            row.pack_start(label('●' if active else ' ', 'marker'), False, False, 0)
            row.pack_start(label(prayer['name'], 'muted' if prayer['name'] == 'Sunrise' else None), True, True, 0)
            row.pack_end(label(prayer['time'], 'muted' if prayer['name'] == 'Sunrise' else None), False, False, 0)
            self.content.pack_start(row, False, False, 0)
        self.content.pack_start(label(following, 'muted'), False, False, 0)
        if self.error:
            self.content.pack_start(label('Refresh failed · showing cached times', 'muted'), False, False, 0)

    def tick(self):
        today = datetime.now(CLOCK_TZ).date()
        if self.mode == 'prayers' or today != self.visible_date:
            self.visible_date = today
            self.render()
        return True

    def refresh(self):
        if self.mode != 'prayers' or self.loading:
            return True
        self.loading = True
        def worker():
            try:
                binary = Path.home() / '.cargo/bin/athan'
                result = subprocess.run([str(binary), '--all', '--json'], capture_output=True, text=True, timeout=30)
                if result.returncode:
                    raise ValueError('Unable to load prayer times. Retrying…')
                data = json.loads(result.stdout)
                prayer_state(data, datetime.now(ZoneInfo(data['timezone'])))
                error = None
            except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
                data, error = None, str(exc)
            GLib.idle_add(self.loaded, data, error)
        threading.Thread(target=worker, daemon=True).start()
        return True

    def loaded(self, data, error):
        self.loading = False
        self.error = error
        if data is not None:
            self.data = data
        if self.mode == 'prayers':
            # Avoid initiating another load while rendering an error.
            clear(self.content)
            self.render_prayers()
            self.content.show_all()
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['calendar', 'prayers', 'nowplaying', 'tailscale'])
    parser.add_argument('--bar-height', type=int, default=31)
    args = parser.parse_args()
    runtime = Path(os.environ['XDG_RUNTIME_DIR'])
    address = str(runtime / 'waybar-popup.sock')
    # Serialize launches without retaining a daemon after the panel closes.
    with open(runtime / 'waybar-popup.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
            try:
                client.sendto(args.mode.encode(), address)
                return
            except (FileNotFoundError, ConnectionRefusedError):
                pass
        if not Gtk.init_check()[0] or not GtkLayerShell.is_supported():
            raise SystemExit('A Wayland session with layer-shell support is required')
        Path(address).unlink(missing_ok=True)
        server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        server.bind(address)
        os.chmod(address, 0o600)
        server.setblocking(False)
        provider = Gtk.CssProvider()
        provider.load_from_path(str(ROOT / 'popup.css'))
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        popup = Popup(args.mode, args.bar_height)
        def receive(*_):
            mode = server.recv(32).decode()
            if mode in ('calendar', 'prayers', 'nowplaying', 'tailscale'):
                popup.command(mode)
            return True
        GLib.io_add_watch(server.fileno(), GLib.IO_IN, receive)
    try:
        Gtk.main()
    finally:
        server.close()
        # Retain the socket pathname: a later launch detects the dead listener.


if __name__ == '__main__':
    main()
