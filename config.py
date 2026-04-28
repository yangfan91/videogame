"""
全局配置文件
"""
import os
import sys

# 应用信息
APP_NAME = "电玩店包厢计时系统"
APP_VERSION = "2.0.0"

# 路径配置
# PyInstaller 打包后 sys.frozen=True，exe 所在目录为 sys.executable 的父目录
# 开发模式下使用 __file__ 所在目录
if getattr(sys, 'frozen', False):
    # 打包后：数据库放在 exe 同目录下的 data/ 文件夹
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 开发模式：数据库放在项目根目录下的 data/ 文件夹
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RESOURCE_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
ASSETS_DIR = os.path.join(RESOURCE_DIR, "assets")
APP_ICON_PATH = os.path.join(ASSETS_DIR, "app_icon.png")
NAV_ICON_PATHS = {
    "device": os.path.join(ASSETS_DIR, "generated", "nav_console.png"),
    "stats": os.path.join(ASSETS_DIR, "generated", "nav_stats.png"),
    "settings": os.path.join(ASSETS_DIR, "generated", "nav_settings.png"),
}
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH  = os.path.join(DATA_DIR, "videogame.db")

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 计时器刷新间隔（毫秒）
TIMER_INTERVAL_MS = 1000

# 默认包厢类型
DEFAULT_DEVICE_TYPES = [
    {"name": "PS4包厢"},
    {"name": "PS5包厢"},
    {"name": "Xbox包厢"},
    {"name": "Switch包厢"},
    {"name": "其他包厢"},
]

# UI 颜色主题
DARK_COLORS = {
    "primary": "#0F172A",       # 深色标题/导航
    "secondary": "#38BDF8",     # 蓝色信息强调
    "accent": "#80F7FF",        # 暗色控制台主强调色
    "accent_text": "#08212A",   # 高亮蓝底按钮文字
    "success": "#22C55E",       # 绿色（空闲/成功）
    "warning": "#F59E0B",       # 琥珀色（暂停/即将到时）
    "danger": "#F43F5E",        # 红色（使用中/超时）
    "maintenance": "#64748B",   # 灰色（维护）
    "background": "#0B1118",    # 应用背景
    "surface": "#101822",       # 次级深色面
    "surface_alt": "#17212C",   # 控件深色面
    "card_bg": "#111821",       # 卡片背景
    "border": "#243040",        # 主边框
    "border_soft": "#17212C",   # 柔和分隔线
    "sidebar": "#080D13",       # 侧边栏
    "sidebar_muted": "#8A94A6", # 侧边栏弱文字
    "text_dark": "#F8FBFF",     # 主文字
    "text_light": "#FFFFFF",    # 浅色文字
    "text_muted": "#8A94A6",    # 弱文字
    "countdown": "#8B5CF6",     # 紫色（倒计时模式）
}

LIGHT_COLORS = {
    "primary": "#F8FAFC",
    "secondary": "#0284C7",
    "accent": "#0891B2",
    "accent_text": "#FFFFFF",
    "success": "#16A34A",
    "warning": "#D97706",
    "danger": "#E11D48",
    "maintenance": "#64748B",
    "background": "#F3F7FB",
    "surface": "#FFFFFF",
    "surface_alt": "#E8EEF5",
    "card_bg": "#FFFFFF",
    "border": "#CBD5E1",
    "border_soft": "#E2E8F0",
    "sidebar": "#FFFFFF",
    "sidebar_muted": "#64748B",
    "text_dark": "#0F172A",
    "text_light": "#FFFFFF",
    "text_muted": "#64748B",
    "countdown": "#7C3AED",
}

THEMES = {
    "dark": DARK_COLORS,
    "light": LIGHT_COLORS,
}
THEME_LABELS = {
    "dark": "深色",
    "light": "浅色",
}
CURRENT_THEME = "dark"
COLORS = DARK_COLORS.copy()


def set_theme(theme: str) -> str:
    """Update the shared color tokens in place and return the active theme."""
    global CURRENT_THEME
    if theme not in THEMES:
        theme = "dark"
    CURRENT_THEME = theme
    COLORS.clear()
    COLORS.update(THEMES[theme])
    return CURRENT_THEME


def toggle_theme() -> str:
    return set_theme("light" if CURRENT_THEME == "dark" else "dark")


def is_dark_theme() -> bool:
    return CURRENT_THEME == "dark"

# 计时模式
class TimerMode:
    COUNTDOWN = "countdown"   # 团购套餐倒计时
    FREEPLAY  = "freeplay"    # 自由计时（先玩后结账）

    LABELS = {
        COUNTDOWN: "团购套餐",
        FREEPLAY:  "自由计时",
    }

# 包厢状态
class DeviceStatus:
    IDLE        = "idle"
    ACTIVE      = "active"
    PAUSED      = "paused"
    EXPIRED     = "expired"      # 倒计时到时（未结束）
    MAINTENANCE = "maintenance"

    LABELS = {
        IDLE:        "空闲",
        ACTIVE:      "使用中",
        PAUSED:      "已暂停",
        EXPIRED:     "时间到！",
        MAINTENANCE: "维护中",
    }

# 会话状态
class SessionStatus:
    ACTIVE    = "active"
    PAUSED    = "paused"
    COMPLETED = "completed"

# 倒计时警告阈值（秒）：剩余时间低于此值时开始闪烁警告
COUNTDOWN_WARNING_SECS = 300   # 5分钟
