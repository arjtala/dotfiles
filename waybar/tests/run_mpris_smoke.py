import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import traceback
import gi
from gi.repository import Gio, GLib

xml = '''<node>
<interface name="org.mpris.MediaPlayer2">
<property name="Identity" type="s" access="read"/>
<property name="CanQuit" type="b" access="read"/>
<property name="CanRaise" type="b" access="read"/>
<property name="HasTrackList" type="b" access="read"/>
<property name="SupportedUriSchemes" type="as" access="read"/>
<property name="SupportedMimeTypes" type="as" access="read"/>
</interface>
<interface name="org.mpris.MediaPlayer2.Player">
<method name="PlayPause"/><method name="Next"/><method name="Previous"/>
<method name="Seek"><arg type="x" direction="in"/></method>
<property name="PlaybackStatus" type="s" access="read"/>
<property name="Metadata" type="a{sv}" access="read"/>
<property name="Position" type="x" access="read"/>
<property name="Rate" type="d" access="read"/>
<property name="Volume" type="d" access="read"/>
<property name="CanControl" type="b" access="read"/>
<property name="CanPlay" type="b" access="read"/>
<property name="CanPause" type="b" access="read"/>
<property name="CanSeek" type="b" access="read"/>
<property name="CanGoNext" type="b" access="read"/>
<property name="CanGoPrevious" type="b" access="read"/>
</interface></node>'''
status = 'Playing'
actions = []
conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)
path='/org/mpris/MediaPlayer2'

def get_property(_conn, _sender, _path, _interface, name):
    if name == 'Metadata':
        return GLib.Variant('a{sv}', {'xesam:title':GLib.Variant('s','Test song'), 'xesam:artist':GLib.Variant('as',['Test artist']), 'mpris:length':GLib.Variant('x',300000000), 'mpris:trackid':GLib.Variant('o','/test/track')})
    if name == 'PlaybackStatus': return GLib.Variant('s',status)
    if name == 'Identity': return GLib.Variant('s','Test player')
    if name == 'Position': return GLib.Variant('x',20000000)
    if name in ('Rate','Volume'): return GLib.Variant('d',1.0)
    if name in ('SupportedUriSchemes','SupportedMimeTypes'): return GLib.Variant('as',[])
    return GLib.Variant('b',True)

def method(_conn,_sender,_path,_interface,name,args,invocation):
    global status
    actions.append((name,args.unpack()))
    if name == 'PlayPause':
        status='Paused' if status == 'Playing' else 'Playing'
        conn.emit_signal(None,path,'org.freedesktop.DBus.Properties','PropertiesChanged',GLib.Variant('(sa{sv}as)',('org.mpris.MediaPlayer2.Player',{'PlaybackStatus': GLib.Variant('s',status)},[])))
    invocation.return_value(None)

for interface in Gio.DBusNodeInfo.new_for_xml(xml).interfaces:
    conn.register_object(path,interface,method,get_property,None)
owner=Gio.bus_own_name_on_connection(conn,'org.mpris.MediaPlayer2.waybar_test',Gio.BusNameOwnerFlags.NONE,None,None)
loop=GLib.MainLoop()
errors=[]

def test():
    try:
        time.sleep(.3)
        with tempfile.TemporaryDirectory(prefix='waybar-media-') as runtime:
            env=dict(os.environ,XDG_RUNTIME_DIR=runtime,PYTHONDONTWRITEBYTECODE='1')
            watcher=subprocess.Popen(['python3',str(Path(__file__).resolve().parents[1] / '.config/waybar/scripts/nowplaying.py')],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                def snapshot(playing):
                    deadline=time.monotonic()+8
                    while time.monotonic()<deadline:
                        if watcher.poll() is not None:
                            raise AssertionError(watcher.stderr.read())
                        try:
                            data=json.loads((Path(runtime)/'waybar-nowplaying.json').read_text())['media']
                            if data and data['playing'] == playing: return data
                        except (FileNotFoundError,ValueError): pass
                        time.sleep(.05)
                    raise AssertionError('No matching snapshot')
                data=snapshot(True)
                assert data['title']=='Test song' and data['can_seek']
                player=data['player']
                for command in (['play-pause'],['position','15-'],['next']):
                    subprocess.run(['playerctl','--player',player,*command],check=True,capture_output=True,timeout=4)
                assert snapshot(False)['status']=='Paused'
                assert ('Seek',(-15000000,)) in actions, actions
                assert ('Next',()) in actions, actions
                print('MPRIS integration passed: metadata, pause updates, seek and next controls')
            finally:
                watcher.terminate()
                watcher.wait(timeout=4)
    except Exception:
        errors.append(traceback.format_exc())
    finally:
        GLib.idle_add(loop.quit)
threading.Thread(target=test,daemon=True).start()
loop.run()
if errors:
    raise SystemExit('\n'.join(errors))
