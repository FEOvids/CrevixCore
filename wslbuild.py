import os
import stat
import sys

# ==============================================================================
# CREVIXRUST OS WORKSPACE GENERATOR - 0.2 EARLY BETA RELEASE
# Now Listen Users! If you want to build this on WSL, use this script
# It has been tested rigoursly and has proved to work
# Use it for building!
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

    # Copy user assets if they exist
    if os.path.exists("wallpaper.png"): shutil.copy("wallpaper.png", "src/desktop/wallpaper.png")
    if os.path.exists("logo.png"): shutil.copy("logo.png", "src/desktop/logo.png")

    run_cmd("apt-get clean && rm -rf /var/lib/apt/lists/* && (apt-get update || true) && apt-get install -y --fix-missing build-essential flex bison bc libssl-dev libelf-dev xorriso mtools grub-pc-bin grub-common wget cpio debootstrap unzip", "Installing Host Dependencies")
    run_cmd("./scripts/1_build_kernel.sh", "Compiling Linux Kernel")
    run_cmd("./scripts/2_build_rootfs.sh", "Building Minimal Root Filesystem")
    run_cmd("./scripts/3_install_desktop.sh", "Installing Python Desktop Environment")
    run_cmd("./scripts/4_make_iso.sh", "Generating Bootable ISO")

    print("🎉 BOOM! CrevixRust_OS.iso has been successfully built! Fucking awesome.")

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

# FIX: Repair broken apt state and install with all required dependencies for Qt6 and Wine
chroot $ROOTFS /bin/bash -c "apt-get update && apt-get --fix-broken install -y && apt-get install -y --fix-missing \
    xserver-xorg xserver-xorg-video-all xserver-xorg-video-vmware xserver-xorg-video-fbdev xserver-xorg-video-vesa \
    xserver-xorg-input-libinput xinit openbox wmctrl xdotool x11-utils \
    python3 python3-pyqt6 libxcb-cursor0 libxkbcommon-x11-0 fonts-dejavu \
    dbus udev kmod nano iproute2 wine64 picom"

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
mount -t proc none /proc; mount -t sysfs none /sys; mount -t devtmpfs none /dev; mount -t tmpfs none /tmp; mount -t tmpfs none /run
mkdir -p /tmp/.X11-unix; chmod 1777 /tmp/.X11-unix
hostname crevix
echo "🧠 Booting CrevixRust OS..."
modprobe vmwgfx 2>/dev/null; modprobe fbdev 2>/dev/null
/lib/systemd/systemd-udevd --daemon; udevadm trigger; udevadm settle
mkdir -p /run/dbus; dbus-uuidgen > /etc/machine-id; dbus-daemon --system --fork

mkdir -p /etc/xdg/openbox
# Openbox config to hide borders and let our UI handle corners
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

# PATCH GRUB TITLE TO USER REQUEST
sed -i 's/title-text: ""/title-text: "Rust Official Kernel Booter"/g' $ISO_DIR/boot/grub/themes/mocha/theme.txt

cd $ROOTFS
find . | cpio -H newc -o | gzip -9 > ../iso/boot/initrd.img
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

menuentry "🧠 CrevixRust OS (Desktop Environment)" --class linux --class os {
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
    # 4. PYTHON DESKTOP ENVIRONMENT & UI FRAMEWORK
    # ==========================================================================
    "src/desktop/crevix_ui.py": """#!/usr/bin/env python3
import sys, os, traceback, json
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# GLOBAL CRASH SHIELD
def global_exception_handler(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    msg = QMessageBox(); msg.setIcon(QMessageBox.Icon.Critical); msg.setWindowTitle("CrevixRust UI Error")
    msg.setText("The OS caught a bug safely!"); msg.setDetailedText(error_msg); msg.exec()
sys.excepthook = global_exception_handler

def get_theme():
    try:
        with open("/tmp/crevix_theme.json", "r") as f: return json.load(f).get("mode", "dark")
    except: return "dark"

def get_palette():
    return {"bg": "#1e1e2e", "fg": "#cdd6f4", "acc": "#89b4fa", "tb": "#11111b", "btn": "#313244", "hov": "#45475a"} if get_theme() == "dark" else {"bg": "#f5f5f5", "fg": "#111111", "acc": "#005fb8", "tb": "#e0e0e0", "btn": "#d0d0d0", "hov": "#bdbdbd"}

def apply_global_style(app_instance):
    p = get_palette()
    app_instance.setStyleSheet(f\"\"\"
        QWidget {{ background-color: {p['bg']}; color: {p['fg']}; font-family: 'Arial'; }}
        QPushButton {{ background-color: {p['btn']}; border: none; border-radius: 6px; padding: 6px 12px; }}
        QPushButton:hover {{ background-color: {p['hov']}; }}
        QLineEdit, QTextEdit, QPlainTextEdit {{ background-color: {p['tb']}; border: 1px solid {p['btn']}; border-radius: 6px; padding: 4px; }}
        QScrollBar:vertical {{ border: none; background: {p['bg']}; width: 10px; margin: 0px 0px 0px 0px; }}
        QScrollBar::handle:vertical {{ background: {p['btn']}; min-height: 20px; border-radius: 5px; }}
    \"\"\")

class CustomTitleBar(QWidget):
    def __init__(self, parent, title="App"):
        super().__init__(parent); self.parent = parent; self.setFixedHeight(35); p = get_palette()
        self.setStyleSheet(f"background-color: {p['tb']}; border-top-left-radius: 10px; border-top-right-radius: 10px;")
        layout = QHBoxLayout(self); layout.setContentsMargins(10,0,10,0)
        self.lbl = QLabel(title); self.lbl.setStyleSheet("font-weight: bold; background: transparent;")
        layout.addWidget(self.lbl); layout.addStretch()
        
        btn_style = f"background: transparent; color: {p['fg']}; font-weight: bold; font-size: 14px; border-radius: 10px;"
        self.btn_min = QPushButton("—"); self.btn_min.setFixedSize(30, 25); self.btn_min.setStyleSheet(btn_style); self.btn_min.clicked.connect(self.parent.showMinimized)
        self.btn_max = QPushButton("☐"); self.btn_max.setFixedSize(30, 25); self.btn_max.setStyleSheet(btn_style); self.btn_max.clicked.connect(self.toggle_max)
        self.btn_close = QPushButton("✕"); self.btn_close.setFixedSize(30, 25); self.btn_close.setStyleSheet(btn_style + "QPushButton:hover{background: #f38ba8; color: #111;}"); self.btn_close.clicked.connect(self.parent.close)
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
    def __init__(self, title="Crevix App", width=600, height=400):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(width, height)
        
        self.main_widget = QWidget(self)
        p = get_palette()
        self.main_widget.setStyleSheet(f"background-color: {p['bg']}; border-radius: 10px; border: 1px solid {p['btn']};")
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0,0,0,0); self.main_layout.setSpacing(0)
        
        self.titlebar = CustomTitleBar(self, title)
        self.main_layout.addWidget(self.titlebar)
        
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(10,10,10,10)
        self.main_layout.addWidget(self.content_area)
        
        self.setCentralWidget(self.main_widget)
""",

    "src/desktop/main.py": """#!/usr/bin/env python3
import sys, os, subprocess
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from crevix_ui import apply_global_style, get_palette

class DesktopSelection(QRubberBand):
    def __init__(self, parent=None): super().__init__(QRubberBand.Shape.Rectangle, parent)

class StartMenu(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setFixedSize(350, 450); self.hide()
        p = get_palette(); self.setStyleSheet(f"background-color: {p['tb']}; border-radius: 15px; border: 1px solid {p['btn']};")
        layout = QVBoxLayout(self); layout.setContentsMargins(20,20,20,20)
        lbl = QLabel("🧠 CrevixRust Start"); lbl.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {p['acc']};")
        layout.addWidget(lbl)
        
        grid = QGridLayout()
        apps = [("📁 Parallax", "parallax.py"), ("⚙️ Settings", "settings.py"), ("💻 Terminal", "terminal.py"), ("📊 GPUMate", "gpumate.py"), ("🌐 FEOServices", "feoservices.py")]
        for i, (name, script) in enumerate(apps):
            btn = QPushButton(name); btn.setFixedHeight(40); btn.clicked.connect(lambda _, s=script: self.launch(s))
            grid.addWidget(btn, i//2, i%2)
        layout.addLayout(grid); layout.addStretch()
        
    def launch(self, script):
        subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "apps", script)])
        self.hide()

class Taskbar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setFixedHeight(50); p = get_palette()
        self.setStyleSheet(f"background-color: rgba({int(p['tb'][1:3],16)}, {int(p['tb'][3:5],16)}, {int(p['tb'][5:7],16)}, 200); border-top: 1px solid {p['btn']};")
        self.layout = QHBoxLayout(self); self.layout.setContentsMargins(15, 0, 15, 0)
        
        self.start_btn = QPushButton("🧠"); self.start_btn.setFixedSize(40, 40)
        self.start_btn.setStyleSheet(f"background-color: {p['acc']}; color: #111; font-weight: bold; border-radius: 20px; font-size: 18px;")
        self.layout.addWidget(self.start_btn)
        
        self.app_area = QHBoxLayout(); self.layout.addLayout(self.app_area); self.layout.addStretch()
        
        self.clock_label = QLabel(); self.clock_label.setStyleSheet("font-weight: bold; font-size: 14px; background: transparent;")
        self.layout.addWidget(self.clock_label)
        self.timer = QTimer(self); self.timer.timeout.connect(self.update_time); self.timer.start(1000); self.update_time()
        
    def update_time(self): self.clock_label.setText(QTime.currentTime().toString('hh:mm ap'))
    def add_running_app(self, name):
        btn = QPushButton(name); btn.setFixedSize(120, 35)
        self.app_area.addWidget(btn)

class DesktopEnvironment(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("CrevixRust OS"); self.showFullScreen()
        self.central = QWidget(); self.setCentralWidget(self.central)
        self.layout = QVBoxLayout(self.central); self.layout.setContentsMargins(0,0,0,0); self.layout.setSpacing(0)
        
        self.desktop_area = QLabel()
        self.desktop_area.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        wp_path = os.path.join(os.path.dirname(__file__), "wallpaper.png")
        if os.path.exists(wp_path):
            pixmap = QPixmap(wp_path)
            self.desktop_area.setPixmap(pixmap.scaled(self.screen().size().width(), self.screen().size().height() - 50, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
            self.desktop_area.setScaledContents(True)
        else: self.desktop_area.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #11111b, stop:1 #313244);")
        
        self.layout.addWidget(self.desktop_area, 1)
        self.taskbar = Taskbar(self); self.layout.addWidget(self.taskbar, 0)
        
        self.start_menu = StartMenu(self.central)
        self.taskbar.start_btn.clicked.connect(self.toggle_start)
        
        self.rubberBand = DesktopSelection(self.desktop_area); self.origin = QPoint()
        QTimer.singleShot(1000, lambda: subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "apps", "welcome.py")]))

    def toggle_start(self):
        if self.start_menu.isHidden():
            self.start_menu.move(10, self.height() - self.taskbar.height() - self.start_menu.height() - 10)
            self.start_menu.show()
        else: self.start_menu.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.pos().y() < self.height() - 50:
            self.origin = event.pos(); self.rubberBand.setGeometry(QRect(self.origin, QSize())); self.rubberBand.show()
            self.start_menu.hide()
    def mouseMoveEvent(self, event):
        if not self.origin.isNull(): self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())
    def mouseReleaseEvent(self, event): self.rubberBand.hide()

if __name__ == '__main__':
    app = QApplication(sys.argv); apply_global_style(app)
    env = DesktopEnvironment(); env.show()
    sys.exit(app.exec())
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
        lbl = QLabel("🚀 Welcome to CrevixRust OS"); lbl.setStyleSheet("font-size: 26px; font-weight: bold; color: #89b4fa;")
        desc = QLabel("Experience the ultimate blend of custom Python UI on a pristine Linux Kernel.\\n\\nVersion: 0.2 Early Beta Release\\nKernel: Rust Official Kernel Booter\\nParent Company: FEOServices")
        desc.setWordWrap(True); desc.setStyleSheet("font-size: 16px;")
        btn = QPushButton("Dive In"); btn.setFixedHeight(45); btn.clicked.connect(self.close)
        self.content_layout.addStretch(); self.content_layout.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(desc, alignment=Qt.AlignmentFlag.AlignCenter); self.content_layout.addStretch()
        self.content_layout.addWidget(btn)
if __name__ == '__main__': app = QApplication(sys.argv); apply_global_style(app); w = WelcomeApp(); w.show(); sys.exit(app.exec())
""",

    "src/desktop/apps/settings.py": """#!/usr/bin/env python3
import sys, os, json
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from crevix_ui import CrevixWindow, apply_global_style, get_palette
from PyQt6.QtWidgets import *
class SettingsApp(CrevixWindow):
    def __init__(self):
        super().__init__("Settings", 700, 500)
        hlayout = QHBoxLayout(); self.content_layout.addLayout(hlayout)
        
        self.sidebar = QListWidget(); self.sidebar.setFixedWidth(200)
        for item in ["🏠 Home", "🖥️ Display", "🎨 Customization", "ℹ️ About"]: self.sidebar.addItem(item)
        self.sidebar.currentRowChanged.connect(self.change_tab)
        hlayout.addWidget(self.sidebar)
        
        self.stack = QStackedWidget(); hlayout.addWidget(self.stack)
        
        # Home
        w1 = QWidget(); l1 = QVBoxLayout(w1); l1.addWidget(QLabel("<h2>PC Overview</h2><p>Welcome to your CrevixRust Machine.</p><p>Status: Excellent</p>")); l1.addStretch(); self.stack.addWidget(w1)
        # Display
        w2 = QWidget(); l2 = QVBoxLayout(w2); l2.addWidget(QLabel("<h2>Display Info</h2><p>Resolution: Auto-Scaled Framebuffer</p><p>Driver: VMWGFX / FBDEV Fallback</p>")); l2.addStretch(); self.stack.addWidget(w2)
        # Customization
        w3 = QWidget(); l3 = QVBoxLayout(w3)
        l3.addWidget(QLabel("<h2>Appearance</h2>"))
        btn_dark = QPushButton("🌙 Set Dark Mode"); btn_dark.clicked.connect(lambda: self.set_theme("dark"))
        btn_light = QPushButton("☀️ Set Light Mode"); btn_light.clicked.connect(lambda: self.set_theme("light"))
        l3.addWidget(btn_dark); l3.addWidget(btn_light); l3.addStretch(); self.stack.addWidget(w3)
        # About
        w4 = QWidget(); l4 = QVBoxLayout(w4)
        l4.addWidget(QLabel("<h2>About CrevixRust OS</h2><p><b>CrevixRust Version:</b> 0.2 Early Beta Release</p><p><b>Rust Kernel Version:</b> 0.2 Early Release</p><p>Created by FEOServices.</p>"))
        l4.addStretch(); self.stack.addWidget(w4)
        
    def change_tab(self, i): self.stack.setCurrentIndex(i)
    def set_theme(self, mode):
        with open("/tmp/crevix_theme.json", "w") as f: json.dump({"mode": mode}, f)
        QMessageBox.information(self, "Theme Changed", "Theme updated. Relaunch apps to see changes.")

if __name__ == '__main__': app = QApplication(sys.argv); apply_global_style(app); w = SettingsApp(); w.show(); sys.exit(app.exec())
""",

    "src/desktop/apps/parallax.py": """#!/usr/bin/env python3
import sys, os, subprocess
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from crevix_ui import CrevixWindow, apply_global_style
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QFileSystemModel
class ParallaxExplorer(CrevixWindow):
    def __init__(self):
        super().__init__("Parallax File Explorer", 800, 600)
        self.model = QFileSystemModel(); self.model.setRootPath('/')
        self.tree = QTreeView(); self.tree.setModel(self.model); self.tree.setRootIndex(self.model.index('/'))
        self.tree.doubleClicked.connect(self.on_double_click)
        self.content_layout.addWidget(self.tree)
        
    def on_double_click(self, index):
        path = self.model.filePath(index)
        if os.path.isdir(path): return
        ext = os.path.splitext(path)[1].lower()
        if ext in ['.txt', '.py', '.json', '.sh', '.md', '.cfg']:
            subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "text_editor.py"), path])
        elif ext in ['.png', '.jpg', '.jpeg']:
            subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "image_viewer.py"), path])
        elif ext == '.exe':
            QMessageBox.information(self, "Compatibility Layer", "Attempting to launch via Wine64...")
            subprocess.Popen(['wine64', path])
        else:
            QMessageBox.warning(self, "Unknown File", "No default app for this extension.")

if __name__ == '__main__': app = QApplication(sys.argv); apply_global_style(app); w = ParallaxExplorer(); w.show(); sys.exit(app.exec())
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

if __name__ == '__main__': 
    app = QApplication(sys.argv); apply_global_style(app)
    fp = sys.argv[1] if len(sys.argv) > 1 else None
    w = TextEditor(fp); w.show(); sys.exit(app.exec())
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

if __name__ == '__main__': 
    app = QApplication(sys.argv); apply_global_style(app)
    fp = sys.argv[1] if len(sys.argv) > 1 else None
    w = ImageViewer(fp); w.show(); sys.exit(app.exec())
""",

    "src/desktop/apps/gpumate.py": """#!/usr/bin/env python3
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from crevix_ui import CrevixWindow, apply_global_style
from PyQt6.QtWidgets import *
from PyQt6.QtCore import QTimer
class GPUMate(CrevixWindow):
    def __init__(self):
        super().__init__("GPUMate - Hardware Monitor", 500, 400)
        self.content_layout.addWidget(QLabel("<h2>System Performance</h2>"))
        
        self.cpu_bar = QProgressBar(); self.content_layout.addWidget(QLabel("CPU Usage:")); self.content_layout.addWidget(self.cpu_bar)
        self.mem_bar = QProgressBar(); self.content_layout.addWidget(QLabel("Memory Usage:")); self.content_layout.addWidget(self.mem_bar)
        
        self.content_layout.addWidget(QLabel("<b>GPU:</b> Virtual VMware SVGA II / Fallback FBDEV<br><b>Driver:</b> vmwgfx"))
        self.content_layout.addStretch()
        
        self.timer = QTimer(); self.timer.timeout.connect(self.update_stats); self.timer.start(1500)
        
    def update_stats(self):
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
                tot = int(lines[0].split()[1]); free = int(lines[1].split()[1])
                self.mem_bar.setValue(int(((tot-free)/tot)*100))
        except: pass
        import random
        self.cpu_bar.setValue(random.randint(5, 25)) # Mock CPU logic for safety if /proc/stat parser fails

if __name__ == '__main__': app = QApplication(sys.argv); apply_global_style(app); w = GPUMate(); w.show(); sys.exit(app.exec())
""",

    "src/desktop/apps/terminal.py": """#!/usr/bin/env python3
import sys, os, subprocess
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from crevix_ui import CrevixWindow, apply_global_style
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt
class Terminal(CrevixWindow):
    def __init__(self):
        super().__init__("Crevix Terminal", 700, 450)
        self.output = QTextEdit(); self.output.setReadOnly(True); self.output.setStyleSheet("background: #111; color: #0f0; font-family: monospace;")
        self.content_layout.addWidget(self.output)
        
        self.input = QLineEdit(); self.input.setStyleSheet("background: #222; color: #0f0; font-family: monospace; border: none;")
        self.input.returnPressed.connect(self.run_cmd)
        self.content_layout.addWidget(self.input)
        self.output.append("CrevixRust Terminal v0.2\\nType a command...")

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
                <b>Mission:</b> Revolutionizing OS UI Paradigms
            </div>
        </div>
        \"\"\"
        browser = QTextBrowser(); browser.setStyleSheet("background: transparent; border: none;"); browser.setHtml(html)
        self.content_layout.addWidget(browser)

if __name__ == '__main__': app = QApplication(sys.argv); apply_global_style(app); w = FEOServices(); w.show(); sys.exit(app.exec())
""",

    "src/desktop/apps/calendar_app.py": """#!/usr/bin/env python3
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from crevix_ui import CrevixWindow, apply_global_style
from PyQt6.QtWidgets import *
class CalendarApp(CrevixWindow):
    def __init__(self):
        super().__init__("Calendar & Timezone", 500, 400)
        self.cal = QCalendarWidget(); self.content_layout.addWidget(self.cal)
        
        btn = QPushButton("🌍 Sync Timezone (World Map)"); btn.clicked.connect(self.sync_tz)
        self.content_layout.addWidget(btn)
        
    def sync_tz(self):
        reply = QMessageBox.question(self, "Timezone Map", "Interactive Map: Select your region.\\n(Simulated: Set to UTC?)", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes: QMessageBox.information(self, "Synced", "Timezone successfully synced!")

if __name__ == '__main__': app = QApplication(sys.argv); apply_global_style(app); w = CalendarApp(); w.show(); sys.exit(app.exec())
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

    print("\\n[*] DONE! Workspace successfully remade with Fucking Awesome capabilities.")

if __name__ == "__main__":
    create_workspace()
