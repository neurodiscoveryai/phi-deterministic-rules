"""README generated sections must match the code (regenerate with `python tools/render_readme.py`)."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_readme_in_sync():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "render_readme.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


if __name__ == "__main__":
    test_readme_in_sync(); print("ok")
