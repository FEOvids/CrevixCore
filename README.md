# 🧠 CrevixRust OS

**Version: 0.2 Early Beta Release**
Kernel: Rust Official Kernel Booter (Linux 6.6.10 Base)
**Developer: FEOServices**

CrevixRust is a custom operating system featuring a bulletproof, pure-Python desktop environment running directly on top of a minimal Linux kernel. It bypasses bloated traditional desktop environments (like GNOME or KDE) in favor of a lightweight, heavily customized PyQt6 interface.

**✨ Features**

**Custom UI Framework** (crevix_ui.py): Windows 11-style borderless rounded corners, custom title bars, and a unified color palette.

**Global Theming**: System-wide Light and Dark mode toggles.

**Foolproof Crash Shield**: Python exceptions are caught and displayed safely in GUI message boxes instead of crashing the OS.

**Built-in Apps**: Parallax (File Explorer with .exe Wine64 support)

**GPUMate (Hardware Monitor)**

**Terminal (Native bash integration)**

**TextEditor & ImageViewer**

# 🚀 Building the OS

You can build this OS natively on Linux or via WSL (Windows Subsystem for Linux).

Ensure you are in your WSL/Linux home directory (e.g., ~/CrevixRust_OS_Project). Do not build on a mounted Windows drive (/mnt/c/).

Run the build script as root:

```bash
sudo ./build.sh
```

The final bootable ISO will be generated in build/CrevixRust_OS.iso.
