"""
时长工具模块（v2）
移除计费逻辑，仅保留时长格式化工具函数。
"""


def format_duration(total_seconds: int) -> str:
    """
    将秒数格式化为 HH:MM:SS 字符串。

    Args:
        total_seconds: 总秒数（非负）

    Returns:
        格式化字符串，如 "01:23:45"
    """
    total_seconds = max(0, int(total_seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_duration_readable(total_seconds: int) -> str:
    """
    将秒数格式化为可读字符串，如 "1小时23分45秒"。

    Args:
        total_seconds: 总秒数

    Returns:
        可读格式字符串
    """
    total_seconds = max(0, int(total_seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分")
    parts.append(f"{seconds}秒")
    return "".join(parts)


def parse_minutes_to_seconds(minutes: float) -> int:
    """
    将分钟数转换为秒数（用于套餐时长输入）。

    Args:
        minutes: 分钟数（支持小数，如 90.5 = 90分30秒）

    Returns:
        秒数（整数）
    """
    return max(0, int(minutes * 60))
