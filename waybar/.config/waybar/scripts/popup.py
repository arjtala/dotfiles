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
import threading
from zoneinfo import ZoneInfo

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gdk, GLib, Gtk, GtkLayerShell

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


class Popup:
    def __init__(self, mode, bar_height):
        self.mode = mode
        self.data = None
        self.loading = False
        self.error = None
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
        self.window.connect('destroy', lambda *_: Gtk.main_quit())
        self.window.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.window.connect('button-press-event', self.outside_click)
        self.panel = Gtk.EventBox()
        self.panel.set_name('popup-panel')
        self.panel.set_halign(Gtk.Align.CENTER)
        self.panel.set_valign(Gtk.Align.END)
        self.panel.set_margin_bottom(8)
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
        self.window.add(self.panel)
        self.render()
        self.window.show_all()
        GLib.timeout_add_seconds(15, self.tick)
        GLib.timeout_add_seconds(60, self.refresh)

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
        return False

    def render(self):
        clear(self.content)
        if self.mode == 'calendar':
            self.render_calendar()
        else:
            self.render_prayers()
            if self.data is None and not self.loading:
                self.refresh()
        self.content.show_all()

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
    parser.add_argument('mode', choices=['calendar', 'prayers'])
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
            if mode in ('calendar', 'prayers'):
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
