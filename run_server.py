import sys
import os
import socket
from pathlib import Path

# Configure UTF-8 output if supported
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import uvicorn

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def find_available_port(preferred_ports=[8000, 8080, 8050, 8001, 8888]):
    for port in preferred_ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return 8080

if __name__ == "__main__":
    port = int(os.environ.get("PORT", find_available_port()))
    local_ip = get_local_ip()

    print("=" * 65)
    print("CareerPilot AI - Autonomous Career Navigation & Application Engine")
    print("=" * 65)
    print(f"  * Local PC URL:        http://localhost:{port}")
    print(f"  * Mobile / LAN URL:    http://{local_ip}:{port}")
    print(f"  * Interactive Swagger: http://localhost:{port}/docs")
    print( "  * Database:            SQLite (backend/career_agent.db)")
    print("=" * 65)
    print("Press Ctrl+C to stop the server.\n")

    # Bind to 0.0.0.0 so phones on the same Wi-Fi can access it
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=False)
