"""Run upstream stubs in separate processes to avoid module pollution."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
failed = []
for path in sorted((root / "tests").glob("test_*.py")):
    result = subprocess.run([sys.executable, str(path)], cwd=root, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=120)
    print(f"{'PASS' if result.returncode == 0 else 'FAIL'} {path.name}", flush=True)
    if result.returncode:
        failed.append(path.name)
        print(result.stdout + result.stderr)
print(f"{len(failed)} failed", flush=True)
sys.exit(bool(failed))
