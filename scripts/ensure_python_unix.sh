#!/usr/bin/env bash
# Bootstrap Python 3.10+ using the platform package manager, then launch the GUI.
set -euo pipefail
APP_DIR="${1:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"

find_python() {
  local candidate version
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      version="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
      if [[ "$version" =~ ^([0-9]+)\.([0-9]+)$ ]] && (( BASH_REMATCH[1] > 3 || (BASH_REMATCH[1] == 3 && BASH_REMATCH[2] >= 10) )); then
        printf '%s\n' "$("$candidate" -c 'import sys; print(sys.executable)')"
        return 0
      fi
    fi
  done
  return 1
}

python_exe=""
if python_exe="$(find_python)" && "$python_exe" -c 'import tkinter' >/dev/null 2>&1; then
  :
else
  if [[ -n "$python_exe" ]]; then
    echo "Python 3.10+ is installed, but Tkinter (the GUI module) is missing."
  else
    echo "Python 3.10+ was not found. This launcher can install it using a supported package manager."
  fi
  read -r -p "Continue with Python installation (may request administrator approval)? [y/N] " answer
  [[ "$answer" =~ ^[Yy]$ ]] || { echo "Cancelled."; exit 1; }

  if [[ "$(uname -s)" == "Darwin" ]]; then
    if ! command -v brew >/dev/null 2>&1; then
      echo "Homebrew is required for automatic installation on macOS. Install it from https://brew.sh/ and rerun this launcher."
      exit 1
    fi
    brew install python@3.12 python-tk@3.12
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-tk
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3 python3-tkinter
  elif command -v zypper >/dev/null 2>&1; then
    sudo zypper --non-interactive install python3 python3-tk
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --needed --noconfirm python tk
  else
    echo "No supported package manager was found. Install Python 3.10+ and Tkinter manually, then rerun start.sh."
    exit 1
  fi

  python_exe="$(find_python)" || { echo "Installation finished, but Python 3.10+ was not found on PATH."; exit 1; }
  "$python_exe" -c 'import tkinter' || { echo "Tkinter is still unavailable. Install the Tkinter package for your Python distribution."; exit 1; }
fi

cd "$APP_DIR"
exec "$python_exe" "$APP_DIR/gui.py"
