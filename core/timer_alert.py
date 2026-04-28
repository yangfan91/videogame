"""
语音提醒模块
使用 Windows 内置 SAPI（Speech API）进行语音播报。
无需额外安装依赖，Windows 系统自带。
"""
import threading
import subprocess
import sys


def _speak_windows(text: str):
    """使用 PowerShell + SAPI 播放语音（Windows 专用）"""
    try:
        # 转义单引号
        safe_text = text.replace("'", "''")
        script = (
            f"Add-Type -AssemblyName System.Speech; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Rate = -2; "
            f"$s.Speak('{safe_text}');"
        )
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-Command", script],
            creationflags=subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
    except Exception:
        pass  # 语音失败不影响主程序


def speak(text: str):
    """
    异步播放语音，不阻塞 UI 线程。

    Args:
        text: 要播报的文字
    """
    t = threading.Thread(target=_speak_windows, args=(text,), daemon=True)
    t.start()


def alert_expired(device_name: str):
    """包厢时间到提醒"""
    speak(f"{device_name}，时间到，请及时结账。")


def alert_warning(device_name: str, remaining_minutes: int):
    """包厢即将到时提醒"""
    if remaining_minutes <= 1:
        speak(f"{device_name}，还剩不到一分钟，请准备结账。")
    else:
        speak(f"{device_name}，还剩{remaining_minutes}分钟。")
