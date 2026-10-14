"""Integration check on a private headless Sway display and virtual pointer."""
import os
from pathlib import Path
import subprocess
import tempfile
import time
import socket
import struct
import threading

with tempfile.TemporaryDirectory(prefix='popup-placement-') as directory:
    root=Path(directory)
    config=root/'config'
    config.write_text('xwayland disable\noutput HEADLESS-1 resolution 1280x720\nseat seat0 fallback true\n')
    env={k:v for k,v in os.environ.items() if k not in ('WAYLAND_DISPLAY','DISPLAY','SWAYSOCK')}
    env['WAYBAR_TEST_SCRIPTS']=str(Path(__file__).resolve().parents[1] / '.config/waybar/scripts')
    env.update(XDG_RUNTIME_DIR=directory,WLR_BACKENDS='headless',WLR_RENDERER='pixman',WLR_LIBINPUT_NO_DEVICES='1')
    with (root/'sway.log').open('w') as log:
        compositor=subprocess.Popen(['sway','--unsupported-gpu','-c',str(config)],env=env,stdout=log,stderr=log)
        try:
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                sockets=list(root.glob('sway-ipc*.sock'))
                displays=[p for p in root.glob('wayland-*') if not p.name.endswith('.lock')]
                if sockets and displays: break
                if compositor.poll() is not None: raise RuntimeError((root/'sway.log').read_text())
                time.sleep(.1)
            env.update(SWAYSOCK=str(sockets[0]),WAYLAND_DISPLAY=displays[0].name,PYTHONDONTWRITEBYTECODE='1')
            pointer=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            pointer.connect(str(root / env['WAYLAND_DISPLAY']))
            def send(obj, opcode, payload=b''):
                pointer.sendall(struct.pack('II',obj,((8+len(payload))<<16)|opcode)+payload)
            send(1,1,struct.pack('I',2))
            send(1,0,struct.pack('I',3))
            buffer=b''
            manager=None
            done=False
            while not done:
                buffer+=pointer.recv(65536)
                while len(buffer)>=8:
                    obj,header=struct.unpack('II',buffer[:8])
                    size=header>>16
                    if len(buffer)<size: break
                    body=buffer[8:size]
                    buffer=buffer[size:]
                    if obj==2 and header&65535==0:
                        name,length=struct.unpack('II',body[:8])
                        interface=body[8:8+length-1].decode()
                        if interface=='zwlr_virtual_pointer_manager_v1': manager=name
                    if obj==3: done=True
            assert manager is not None
            interface=b'zwlr_virtual_pointer_manager_v1\0'
            string=struct.pack('I',len(interface))+interface+b'\0'*((-len(interface))%4)
            send(2,0,struct.pack('I',manager)+string+struct.pack('II',1,4))
            send(4,0,struct.pack('II',0,5))
            send(5,1,struct.pack('IIIII',0,240,710,1280,720))
            send(5,4)
            time.sleep(.1)
            child=root/'check.py'
            child.write_text('''import sys
import os
import subprocess
sys.path.insert(0, os.environ['WAYBAR_TEST_SCRIPTS'])
import popup
from gi.repository import Gdk, GLib, Gtk
provider=Gtk.CssProvider()
provider.load_from_path(os.path.join(os.environ['WAYBAR_TEST_SCRIPTS'], '..', 'popup.css'))
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
background=Gtk.Window()
background.set_name('popup-anchor-probe')
popup.GtkLayerShell.init_for_window(background)
popup.GtkLayerShell.set_layer(background,popup.GtkLayerShell.Layer.BOTTOM)
for edge in (popup.GtkLayerShell.Edge.TOP,popup.GtkLayerShell.Edge.BOTTOM,popup.GtkLayerShell.Edge.LEFT,popup.GtkLayerShell.Edge.RIGHT):
    popup.GtkLayerShell.set_anchor(background,edge,True)
background.add(Gtk.Label(label='test desktop'))
background.show_all()
p=None
def open_popup():
    global p
    p=popup.Popup('calendar',31)
    return False
GLib.timeout_add(900,open_popup)
errors=[]
stage=0
def check():
    global stage
    try:
        assert p.anchor_x is not None, 'No pointer enter received'
        width=p.panel.get_allocated_width()
        x=p.panel.translate_coordinates(p.window,0,0)[0]
        print('anchor',p.anchor_x,'panel left',x,'width',width,'surface',p.window.get_allocated_width(),'margin',p.panel.get_margin_start(), 'preferred',p.panel.get_preferred_width(),flush=True)
        if stage == 0:
            assert abs(x+width/2-p.anchor_x)<=2, (x,width,p.anchor_x)
            subprocess.run(['swaymsg','-q','seat','seat0','cursor','set','1260','710'],check=True)
            p.command('nowplaying')
            stage=1
            GLib.timeout_add(800,check)
            return False
        assert x+width == 1272, (x,width)
        if stage == 1:
            p.content.set_size_request(400,-1)
            stage=2
            GLib.timeout_add(300,check)
            return False
        assert width >= 430, width
    except Exception as e:
        errors.append(repr(e))
    p.window.destroy()
    return False
GLib.timeout_add(1900,check)
Gtk.main()
if errors: raise SystemExit(str(errors))
''')
            def move():
                for _ in range(6):
                    time.sleep(.1)
                    send(5,1,struct.pack('IIIII',100,240,710,1280,720))
                    send(5,4)
            threading.Thread(target=move,daemon=True).start()
            result=subprocess.run(['python3',str(child)],env=env,capture_output=True,text=True,timeout=10)
            print(result.stdout, result.stderr)
            if result.returncode: raise SystemExit(result.returncode)
        finally:
            compositor.terminate()
            compositor.wait(timeout=5)
