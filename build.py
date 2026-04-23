#!/bin/bash

# ==============================================================================
# CREVIXRUST OS MASTER BUILD TRIGGER (WSL & LINUX NATIVE)
# ==============================================================================

set -e

echo "🧠 Checking build environment..."

if [ "$EUID" -ne 0 ]; then
  echo "[!] ERROR: Please run this script as root (sudo ./build.sh)"
  exit 1
fi

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  echo "[!] ERROR: You are running this in native Windows. Please open WSL (Ubuntu) and run it there."
  exit 1
fi

PWD_PATH=$(pwd)
if [[ "$PWD_PATH" == /mnt/c/* ]] || [[ "$PWD_PATH" == /mnt/d/* ]]; then
  echo "[!] STOP: You are in a mounted Windows directory ($PWD_PATH)."
  echo "    Building here will break file permissions and symlinks."
  echo "    Move the project to your native Linux home directory (e.g., ~/CrevixRust_OS_Project) and try again."
  exit 1
fi

echo "[*] Environment looks good. Generating workspace..."
python3 generate_workspace.py

echo "[*] Firing up the Python build system..."
python3 build_crevixrust.py

echo "✅ Build pipeline completed successfully."
