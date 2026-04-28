"""
计时引擎模块（v2）
支持两种模式：
  - countdown（美团套餐）：倒计时，到时发出 expired 信号
  - freeplay（自由计时）：正计时，无限制
"""
from datetime import datetime
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from core.billing import format_duration
from config import TIMER_INTERVAL_MS, TimerMode, COUNTDOWN_WARNING_SECS


class TimerEngine(QObject):
    """
    单包厢计时引擎。

    Signals:
        tick(elapsed_seconds, remaining_seconds):
            每秒触发。
            - freeplay 模式：remaining_seconds = -1
            - countdown 模式：remaining_seconds = 剩余秒数（可为负，表示超时）
        expired():
            countdown 模式倒计时归零时触发（只触发一次）
        warning(remaining_seconds):
            countdown 模式剩余时间低于警告阈值时触发（只触发一次）
    """

    tick    = pyqtSignal(int, int)   # (elapsed_seconds, remaining_seconds)
    expired = pyqtSignal()
    warning = pyqtSignal(int)        # remaining_seconds

    def __init__(self, device_id: int,
                 mode: str = TimerMode.FREEPLAY,
                 countdown_seconds: int = 0,
                 parent=None):
        super().__init__(parent)
        self.device_id = device_id
        self.mode = mode
        self.countdown_seconds = countdown_seconds   # 套餐总秒数

        # 会话状态
        self.session_id: int = -1
        self.start_time: datetime | None = None
        self.pause_duration: int = 0        # 累计暂停秒数
        self._pause_start: datetime | None = None
        self._is_running: bool = False
        self._is_paused: bool = False
        self._expired_emitted: bool = False
        self._warning_emitted: bool = False

        # QTimer
        self._timer = QTimer(self)
        self._timer.setInterval(TIMER_INTERVAL_MS)
        self._timer.timeout.connect(self._on_tick)

    # ─────────────────────────────────────────
    # 公开接口
    # ─────────────────────────────────────────

    def start(self, session_id: int,
              mode: str | None = None,
              countdown_seconds: int | None = None,
              start_time: datetime | None = None,
              pause_duration: int = 0):
        """
        开始或恢复计时（用于新会话或程序重启后恢复）。

        Args:
            session_id:         数据库会话 ID
            mode:               计时模式（None 则使用初始化时的模式）
            countdown_seconds:  套餐总秒数（None 则使用初始化时的值）
            start_time:         会话开始时间（None 表示当前时间）
            pause_duration:     已累计的暂停秒数（恢复时使用）
        """
        self.session_id = session_id
        if mode is not None:
            self.mode = mode
        if countdown_seconds is not None:
            self.countdown_seconds = countdown_seconds
        self.start_time = start_time or datetime.now()
        self.pause_duration = pause_duration
        self._is_running = True
        self._is_paused = False
        self._pause_start = None
        self._expired_emitted = False
        self._warning_emitted = False
        self._timer.start()

    def pause(self):
        """暂停计时"""
        if self._is_running and not self._is_paused:
            self._pause_start = datetime.now()
            self._is_paused = True
            self._timer.stop()

    def resume(self, extra_pause_seconds: int = 0):
        """
        恢复计时。

        Args:
            extra_pause_seconds: 从数据库重新计算的暂停秒数（精确值，0 则本地计算）
        """
        if self._is_running and self._is_paused:
            if extra_pause_seconds > 0:
                self.pause_duration = extra_pause_seconds
            elif self._pause_start:
                paused = int((datetime.now() - self._pause_start).total_seconds())
                self.pause_duration += paused
            self._pause_start = None
            self._is_paused = False
            self._timer.start()

    def stop(self) -> int:
        """
        停止计时，返回 elapsed_seconds（实际使用秒数）。
        """
        self._timer.stop()
        self._is_running = False
        self._is_paused = False
        return self.get_elapsed_seconds()

    def add_time(self, extra_seconds: int):
        """
        为倒计时模式增加时长（续费套餐）。

        Args:
            extra_seconds: 新增秒数
        """
        if self.mode != TimerMode.COUNTDOWN or extra_seconds <= 0:
            return
        self.countdown_seconds += extra_seconds
        # 重置到时标志，让计时继续
        self._expired_emitted = False
        # 如果新的剩余时间超过警告阈值，允许再次触发警告
        if self.get_remaining_seconds() > COUNTDOWN_WARNING_SECS:
            self._warning_emitted = False
        # 若 QTimer 因暂停之外的原因停止了，重新启动
        if self._is_running and not self._is_paused and not self._timer.isActive():
            self._timer.start()

    def reset(self):
        """重置引擎状态（结算完成后调用）"""
        self._timer.stop()
        self.session_id = -1
        self.start_time = None
        self.pause_duration = 0
        self._pause_start = None
        self._is_running = False
        self._is_paused = False
        self._expired_emitted = False
        self._warning_emitted = False

    # ─────────────────────────────────────────
    # 状态查询
    # ─────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._is_running and not self._is_paused

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def is_active(self) -> bool:
        """是否有进行中的会话（包括暂停状态）"""
        return self._is_running

    def get_elapsed_seconds(self) -> int:
        """获取实际使用秒数（已扣除暂停时长）"""
        if self.start_time is None:
            return 0
        total = int((datetime.now() - self.start_time).total_seconds())
        current_pause = 0
        if self._is_paused and self._pause_start:
            current_pause = int((datetime.now() - self._pause_start).total_seconds())
        return max(0, total - self.pause_duration - current_pause)

    def get_remaining_seconds(self) -> int:
        """
        获取剩余秒数（仅 countdown 模式有意义）。
        返回值可为负（表示超时）。
        freeplay 模式返回 -1。
        """
        if self.mode == TimerMode.FREEPLAY:
            return -1
        return self.countdown_seconds - self.get_elapsed_seconds()

    def get_display_time(self) -> str:
        """
        获取格式化的显示时间：
        - freeplay：正计时 HH:MM:SS
        - countdown：剩余时间 HH:MM:SS（超时显示 -HH:MM:SS）
        """
        if self.mode == TimerMode.FREEPLAY:
            return format_duration(self.get_elapsed_seconds())
        else:
            remaining = self.get_remaining_seconds()
            if remaining >= 0:
                return format_duration(remaining)
            else:
                return f"-{format_duration(abs(remaining))}"

    # ─────────────────────────────────────────
    # 内部槽
    # ─────────────────────────────────────────

    def _on_tick(self):
        """每秒触发，发射 tick 信号，检查倒计时到时"""
        elapsed = self.get_elapsed_seconds()
        remaining = self.get_remaining_seconds()

        # 发射 tick
        self.tick.emit(elapsed, remaining)

        # countdown 模式：检查警告和到时
        if self.mode == TimerMode.COUNTDOWN:
            if (not self._warning_emitted
                    and 0 < remaining <= COUNTDOWN_WARNING_SECS):
                self._warning_emitted = True
                self.warning.emit(remaining)

            if not self._expired_emitted and remaining <= 0:
                self._expired_emitted = True
                self.expired.emit()
