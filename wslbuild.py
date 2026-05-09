import os
import stat
import sys

# ==============================================================================
# CREVIXRUST OS WORKSPACE GENERATOR - 0.3 MASSIVE UZI ENGINE 2.0 UPDATE
# Now listen users
# This is ONLY for WSL
# This hasnt been tested on a proper linux distribution and might not run as intended
# Neither has this been tested on MacOS
# If you arent on windows, Please just download the ISO from https://crevixcore.ct.ws/ website
# If you are on windows do wsl --install and install Ubuntu from microsoft store and run ubuntu
# Then go to root and move the script there & run it then cd CrevixRust_OS_Project and then sudo python3 build_crevixrust.py
# Pretty simple if your on windows
# ==============================================================================

if os.path.basename(os.getcwd()) == "CrevixRust_OS_Project":
    workspace_name = "."
else:
    workspace_name = "CrevixRust_OS_Project"

files = {
    # ==========================================================================
    # 1. MASTER BUILD SYSTEM
    # ==========================================================================
    "build_crevixrust.py": """#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil

print("🧠 Starting CrevixRust OS Build System...")

def run_cmd(cmd, step_name):
    print(f"\\n---> [RUNNING] {step_name}\\n     Command: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"\\n[!] ERROR: {step_name} failed. Exiting.")
        sys.exit(1)
    print(f"---> [SUCCESS] {step_name}\\n")

def main():
    if sys.platform == "win32":
        print("[!] Detected Windows natively. Please run this inside WSL.")
        sys.exit(1)

    if hasattr(os, 'geteuid') and os.geteuid() != 0:
        print("Please run the build script as root (sudo).")
        sys.exit(1)

    os.makedirs("build/rootfs", exist_ok=True)
    os.makedirs("build/iso", exist_ok=True)

    if os.path.exists("wallpaper.png"): shutil.copy("wallpaper.png", "src/desktop/wallpaper.png")
    if os.path.exists("logo.png"): shutil.copy("logo.png", "src/desktop/logo.png")

    run_cmd("apt-get clean && rm -rf /var/lib/apt/lists/* && (apt-get update || true) && apt-get install -y --fix-missing build-essential flex bison bc libssl-dev libelf-dev xorriso mtools grub-pc-bin grub-common wget cpio debootstrap unzip", "Installing Host Dependencies")
    run_cmd("./scripts/1_build_kernel.sh", "Compiling Linux Kernel")
    run_cmd("./scripts/2_build_rootfs.sh", "Building Minimal Root Filesystem")
    run_cmd("./scripts/3_install_desktop.sh", "Installing Python Desktop Environment")
    run_cmd("./scripts/4_make_iso.sh", "Generating Bootable ISO")

    print("🎉 BOOM! CrevixRust_OS.iso has been successfully built! Uzi Engine 2.0 deployed.")

if __name__ == "__main__":
    main()
""",

    # ==========================================================================
    # 2. BUILD SCRIPTS
    # ==========================================================================
    "scripts/1_build_kernel.sh": """#!/bin/bash
set -e
KERNEL_VERSION="6.6.10"
BUILD_DIR="build/kernel"

if [ ! -f "$BUILD_DIR/arch/x86/boot/bzImage" ]; then
    mkdir -p $BUILD_DIR
    cd $BUILD_DIR
    
    if [ ! -f "linux-$KERNEL_VERSION.tar.xz" ]; then
        wget https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-$KERNEL_VERSION.tar.xz
    fi
    
    if [ ! -f "linux-$KERNEL_VERSION/.fully_extracted" ]; then
        echo "Extracting kernel source..."
        rm -rf linux-$KERNEL_VERSION
        tar -xf linux-$KERNEL_VERSION.tar.xz
        touch linux-$KERNEL_VERSION/.fully_extracted
    fi
    
    cd linux-$KERNEL_VERSION
    cp ../../../configs/kernel.config .config
    
    make ARCH=x86 olddefconfig
    make ARCH=x86 -j$(nproc) bzImage
    make ARCH=x86 -j$(nproc) modules
    cd ../../../
fi
echo "Kernel build complete."
""",

    "scripts/2_build_rootfs.sh": """#!/bin/bash
set -e
ROOTFS="build/rootfs"

if [ ! -d "$ROOTFS/etc" ]; then
    echo "Bootstrapping Debian rootfs..."
    debootstrap --variant=minbase --arch=amd64 bookworm $ROOTFS http://deb.debian.org/debian/
fi

mount -t proc /proc $ROOTFS/proc || true
mount -t sysfs /sys $ROOTFS/sys || true
mount -o bind /dev $ROOTFS/dev || true
trap 'umount $ROOTFS/dev 2>/dev/null; umount $ROOTFS/sys 2>/dev/null; umount $ROOTFS/proc 2>/dev/null || true' EXIT

# HUGE FIX: Add PyQt WebEngine, SVG Support, PCI Utils, and Process Utils
chroot $ROOTFS /bin/bash -c "apt-get update && apt-get --fix-broken install -y && apt-get install -y --fix-missing \
    xserver-xorg xserver-xorg-video-all xserver-xorg-video-vmware xserver-xorg-video-fbdev xserver-xorg-video-vesa \
    xserver-xorg-input-libinput xinit openbox wmctrl xdotool x11-utils \
    python3 python3-pyqt6 python3-pyqt6.qtwebengine python3-pyqt6.qtsvg libqt6svg6 pciutils psmisc wget curl \
    libxcb-cursor0 libxkbcommon-x11-0 fonts-dejavu \
    dbus udev kmod nano iproute2 wine64 picom ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* /var/tmp/* /var/log/*"

mkdir -p $ROOTFS/root/Desktop $ROOTFS/root/Downloads $ROOTFS/root/Documents $ROOTFS/root/Pictures $ROOTFS/root/Music $ROOTFS/root/Videos

mkdir -p $ROOTFS/etc/X11
cat << 'EOF' > $ROOTFS/etc/X11/xorg.conf
Section "Device"
    Identifier "Fallback_Screen"
    Driver "fbdev"
EndSection
EOF

rm -f $ROOTFS/init
cat << 'EOF' > $ROOTFS/init
#!/bin/bash
export PATH=/sbin:/usr/sbin:/bin:/usr/bin
export QTWEBENGINE_DISABLE_SANDBOX=1
mount -t proc none /proc; mount -t sysfs none /sys; mount -t devtmpfs none /dev; mount -t tmpfs none /tmp; mount -t tmpfs none /run
mkdir -p /tmp/.X11-unix; chmod 1777 /tmp/.X11-unix
hostname crevix
echo "🧠 Booting CrevixRust OS 0.3 with Uzi Engine 2.0..."
modprobe vmwgfx 2>/dev/null; modprobe fbdev 2>/dev/null
/lib/systemd/systemd-udevd --daemon; udevadm trigger; udevadm settle
mkdir -p /run/dbus; dbus-uuidgen > /etc/machine-id; dbus-daemon --system --fork

mkdir -p /etc/xdg/openbox
cat << 'OB' > /etc/xdg/openbox/rc.xml
<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc" xmlns:xi="http://www.w3.org/2001/XInclude">
  <theme><keepBorder>no</keepBorder><name>Clearlooks</name><titleLayout>N</titleLayout></theme>
  <applications><application class="*"><decor>no</decor></application></applications>
</openbox_config>
OB

cat << 'OB_AUTO' > /etc/xdg/openbox/autostart
picom -b &
python3 /usr/share/crevix/desktop/main.py &
OB_AUTO
chmod +x /etc/xdg/openbox/autostart

export DISPLAY=:0
xinit /usr/bin/openbox-session -- /usr/bin/Xorg vt1 -keeptty -config /etc/X11/xorg.conf

echo "⚠️ UI Exited. Dropping to shell..."
while true; do setsid sh -c 'exec bash </dev/tty1 >/dev/tty1 2>&1'; done
EOF
chmod +x $ROOTFS/init

rm -f $ROOTFS/sbin/reboot $ROOTFS/sbin/poweroff
echo -e '#!/bin/bash\nsync\necho b > /proc/sysrq-trigger' > $ROOTFS/sbin/reboot
echo -e '#!/bin/bash\nsync\necho o > /proc/sysrq-trigger' > $ROOTFS/sbin/poweroff
chmod +x $ROOTFS/sbin/reboot $ROOTFS/sbin/poweroff
""",

    "scripts/3_install_desktop.sh": """#!/bin/bash
set -e
ROOTFS="build/rootfs"
DESKTOP_DIR="$ROOTFS/usr/share/crevix/desktop"

mkdir -p $DESKTOP_DIR
cp -r src/desktop/* $DESKTOP_DIR/
chmod +x $DESKTOP_DIR/main.py

echo "Desktop Environment installed to rootfs."
""",

    "scripts/4_make_iso.sh": """#!/bin/bash
set -e
ROOTFS="build/rootfs"
ISO_DIR="build/iso"
KERNEL_DIR="build/kernel/linux-6.6.10"

mkdir -p $ISO_DIR/boot/grub/themes
wget -qO catppuccin.zip https://github.com/catppuccin/grub/archive/refs/heads/main.zip
unzip -qo catppuccin.zip
cp -r grub-main/src/catppuccin-mocha-grub-theme $ISO_DIR/boot/grub/themes/mocha
rm -rf catppuccin.zip grub-main

sed -i 's/title-text: ""/title-text: "Rust Official Kernel Booter"/g' $ISO_DIR/boot/grub/themes/mocha/theme.txt

cd $ROOTFS
find . -print0 | cpio --null -H newc -o | gzip -9 > ../iso/boot/initrd.img
cd ../../
cp $KERNEL_DIR/arch/x86/boot/bzImage $ISO_DIR/boot/vmlinuz

cat << 'EOF' > $ISO_DIR/boot/grub/grub.cfg
insmod all_video
set gfxmode=1024x768x32,auto
set gfxpayload=keep
terminal_output gfxterm
loadfont /boot/grub/themes/mocha/font.pf2
set theme=/boot/grub/themes/mocha/theme.txt
export theme
set timeout=5
set default=0

menuentry "🧠 CrevixRust OS 0.3 - Uzi Engine 2.0" --class linux --class os {
    linux /boot/vmlinuz quiet loglevel=3 rdinit=/init
    initrd /boot/initrd.img
}
EOF

grub-mkrescue -o build/CrevixRust_OS.iso $ISO_DIR
echo "ISO Assembly complete: build/CrevixRust_OS.iso"
""",

    # ==========================================================================
    # 3. KERNEL CONFIGURATION
    # ==========================================================================
    "configs/kernel.config": """CONFIG_64BIT=y
CONFIG_SMP=y
CONFIG_DRM_VMWGFX=y
CONFIG_FB=y
CONFIG_FB_VESA=y
CONFIG_FB_EFI=y
CONFIG_FRAMEBUFFER_CONSOLE=y
CONFIG_INPUT=y
CONFIG_INPUT_EVDEV=y
CONFIG_INPUT_KEYBOARD=y
CONFIG_KEYBOARD_ATKBD=y
CONFIG_INPUT_MOUSE=y
CONFIG_MOUSE_PS2=y
CONFIG_NET=y
CONFIG_INET=y
CONFIG_UNIX=y
CONFIG_EXT4_FS=y
CONFIG_BINFMT_ELF=y
CONFIG_BINFMT_SCRIPT=y
CONFIG_VT=y
CONFIG_DEVTMPFS=y
CONFIG_DEVTMPFS_MOUNT=y
CONFIG_BLK_DEV_INITRD=y
CONFIG_RD_GZIP=y
CONFIG_PROC_FS=y
CONFIG_SYSFS=y
CONFIG_MAGIC_SYSRQ=y
""",

    # ==========================================================================
    # 4. PYTHON DESKTOP ENVIRONMENT & UZI ENGINE 2.0 UI FRAMEWORK
    # ==========================================================================
    "src/desktop/crevix_ui.py": """#!/usr/bin/env python3
import sys, os, traceback, json
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtSvg import QSvgRenderer

# --- UZI ENGINE 2.0 SVG ASSET SYSTEM ---
SVG_ICONS = {
    "start": '<svg viewBox="0 0 24 24" fill="none" stroke="CURRENT_COLOR" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/><path d="M2 12h20"/></svg>',
    "folder": '<svg viewBox="0 0 24 24" fill="none" stroke="CURRENT_COLOR" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>',
    "settings": '<svg viewBox="0 0 24 24" fill="none" stroke="CURRENT_COLOR" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    "terminal": '<svg viewBox="0 0 24 24" fill="none" stroke="CURRENT_COLOR" stroke-width="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>',
    "gpumate": '<svg viewBox="0 0 24 24" fill="none" stroke="CURRENT_COLOR" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    "appcenter": '<svg viewBox="0 0 24 24" fill="none" stroke="CURRENT_COLOR" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>',
    "browser": '<svg viewBox="0 0 24 24" fill="none" stroke="CURRENT_COLOR" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
    "hub": '<svg viewBox="0 0 24 24" fill="none" stroke="CURRENT_COLOR" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>',
    "desktop": '<svg viewBox="0 0 24 24" fill="none" stroke="CURRENT_COLOR" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>',
    "media": '<svg viewBox="0 0 24 24" fill="none" stroke="CURRENT_COLOR" stroke-width="2"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="17" x2="22" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/></svg>',
    "close": '<svg viewBox="0 0 24 24" fill="none" stroke="CURRENT_COLOR" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'
}

def get_svg_icon(name, color="#ffffff", size=32):
    svg = SVG_ICONS.get(name, SVG_ICONS["folder"]).replace('CURRENT_COLOR', color)
    renderer = QSvgRenderer(svg.encode('utf-8'))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

def global_exception_handler(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    msg = QMessageBox(); msg.setIcon(QMessageBox.Icon.Critical); msg.setWindowTitle("Uzi Engine Error")
    msg.setText("The OS caught a bug safely!"); msg.setDetailedText(error_msg); msg.exec()
sys.excepthook = global_exception_handler

def get_theme():
    try:
        with open("/tmp/crevix_theme.json", "r") as f: return json.load(f).get("mode", "dark")
    except: return "dark"

def get_palette():
    return {"bg": "#1e1e2e", "fg": "#cdd6f4", "acc": "#89b4fa", "tb": "#11111b", "btn": "#313244", "hov": "#45475a"} if get_theme() == "dark" else {"bg": "#f5f5f5", "fg": "#111111", "acc": "#005fb8", "tb": "#e0e0e0", "btn": "#d0d0d0", "hov": "#bdbdbd"}

def apply_global_style(app_instance):
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    p = get_palette()
    app_instance.setStyleSheet(f\"\"\"
        QWidget {{ background-color: {p['bg']}; color: {p['fg']}; font-family: 'Segoe UI', 'Arial'; }}
        QPushButton {{ background-color: {p['btn']}; border: none; border-radius: 12px; padding: 8px 16px; font-weight: bold; }}
        QPushButton:hover {{ background-color: {p['hov']}; }}
        QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {{ background-color: {p['tb']}; border: 1px solid {p['btn']}; border-radius: 10px; padding: 6px; }}
        QScrollBar:vertical {{ border: none; background: transparent; width: 8px; margin: 0; }}
        QScrollBar::handle:vertical {{ background: {p['btn']}; border-radius: 4px; min-height: 20px; }}
        QListView, QTreeView, QTableWidget {{ border: none; border-radius: 12px; background-color: {p['tb']}; padding: 5px; }}
    \"\"\")

class CustomTitleBar(QWidget):
    def __init__(self, parent, title="App"):
        super().__init__(parent); self.parent = parent; self.setFixedHeight(40); p = get_palette()
        self.setStyleSheet(f"background-color: {p['tb']}; border-top-left-radius: 16px; border-top-right-radius: 16px;")
        layout = QHBoxLayout(self); layout.setContentsMargins(15,0,10,0)
        self.lbl = QLabel(title); self.lbl.setStyleSheet("font-weight: bold; font-size: 14px; background: transparent;")
        layout.addWidget(self.lbl); layout.addStretch()
        
        btn_style = f"background: transparent; color: {p['fg']}; font-weight: bold; font-size: 14px; border-radius: 12px; padding: 4px;"
        self.btn_min = QPushButton("—"); self.btn_min.setFixedSize(32, 32); self.btn_min.setStyleSheet(btn_style); self.btn_min.clicked.connect(self.parent.showMinimized)
        self.btn_max = QPushButton("☐"); self.btn_max.setFixedSize(32, 32); self.btn_max.setStyleSheet(btn_style); self.btn_max.clicked.connect(self.toggle_max)
        self.btn_close = QPushButton(); self.btn_close.setIcon(get_svg_icon("close", p['fg'])); self.btn_close.setFixedSize(32, 32)
        self.btn_close.setStyleSheet(btn_style + "QPushButton:hover{background: #f38ba8; color: #111;}"); self.btn_close.clicked.connect(self.parent.close)
        layout.addWidget(self.btn_min); layout.addWidget(self.btn_max); layout.addWidget(self.btn_close)
        self.start_pos = None
    def toggle_max(self):
        if self.parent.isMaximized(): self.parent.showNormal()
        else: self.parent.showMaximized()
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton: self.start_pos = event.globalPosition().toPoint()
    def mouseMoveEvent(self, event):
        if self.start_pos is not None:
            delta = event.globalPosition().toPoint() - self.start_pos
            self.parent.move(self.parent.pos() + delta)
            self.start_pos = event.globalPosition().toPoint()
    def mouseReleaseEvent(self, event): self.start_pos = None

class CrevixWindow(QMainWindow):
    def __init__(self, title="App", width=800, height=600):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(width, height)
        
        self.main_widget = QWidget(self)
        p = get_palette()
        self.main_widget.setStyleSheet(f"background-color: {p['bg']}; border-radius: 16px; border: 1px solid {p['btn']};")
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0,0,0,0); self.main_layout.setSpacing(0)
        
        self.titlebar = CustomTitleBar(self, title)
        self.main_layout.addWidget(self.titlebar)
        
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(15,15,15,15)
        self.main_layout.addWidget(self.content_area)
        self.setCentralWidget(self.main_widget)
""",

    "src/desktop/main.py": """#!/usr/bin/env python3
import sys, os, subprocess
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from crevix_ui import apply_global_style, get_palette, get_svg_icon

class RotatingLogo(QWidget):
    def __init__(self, pixmap_path):
        super().__init__()
        self.setFixedSize(200, 200)
        if os.path.exists(pixmap_path):
            self.pixmap = QPixmap(pixmap_path).scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        else:
            self.pixmap = QPixmap()
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.spin)
        self.timer.start(20) # 50fps spin

    def spin(self):
        self.angle = (self.angle + 5) % 360
        self.update()

    def paintEvent(self, event):
        if self.pixmap.isNull(): return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.translate(100, 100)
        painter.rotate(self.angle)
        painter.translate(-100, -100)
        painter.drawPixmap(0, 0, self.pixmap)

class BootScreen(QWidget):
    def __init__(self, parent_os):
        super().__init__()
        self.parent_os = parent_os
        self.setStyleSheet("background-color: #020617;") # Deep dark slate
        layout = QVBoxLayout(self)
        
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        self.spinner = RotatingLogo(logo_path)
        
        layout.addStretch()
        layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        
        lbl = QLabel("Starting CrevixRust 0.3..."); 
        lbl.setStyleSheet("color: #89b4fa; font-size: 20px; font-weight: bold; margin-top: 30px;")
        layout.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        
        # Spin for 3 seconds then boot
        QTimer.singleShot(3000, self.finish_boot)

    def finish_boot(self):
        self.parent_os.stack.setCurrentIndex(1) # Go to LoginScreen

class LoginScreen(QWidget):
    def __init__(self, parent_os):
        super().__init__()
        self.parent_os = parent_os
        layout = QVBoxLayout(self)
        self.bg = QLabel(self)
        
        wp_path = "/tmp/crevix_wp.txt"
        img_path = open(wp_path, 'r').read().strip() if os.path.exists(wp_path) else os.path.join(os.path.dirname(__file__), "wallpaper.png")
        if os.path.exists(img_path):
            self.bg.setPixmap(QPixmap(img_path).scaled(QApplication.primaryScreen().geometry().width(), QApplication.primaryScreen().geometry().height(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
            self.bg.setScaledContents(True)
        else: self.bg.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e1e2e, stop:1 #11111b);")
        
        layout.addWidget(self.bg)
        
        center_widget = QWidget(self.bg)
        center_widget.setStyleSheet("background: rgba(17, 17, 27, 0.7); border-radius: 20px; backdrop-filter: blur(20px);")
        center_widget.setFixedSize(400, 300)
        center_layout = QVBoxLayout(center_widget)
        
        user_lbl = QLabel("Welcome to CrevixRust")
        user_lbl.setStyleSheet("font-size: 26px; font-weight: bold; color: #89b4fa; text-align: center; background: transparent;")
        user_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.pwd_input = QLineEdit()
        self.pwd_input.setPlaceholderText("Enter Password")
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.setStyleSheet("background: rgba(49, 50, 68, 0.8); color: white; padding: 12px; border-radius: 12px; font-size: 16px;")
        self.pwd_input.returnPressed.connect(self.login)
        
        btn = QPushButton("Login")
        btn.setStyleSheet("background: #89b4fa; color: #111; padding: 12px; border-radius: 12px; font-size: 16px; font-weight: bold;")
        btn.clicked.connect(self.login)
        
        center_layout.addStretch()
        center_layout.addWidget(user_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.pwd_input)
        center_layout.addWidget(btn)
        center_layout.addStretch()
        
        main_h = QHBoxLayout(); main_h.addStretch(); main_h.addWidget(center_widget); main_h.addStretch()
        main_v = QVBoxLayout(); main_v.addStretch(); main_v.addLayout(main_h); main_v.addStretch()
        self.bg.setLayout(main_v)
        layout.setContentsMargins(0,0,0,0)

    def login(self):
        self.parent_os.stack.setCurrentIndex(2) # Go to Desktop
        QTimer.singleShot(500, lambda: subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "apps", "welcome.py")]))

class DesktopSelection(QRubberBand):
    def __init__(self, parent=None): super().__init__(QRubberBand.Shape.Rectangle, parent)

class StartMenu(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setFixedSize(450, 550); self.hide()
        p = get_palette(); fg = p['fg']
        self.setStyleSheet(f"background-color: rgba({int(p['tb'][1:3],16)}, {int(p['tb'][3:5],16)}, {int(p['tb'][5:7],16)}, 230); border-radius: 20px; border: 1px solid {p['btn']}; backdrop-filter: blur(20px);")
        layout = QVBoxLayout(self); layout.setContentsMargins(25,25,25,25)
        lbl = QLabel("Uzi Engine 2.0 Start"); lbl.setStyleSheet(f"font-size: 26px; font-weight: 900; color: {p['acc']}; background: transparent;")
        layout.addWidget(lbl)
        
        grid = QGridLayout(); grid.setSpacing(15)
        apps = [
            ("Parallax", "parallax.py", "folder"), ("Ozmo Browser", "ozmo.py", "browser"),
            ("AppCenter", "appcenter.py", "appcenter"), ("GPUMate System", "gpumate.py", "gpumate"), 
            ("Settings", "settings.py", "settings"), ("Terminal", "terminal.py", "terminal"),
            ("FEO Hub", "feoservices.py", "hub")
        ]
        for i, (name, script, icon_name) in enumerate(apps):
            btn = QPushButton(f"  {name}"); btn.setFixedHeight(50)
            btn.setIcon(get_svg_icon(icon_name, fg)); btn.setIconSize(QSize(24,24))
            btn.setStyleSheet(f"background: {p['btn']}; border-radius: 12px; font-size: 15px; text-align: left; padding-left: 15px;")
            btn.clicked.connect(lambda _, s=script: self.launch(s))
            grid.addWidget(btn, i//2, i%2)
        layout.addLayout(grid); layout.addStretch()
        
    def launch(self, script):
        subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "apps", script)])
        self.hide()

class Taskbar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setFixedHeight(60); p = get_palette()
        self.setStyleSheet(f"background-color: rgba({int(p['tb'][1:3],16)}, {int(p['tb'][3:5],16)}, {int(p['tb'][5:7],16)}, 210); border-top: 1px solid {p['btn']}; backdrop-filter: blur(15px);")
        self.layout = QHBoxLayout(self); self.layout.setContentsMargins(20, 0, 20, 0)
        
        self.start_btn = QPushButton(); self.start_btn.setFixedSize(45, 45)
        self.start_btn.setIcon(get_svg_icon("start", "#11111b", 28)); self.start_btn.setIconSize(QSize(28,28))
        self.start_btn.setStyleSheet(f"background-color: {p['acc']}; border-radius: 22px;")
        self.layout.addWidget(self.start_btn)
        
        self.app_area = QHBoxLayout(); self.layout.addLayout(self.app_area); self.layout.addStretch()
        
        self.clock_label = QLabel(); self.clock_label.setStyleSheet("font-weight: 800; font-size: 15px; background: transparent;")
        self.layout.addWidget(self.clock_label)
        self.timer = QTimer(self); self.timer.timeout.connect(self.update_time); self.timer.start(1000); self.update_time()
        
    def update_time(self): self.clock_label.setText(QTime.currentTime().toString('hh:mm ap'))

class DesktopEnvironment(QWidget):
    def __init__(self, parent_os):
        super().__init__()
        self.parent_os = parent_os
        self.layout = QVBoxLayout(self); self.layout.setContentsMargins(0,0,0,0); self.layout.setSpacing(0)
        
        self.desktop_area = QLabel()
        self.desktop_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desktop_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        wp_path = "/tmp/crevix_wp.txt"
        img_path = open(wp_path, 'r').read().strip() if os.path.exists(wp_path) else os.path.join(os.path.dirname(__file__), "wallpaper.png")
        if os.path.exists(img_path):
            self.desktop_area.setPixmap(QPixmap(img_path).scaled(QApplication.primaryScreen().geometry().width(), QApplication.primaryScreen().geometry().height(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
            self.desktop_area.setScaledContents(True)
        else: self.desktop_area.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #11111b, stop:1 #313244);")
        
        self.layout.addWidget(self.desktop_area, 1)
        self.taskbar = Taskbar(self); self.layout.addWidget(self.taskbar, 0)
        
        self.start_menu = StartMenu(self)
        self.taskbar.start_btn.clicked.connect(self.toggle_start)
        self.rubberBand = DesktopSelection(self.desktop_area); self.origin = QPoint()

    def toggle_start(self):
        if self.start_menu.isHidden():
            self.start_menu.move(15, self.height() - self.taskbar.height() - self.start_menu.height() - 15)
            self.start_menu.show()
        else: self.start_menu.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.pos().y() < self.height() - 60:
            self.origin = event.pos(); self.rubberBand.setGeometry(QRect(self.origin, QSize())); self.rubberBand.show()
            self.start_menu.hide()
    def mouseMoveEvent(self, event):
        if not self.origin.isNull(): self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())
    def mouseReleaseEvent(self, event): self.rubberBand.hide()

class MainOSWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        screen_geom = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geom)
        self.setFixedSize(screen_geom.width(), screen_geom.height())
        
        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)
        
        self.boot_screen = BootScreen(self)
        self.login_screen = LoginScreen(self)
        self.desktop_env = DesktopEnvironment(self)
        
        self.stack.addWidget(self.boot_screen)
        self.stack.addWidget(self.login_screen)
        self.stack.addWidget(self.desktop_env)

if __name__ == '__main__':
    app = QApplication(sys.argv); apply_global_style(app)
    os_window = MainOSWindow(); os_window.show()
    sys.exit(app.exec())
""",

    "src/desktop/apps/ozmo.py": """#!/usr/bin/env python3
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from crevix_ui import CrevixWindow, apply_global_style, get_palette, get_svg_icon
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtWebEngineWidgets import QWebEngineView

class OzmoBrowser(CrevixWindow):
    def __init__(self):
        super().__init__("Ozmo Browser", 1000, 700)
        p = get_palette()
        
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.setStyleSheet(f"QTabBar::tab {{ background: {p['tb']}; border-radius: 8px; padding: 8px 15px; margin: 2px; }} QTabBar::tab:selected {{ background: {p['btn']}; color: {p['acc']}; font-weight: bold; }}")
        
        nav_bar = QHBoxLayout()
        btn_style = f"background: transparent; padding: 5px; border-radius: 8px;"
        
        back_btn = QPushButton("←"); back_btn.setStyleSheet(btn_style); back_btn.clicked.connect(lambda: self.current_browser().back())
        fwd_btn = QPushButton("→"); fwd_btn.setStyleSheet(btn_style); fwd_btn.clicked.connect(lambda: self.current_browser().forward())
        rel_btn = QPushButton("↻"); rel_btn.setStyleSheet(btn_style); rel_btn.clicked.connect(lambda: self.current_browser().reload())
        
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Search the web or enter URL...")
        self.url_bar.returnPressed.connect(self.navigate)
        
        new_tab_btn = QPushButton("+"); new_tab_btn.setStyleSheet(btn_style); new_tab_btn.clicked.connect(lambda: self.add_tab("https://duckduckgo.com"))
        
        nav_bar.addWidget(back_btn); nav_bar.addWidget(fwd_btn); nav_bar.addWidget(rel_btn)
        nav_bar.addWidget(self.url_bar); nav_bar.addWidget(new_tab_btn)
        
        self.content_layout.addLayout(nav_bar)
        self.content_layout.addWidget(self.tabs)
        
        self.add_tab("https://duckduckgo.com", "New Tab")
        
    def add_tab(self, url, label="Loading..."):
        browser = QWebEngineView()
        browser.setUrl(QUrl(url))
        i = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(i)
        browser.urlChanged.connect(lambda qurl, browser=browser: self.update_url(qurl, browser))
        browser.titleChanged.connect(lambda title, browser=browser: self.update_title(title, browser))

    def close_tab(self, i):
        if self.tabs.count() < 2: return
        self.tabs.removeTab(i)

    def current_browser(self): return self.tabs.currentWidget()

    def navigate(self):
        url = self.url_bar.text()
        if not url.startswith("http"):
            if "." in url and " " not in url: url = "http://" + url
            else: url = "https://duckduckgo.com/?q=" + url.replace(" ", "+")
        self.current_browser().setUrl(QUrl(url))

    def update_url(self, qurl, browser):
        if browser == self.current_browser(): self.url_bar.setText(qurl.toString())

    def update_title(self, title, browser):
        index = self.tabs.indexOf(browser)
        if index != -1: self.tabs.setTabText(index, title[:15] + "..." if len(title) > 15 else title)

if __name__ == '__main__': app = QApplication(sys.argv); apply_global_style(app); w = OzmoBrowser(); w.show(); sys.exit(app.exec())
""",

    "src/desktop/apps/appcenter.py": """#!/usr/bin/env python3
import sys, os, subprocess, threading
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from crevix_ui import CrevixWindow, apply_global_style, get_palette, get_svg_icon
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt

class AppCenter(CrevixWindow):
    def __init__(self):
        super().__init__("Crevix AppCenter", 800, 600)
        p = get_palette()
        
        header = QHBoxLayout()
        lbl = QLabel("🛒 Software Repository")
        lbl.setStyleSheet("font-size: 24px; font-weight: 900;")
        header.addWidget(lbl); header.addStretch()
        self.content_layout.addLayout(header)
        
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        container = QWidget(); vbox = QVBoxLayout(container); vbox.setSpacing(15)
        
        self.apps = [
            {"name": "Discord", "desc": "Communication Client", "url": "https://discord.com/api/download?platform=linux&format=deb", "type": "deb"},
            {"name": "VS Code", "desc": "Code Editor", "url": "https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-x64", "type": "deb"},
            {"name": "Firefox", "desc": "Web Browser", "url": "https://download.mozilla.org/?product=firefox-latest-ssl&os=linux64&lang=en-US", "type": "tar"},
            {"name": "GIMP", "desc": "Image Editor", "url": "https://download.gimp.org/gimp/v3.2/linux/GIMP-3.2.4-x86_64.AppImage", "type": "appimage"}
        ]
        
        for app in self.apps:
            card = QFrame()
            card.setStyleSheet(f"background: {p['tb']}; border-radius: 16px; padding: 15px;")
            card_layout = QHBoxLayout(card)
            
            info = QVBoxLayout()
            title = QLabel(app['name']); title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {p['acc']};")
            subtitle = QLabel(app['desc']); subtitle.setStyleSheet("font-size: 14px;")
            info.addWidget(title); info.addWidget(subtitle)
            
            btn = QPushButton("Install")
            btn.setFixedSize(120, 40)
            btn.clicked.connect(lambda _, a=app, b=btn: self.install_app(a, b))
            
            card_layout.addLayout(info); card_layout.addStretch(); card_layout.addWidget(btn)
            vbox.addWidget(card)
            
        vbox.addStretch()
        scroll.setWidget(container)
        self.content_layout.addWidget(scroll)

    def install_app(self, app, btn):
        btn.setText("Installing...")
        btn.setEnabled(False)
        btn.setStyleSheet("background: #f38ba8; color: #111; font-weight: bold; border-radius: 12px;")
        
        def run_install():
            try:
                if app['type'] == 'deb':
                    os.system(f"wget -qO /tmp/temp.deb '{app['url']}' && dpkg -i /tmp/temp.deb")
                elif app['type'] == 'appimage':
                    os.system(f"wget -qO /root/Desktop/{app['name']}.AppImage '{app['url']}' && chmod +x /root/Desktop/{app['name']}.AppImage")
                elif app['type'] == 'tar':
                    os.system(f"wget -qO /tmp/temp.tar.bz2 '{app['url']}' && tar -xf /tmp/temp.tar.bz2 -C /opt/")
            except Exception as e: print(e)
            
        threading.Thread(target=run_install).start()
        QMessageBox.information(self, "Installing", f"{app['name']} is downloading and installing in the background.")

if __name__ == '__main__': app = QApplication(sys.argv); apply_global_style(app); w = AppCenter(); w.show(); sys.exit(app.exec())
""",

    "src/desktop/apps/gpumate.py": """#!/usr/bin/env python3
import sys, os, subprocess
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from crevix_ui import CrevixWindow, apply_global_style, get_palette
from PyQt6.QtWidgets import *
from PyQt6.QtCore import QTimer

class GPUMate(CrevixWindow):
    def __init__(self):
        super().__init__("GPUMate System Task Manager", 700, 600)
        p = get_palette()
        
        header = QLabel("System Performance"); header.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.content_layout.addWidget(header)
        
        self.cpu_bar = QProgressBar(); self.cpu_bar.setFixedHeight(20)
        self.mem_bar = QProgressBar(); self.mem_bar.setFixedHeight(20)
        self.content_layout.addWidget(QLabel("CPU Usage:")); self.content_layout.addWidget(self.cpu_bar)
        self.content_layout.addWidget(QLabel("Memory Usage:")); self.content_layout.addWidget(self.mem_bar)
        
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["PID", "Process Name", "CPU %", "MEM %"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.content_layout.addWidget(self.table)
        
        btn_kill = QPushButton("☠️ Kill Task")
        btn_kill.setStyleSheet("background: #f38ba8; color: #111;")
        btn_kill.clicked.connect(self.kill_task)
        self.content_layout.addWidget(btn_kill)
        
        self.timer = QTimer(); self.timer.timeout.connect(self.update_stats); self.timer.start(2000)
        self.update_stats()
        
    def update_stats(self):
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
                tot = int(lines[0].split()[1]); free = int(lines[1].split()[1])
                self.mem_bar.setValue(int(((tot-free)/tot)*100))
        except: pass
        
        try:
            output = subprocess.check_output(['ps', '-e', '-o', 'pid,comm,%cpu,%mem', '--sort=-%mem'], text=True).strip().split('\\n')[1:20]
            self.table.setRowCount(0)
            cpu_total = 0.0
            for i, line in enumerate(output):
                parts = line.split()
                if len(parts) >= 4:
                    self.table.insertRow(i)
                    self.table.setItem(i, 0, QTableWidgetItem(parts[0]))
                    self.table.setItem(i, 1, QTableWidgetItem(parts[1]))
                    self.table.setItem(i, 2, QTableWidgetItem(parts[2]))
                    self.table.setItem(i, 3, QTableWidgetItem(parts[3]))
                    try: cpu_total += float(parts[2])
                    except: pass
            self.cpu_bar.setValue(min(int(cpu_total), 100))
        except Exception as e: print(e)

    def kill_task(self):
        row = self.table.currentRow()
        if row >= 0:
            pid = self.table.item(row, 0).text()
            os.system(f"kill -9 {pid}")
            QMessageBox.information(self, "Terminated", f"Task {pid} executed successfully.")
            self.update_stats()

if __name__ == '__main__': app = QApplication(sys.argv); apply_global_style(app); w = GPUMate(); w.show(); sys.exit(app.exec())
""",

    "src/desktop/apps/settings.py": """#!/usr/bin/env python3
import sys, os, json, subprocess
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from crevix_ui import CrevixWindow, apply_global_style, get_palette, get_svg_icon
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt

class SettingsApp(CrevixWindow):
    def __init__(self):
        super().__init__("Settings", 850, 600)
        p = get_palette()
        hlayout = QHBoxLayout(); self.content_layout.addLayout(hlayout)
        
        self.sidebar = QListWidget(); self.sidebar.setFixedWidth(220)
        self.sidebar.setStyleSheet(f"background: {p['tb']}; border-radius: 12px; font-size: 15px; padding: 10px;")
        for item in ["🏠 Home", "🖥️ Display", "📊 Specifications", "🎨 Customization", "ℹ️ About"]: 
            i = QListWidgetItem(item); self.sidebar.addItem(i)
        self.sidebar.currentRowChanged.connect(self.change_tab)
        hlayout.addWidget(self.sidebar)
        
        self.stack = QStackedWidget(); hlayout.addWidget(self.stack)
        
        # 1. Home
        w1 = QWidget(); l1 = QVBoxLayout(w1); l1.addWidget(QLabel("<h2>PC Overview</h2><p>Welcome to your CrevixRust OS Machine.</p><p>Status: Excellent</p>")); l1.addStretch(); self.stack.addWidget(w1)
        
        # 2. Display
        w2 = QWidget(); l2 = QVBoxLayout(w2)
        vga_info = subprocess.getoutput("lspci | grep VGA") if os.path.exists("/usr/bin/lspci") else "Generic VESA/FBDEV Fallback"
        l2.addWidget(QLabel(f"<h2>Display Info</h2><p><b>Resolution:</b> Auto-Scaled X11 Framebuffer</p><p><b>Driver:</b> vmwgfx / fbdev</p><p><b>GPU Hardware:</b> {vga_info}</p>"))
        l2.addStretch(); self.stack.addWidget(w2)
        
        # 3. Specs
        w_specs = QWidget(); l_specs = QVBoxLayout(w_specs)
        cpu_info = subprocess.getoutput("cat /proc/cpuinfo | grep 'model name' | head -1").replace("model name\\t:", "").strip()
        mem_info = subprocess.getoutput("cat /proc/meminfo | head -3")
        l_specs.addWidget(QLabel(f"<h2>System Specifications</h2><p><b>CPU:</b> {cpu_info}</p><p><b>Memory Details:</b><br><pre>{mem_info}</pre></p><p><b>Kernel:</b> Linux 6.6.10 Official Rust Booter</p>"))
        l_specs.addStretch(); self.stack.addWidget(w_specs)

        # 4. Customization
        w3 = QWidget(); l3 = QVBoxLayout(w3)
        l3.addWidget(QLabel("<h2>Appearance & Wallpaper</h2>"))
        btn_dark = QPushButton("🌙 Set Dark Mode"); btn_dark.clicked.connect(lambda: self.set_theme("dark"))
        btn_light = QPushButton("☀️ Set Light Mode"); btn_light.clicked.connect(lambda: self.set_theme("light"))
        
        btn_wp = QPushButton("🖼️ Choose Custom Wallpaper")
        btn_wp.clicked.connect(self.pick_wallpaper)
        
        l3.addWidget(btn_dark); l3.addWidget(btn_light); l3.addWidget(QLabel("<hr>")); l3.addWidget(btn_wp)
        l3.addStretch(); self.stack.addWidget(w3)
        
        # 5. About
        w4 = QWidget(); l4 = QVBoxLayout(w4)
        l4.addWidget(QLabel("<h2>About CrevixRust OS</h2><p><b>Version:</b> 0.3 Massive Engine Update</p><p><b>Creator:</b> FEOServices</p><p>We reinvented the wheel by replacing bloated Desktop Environments with pure Python.</p>"))
        l4.addStretch()
        uzi_lbl = QLabel("UI systems made with Uzi Engine 2.0")
        uzi_lbl.setStyleSheet("color: #89b4fa; font-weight: 900; font-size: 16px;")
        l4.addWidget(uzi_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(w4)
        
    def change_tab(self, i): self.stack.setCurrentIndex(i)
    
    def set_theme(self, mode):
        with open("/tmp/crevix_theme.json", "w") as f: json.dump({"mode": mode}, f)
        QMessageBox.information(self, "Theme Changed", "Theme updated. Relaunch apps to see changes.")

    def pick_wallpaper(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Wallpaper", "/root", "Images (*.png *.jpg *.jpeg)")
        if file:
            with open("/tmp/crevix_wp.txt", "w") as f: f.write(file)
            QMessageBox.information(self, "Wallpaper Set", "Wallpaper applied! Please restart your desktop session.")

if __name__ == '__main__': app = QApplication(sys.argv); apply_global_style(app); w = SettingsApp(); w.show(); sys.exit(app.exec())
""",

    "src/desktop/apps/parallax.py": """#!/usr/bin/env python3
import sys, os, subprocess, datetime
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from crevix_ui import CrevixWindow, apply_global_style, get_palette, get_svg_icon
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

class ParallaxExplorer(CrevixWindow):
    def __init__(self):
        super().__init__("Parallax File Explorer (Remastered)", 950, 650)
        p = get_palette()
        fg = p['fg']
        
        main_h = QHBoxLayout(); self.content_layout.addLayout(main_h)
        
        # --- SIDEBAR ---
        self.sidebar = QListWidget(); self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet(f"background: {p['tb']}; border-radius: 12px; font-weight: bold; font-size: 14px; padding: 5px;")
        
        folders = [("Desktop", "desktop"), ("Downloads", "folder"), ("Documents", "folder"), ("Pictures", "media"), ("Music", "media"), ("Videos", "media")]
        for name, icon in folders:
            item = QListWidgetItem(f"  {name}"); item.setIcon(get_svg_icon(icon, fg)); item.setData(Qt.ItemDataRole.UserRole, f"/root/{name}")
            self.sidebar.addItem(item)
            
        pc_item = QListWidgetItem("  My PC"); pc_item.setIcon(get_svg_icon("gpumate", p['acc'])); pc_item.setData(Qt.ItemDataRole.UserRole, "/")
        self.sidebar.addItem(pc_item)
        self.sidebar.itemClicked.connect(self.nav_sidebar)
        main_h.addWidget(self.sidebar)
        
        # --- RIGHT PANEL ---
        right_v = QVBoxLayout()
        
        # Ribbon
        ribbon = QHBoxLayout()
        self.sort_combo = QComboBox(); self.sort_combo.addItems(["Sort: Name", "Sort: Size", "Sort: Type", "Sort: Date Modified"])
        self.view_combo = QComboBox(); self.view_combo.addItems(["View: Details", "View: List", "View: Tiles", "View: Small Icons", "View: Medium Icons", "View: Large Icons", "View: EXTREMELY LARGE"])
        self.view_combo.currentIndexChanged.connect(self.change_view)
        
        self.path_bar = QLineEdit("/root/Desktop")
        self.path_bar.returnPressed.connect(lambda: self.load_path(self.path_bar.text()))
        
        ribbon.addWidget(self.path_bar); ribbon.addWidget(self.sort_combo); ribbon.addWidget(self.view_combo)
        right_v.addLayout(ribbon)
        
        # Main View
        self.model = QFileSystemModel()
        self.model.setRootPath('/root/Desktop')
        
        self.list_view = QListView()
        self.list_view.setModel(self.model)
        self.list_view.setRootIndex(self.model.index('/root/Desktop'))
        self.list_view.setViewMode(QListView.ViewMode.IconMode)
        self.list_view.setIconSize(QSize(64, 64))
        self.list_view.setSpacing(10)
        self.list_view.doubleClicked.connect(self.open_file)
        
        right_v.addWidget(self.list_view)
        main_h.addLayout(right_v)

    def nav_sidebar(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        self.path_bar.setText(path)
        self.load_path(path)
        
    def load_path(self, path):
        if os.path.exists(path):
            self.list_view.setRootIndex(self.model.index(path))

    def change_view(self, index):
        mode = self.view_combo.currentText()
        if "Details" in mode or "List" in mode:
            self.list_view.setViewMode(QListView.ViewMode.ListMode)
        else:
            self.list_view.setViewMode(QListView.ViewMode.IconMode)
            if "Small" in mode: self.list_view.setIconSize(QSize(32, 32))
            elif "Medium" in mode: self.list_view.setIconSize(QSize(64, 64))
            elif "Large" in mode: self.list_view.setIconSize(QSize(128, 128))
            elif "EXTREMELY" in mode: self.list_view.setIconSize(QSize(256, 256))

    def open_file(self, index):
        path = self.model.filePath(index)
        if os.path.isdir(path):
            self.path_bar.setText(path); self.load_path(path)
            return
            
        ext = os.path.splitext(path)[1].lower()
        if ext in ['.txt', '.json', '.md', '.cfg']: subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "text_editor.py"), path])
        elif ext in ['.py']: subprocess.Popen([sys.executable, path])
        elif ext in ['.sh']: os.system(f"chmod +x {path} && {path} &")
        elif ext in ['.png', '.jpg', '.jpeg']: subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "image_viewer.py"), path])
        elif ext == '.exe': subprocess.Popen(['wine64', path])
        elif ext == '.appimage': os.system(f"chmod +x {path} && {path} &")
        elif os.access(path, os.X_OK): subprocess.Popen([path])
        else: QMessageBox.warning(self, "Execution Engine", "Format unrecognized. Attempting generic execution.")

if __name__ == '__main__': app = QApplication(sys.argv); apply_global_style(app); w = ParallaxExplorer(); w.show(); sys.exit(app.exec())
""",

    "src/desktop/apps/welcome.py": """#!/usr/bin/env python3
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from crevix_ui import CrevixWindow, apply_global_style
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt
class WelcomeApp(CrevixWindow):
    def __init__(self):
        super().__init__("Welcome to CrevixRust", 600, 450)
        lbl = QLabel("🚀 Welcome to CrevixRust OS 0.3"); lbl.setStyleSheet("font-size: 26px; font-weight: bold; color: #89b4fa;")
        desc = QLabel("Experience the ultimate blend of custom Python UI on a pristine Linux Kernel.\\n\\nNew in 0.3:\\n- Uzi Engine 2.0 Vector Graphics\\n- Ozmo Web Browser\\n- GPUMate Task Manager\\n- Parallax Remastered")
        desc.setWordWrap(True); desc.setStyleSheet("font-size: 16px;")
        btn = QPushButton("Dive In"); btn.setFixedHeight(45); btn.clicked.connect(self.close)
        self.content_layout.addStretch(); self.content_layout.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(desc, alignment=Qt.AlignmentFlag.AlignCenter); self.content_layout.addStretch()
        self.content_layout.addWidget(btn)
if __name__ == '__main__': app = QApplication(sys.argv); apply_global_style(app); w = WelcomeApp(); w.show(); sys.exit(app.exec())
""",

    "src/desktop/apps/text_editor.py": """#!/usr/bin/env python3
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from crevix_ui import CrevixWindow, apply_global_style
from PyQt6.QtWidgets import *
class TextEditor(CrevixWindow):
    def __init__(self, filepath=None):
        title = f"Text Editor - {os.path.basename(filepath)}" if filepath else "Text Editor"
        super().__init__(title, 700, 500)
        self.filepath = filepath
        
        toolbar = QHBoxLayout(); self.content_layout.addLayout(toolbar)
        btn_save = QPushButton("💾 Save"); btn_save.clicked.connect(self.save_file); toolbar.addWidget(btn_save)
        btn_bold = QPushButton("B"); btn_bold.setStyleSheet("font-weight: bold;"); btn_bold.clicked.connect(lambda: self.editor.setFontWeight(75))
        toolbar.addWidget(btn_bold); toolbar.addStretch()
        
        self.editor = QTextEdit(); self.content_layout.addWidget(self.editor)
        if filepath and os.path.exists(filepath):
            with open(filepath, 'r') as f: self.editor.setPlainText(f.read())
            
    def save_file(self):
        if not self.filepath: self.filepath, _ = QFileDialog.getSaveFileName(self, "Save File")
        if self.filepath:
            with open(self.filepath, 'w') as f: f.write(self.editor.toPlainText())
            QMessageBox.information(self, "Saved", "File saved successfully!")
if __name__ == '__main__': app = QApplication(sys.argv); apply_global_style(app); fp = sys.argv[1] if len(sys.argv) > 1 else None; w = TextEditor(fp); w.show(); sys.exit(app.exec())
""",

    "src/desktop/apps/image_viewer.py": """#!/usr/bin/env python3
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from crevix_ui import CrevixWindow, apply_global_style
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
class ImageViewer(CrevixWindow):
    def __init__(self, filepath=None):
        super().__init__("Image Viewer", 800, 600)
        self.lbl = QLabel("No Image Selected"); self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.lbl)
        if filepath and os.path.exists(filepath):
            pix = QPixmap(filepath)
            self.lbl.setPixmap(pix.scaled(750, 550, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
if __name__ == '__main__': app = QApplication(sys.argv); apply_global_style(app); fp = sys.argv[1] if len(sys.argv) > 1 else None; w = ImageViewer(fp); w.show(); sys.exit(app.exec())
""",

    "src/desktop/apps/terminal.py": """#!/usr/bin/env python3
import sys, os, subprocess
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from crevix_ui import CrevixWindow, apply_global_style
from PyQt6.QtWidgets import *
class Terminal(CrevixWindow):
    def __init__(self):
        super().__init__("Crevix Terminal", 700, 450)
        self.output = QTextEdit(); self.output.setReadOnly(True); self.output.setStyleSheet("background: rgba(0,0,0,0.8); color: #0f0; font-family: monospace;")
        self.content_layout.addWidget(self.output)
        
        self.input = QLineEdit(); self.input.setStyleSheet("background: #222; color: #0f0; font-family: monospace; border: none;")
        self.input.returnPressed.connect(self.run_cmd)
        self.content_layout.addWidget(self.input)
        self.output.append("Uzi Engine Terminal v2.0\\nType a command...")

    def run_cmd(self):
        cmd = self.input.text(); self.input.clear()
        if not cmd: return
        self.output.append(f"\\nroot@crevix:~# {cmd}")
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.stdout: self.output.append(res.stdout.strip())
            if res.stderr: self.output.append(res.stderr.strip())
        except Exception as e: self.output.append(str(e))
if __name__ == '__main__': app = QApplication(sys.argv); apply_global_style(app); w = Terminal(); w.show(); sys.exit(app.exec())
""",

    "src/desktop/apps/feoservices.py": """#!/usr/bin/env python3
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from crevix_ui import CrevixWindow, apply_global_style
from PyQt6.QtWidgets import *
class FEOServices(CrevixWindow):
    def __init__(self):
        super().__init__("FEOServices Hub", 600, 400)
        self.main_widget.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(137, 180, 250, 0.8), stop:1 rgba(30, 30, 46, 0.9)); border-radius: 15px;")
        html = \"\"\"
        <div style='text-align: center; color: white; font-family: Arial; padding: 20px;'>
            <h1 style='font-size: 36px; text-shadow: 2px 2px 5px rgba(0,0,0,0.5);'>FEOServices</h1>
            <p style='font-size: 18px;'>The visionary parent company behind CrevixCore and CrevixRust OS.</p>
            <br>
            <div style='background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.2);'>
                <b>Status:</b> Operational<br>
                <b>Engine:</b> Uzi Engine 2.0
            </div>
        </div>
        \"\"\"
        browser = QTextBrowser(); browser.setStyleSheet("background: transparent; border: none;"); browser.setHtml(html)
        self.content_layout.addWidget(browser)
if __name__ == '__main__': app = QApplication(sys.argv); apply_global_style(app); w = FEOServices(); w.show(); sys.exit(app.exec())
"""
}

def create_workspace():
    print(f"[*] Creating {workspace_name} workspace...")
    if not os.path.exists(workspace_name):
        os.makedirs(workspace_name)
    
    for filepath, content in files.items():
        full_path = os.path.join(workspace_name, filepath)
        directory = os.path.dirname(full_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        with open(full_path, "w", encoding="utf-8", newline='\n') as f:
            f.write(content)
        if filepath.endswith(".sh") or filepath.endswith(".py"):
            os.chmod(full_path, os.stat(full_path).st_mode | stat.S_IEXEC)
        print(f"  --> Created: {filepath}")

    print("\\n[*] DONE! Workspace updated to CrevixRust 0.3 with Uzi Engine 2.0. Fucking awesome capabilities deployed.")

if __name__ == "__main__":
    create_workspace()
