import subprocess
import time
import sys
from pathlib import Path

AGENTS = [
    # ("host", "host_agent_adk", 10001),
    ("karley", "karley_agent_adk", 10002),
    ("nate", "nate_agent_adk", 10003),
    ("kaitlynn", "kaitlynn_agent_adk", 10004),
]


def start_agents():
    processes = []
    for name, path, port in AGENTS:
        print(f"Starting {name} on port {port}...")
        proc = subprocess.Popen(["python", path])
        processes.append(proc)
        time.sleep(1)  # Small delay to help avoid port race conditions
    return processes



if __name__ == "__main__":
    try:
        procs = start_agents()
        print("✅ All agents launched. Keep this window open.")
        print("➡ Now open another terminal and run: python host_cli.py")
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        print("🛑 Stopping all agents...")
        for p in procs:
            p.terminate()
            
