"""SmartMiBand desktop entry point and owned service-process controller."""
import json
import os
import socket
import subprocess
import sys
import threading
from app_paths import data_dir, resource_dir


def service_command():
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--service']
    return [sys.executable, str(resource_dir() / 'windows_app.py'), '--service']


def dashboard_url():
    cfg = json.loads((data_dir() / 'config.json').read_text(encoding='utf-8-sig'))
    port = int(cfg.get('http_port', 8765))
    if not 1 <= port <= 65535:
        raise ValueError('http_port must be between 1 and 65535')
    return f'http://127.0.0.1:{port}'


def prepare_config():
    path = data_dir() / 'config.json'
    if not path.exists():
        cfg = json.loads((resource_dir() / 'config.example.json').read_text(encoding='utf-8'))
        cfg['host'] = '127.0.0.1'
        path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8')
    return path


def autostart(enabled=None):
    import winreg
    keypath = r'Software\Microsoft\Windows\CurrentVersion\Run'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, keypath) as key:
        if enabled is None:
            try:
                winreg.QueryValueEx(key, 'SmartMiBand')
                return True
            except FileNotFoundError:
                return False
        if enabled:
            command = [sys.executable]
            if not getattr(sys, 'frozen', False):
                command.append(str(resource_dir() / 'windows_app.py'))
            winreg.SetValueEx(key, 'SmartMiBand', 0, winreg.REG_SZ, subprocess.list2cmdline(command))
        else:
            try:
                winreg.DeleteValue(key, 'SmartMiBand')
            except FileNotFoundError:
                pass
    return bool(enabled)


class ServiceController:
    """Only stop our child, never kill unrelated Python processes."""
    def __init__(self):
        self.process = None
        self.lock = threading.RLock()
        self.stop_file = data_dir() / '.desktop-stop'
        self.stopping = False
        self.desired = False

    def running(self):
        return self.process is not None and self.process.poll() is None

    def start(self):
        with self.lock:
            if self.running() or self.stopping:
                return
            cfg = json.loads(prepare_config().read_text(encoding='utf-8-sig'))
            key = str(cfg.get('auth_key', '')).strip()
            if key.lower().startswith('0x'):
                key = key[2:]
            import re
            if not re.fullmatch(r'[0-9a-fA-F]{32}', key):
                raise ValueError('Укажите auth_key (32 hex-символа) и COM-порт в config.json')
            dashboard_url()
            self.stop_file.unlink(missing_ok=True)
            self.desired = True
            env = dict(os.environ, SMARTMIBAND_DATA_DIR=str(data_dir()),
                       SMARTMIBAND_STOP_FILE=str(self.stop_file))
            with (data_dir() / 'desktop-service.log').open('ab') as log:
                self.process = subprocess.Popen(service_command(), cwd=data_dir(), env=env,
                    stdout=log, stderr=log,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))

    def recover(self):
        with self.lock:
            if self.desired and self.process is not None and self.process.poll() == 2:
                self.start()

    def stop(self):
        with self.lock:
            self.desired = False
            if not self.running():
                return
            self.stopping = True
            try:
                self.stop_file.touch()
                try:
                    self.process.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    self.process.terminate()
                    self.process.wait(timeout=5)
            finally:
                self.stopping = False
                self.stop_file.unlink(missing_ok=True)


def main():
    if '--service' in sys.argv:
        import service  # supervisor runs in this child only
        return
    # OS releases this socket on crash; prevent two trays owning two children.
    guard = socket.socket()
    if os.name == 'nt':
        guard.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        guard.bind(('127.0.0.1', 58766))
    except OSError:
        return
    prepare_config()
    import tray
    tray.run(ServiceController())
    guard.close()


if __name__ == '__main__':
    main()
