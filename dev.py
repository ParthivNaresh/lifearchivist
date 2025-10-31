#!/usr/bin/env python3
"""
Development server with hot reload support for Life Archivist.
Provides better reload handling than uvicorn's built-in reload.
"""

import os
import sys
import time
import subprocess
import signal
from pathlib import Path
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

class ServerReloader(FileSystemEventHandler):
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.last_restart = 0
        self.restart_delay = 1.0
        self.watch_extensions = {'.py', '.toml', '.env', '.sql'}
        self.ignore_paths = {
            '__pycache__',
            '.git',
            '.mypy_cache',
            '.pytest_cache',
            '.ruff_cache',
            'node_modules',
            'dist',
            'build',
            '.venv',
            'desktop'
        }
        
    def should_reload(self, path: str) -> bool:
        path_obj = Path(path)
        
        if any(ignored in path_obj.parts for ignored in self.ignore_paths):
            return False
            
        if path_obj.suffix not in self.watch_extensions:
            return False
            
        return True
        
    def on_modified(self, event):
        if isinstance(event, FileModifiedEvent) and not event.is_directory:
            if self.should_reload(event.src_path):
                current_time = time.time()
                if current_time - self.last_restart > self.restart_delay:
                    print(f"\n🔄 File changed: {event.src_path}")
                    self.restart_server()
                    self.last_restart = current_time
    
    def start_server(self):
        print("🚀 Starting Life Archivist development server...")
        
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['TOKENIZERS_PARALLELISM'] = 'false'
        
        self.process = subprocess.Popen(
            [
                sys.executable, '-m', 'uvicorn',
                'lifearchivist.server.main:create_app',
                '--host', 'localhost',
                '--port', '8000',
                '--factory',
                '--log-level', 'info'
            ],
            env=env,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        
        print("✅ Server started on http://localhost:8000")
        
    def stop_server(self):
        if self.process:
            print("🛑 Stopping server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None
            
    def restart_server(self):
        print("♻️  Restarting server...")
        self.stop_server()
        time.sleep(0.5)
        self.start_server()
        
    def run(self):
        self.start_server()
        
        observer = Observer()
        observer.schedule(self, path='lifearchivist', recursive=True)
        observer.start()
        
        print("👀 Watching for file changes...")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                time.sleep(1)
                if self.process and self.process.poll() is not None:
                    print("⚠️  Server crashed, restarting...")
                    self.start_server()
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
            observer.stop()
            self.stop_server()
        observer.join()

def main():
    def signal_handler(sig, frame):
        print("\n👋 Received interrupt signal")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    reloader = ServerReloader()
    reloader.run()

if __name__ == '__main__':
    main()