#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电玩店房间计时程序
Video Game Store – Room Timer

使用方法 / Usage:
    python main.py

依赖 / Dependencies:
    仅使用 Python 标准库（tkinter + sqlite3），无需安装额外软件。
    Only Python standard library (tkinter + sqlite3) – no extra software needed.
"""

import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, simpledialog, ttk

import db


def _format_duration(seconds: float) -> str:
    """Return HH:MM:SS string for the given number of seconds."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class HistoryWindow(tk.Toplevel):
    """Popup window that shows all completed sessions."""

    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent)
        self.title("历史记录")
        self.geometry("820x420")
        self.resizable(True, True)
        self._build()

    def _build(self) -> None:
        frame = tk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        columns = ("room", "start", "end", "duration", "cost")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        tree.heading("room", text="房间")
        tree.heading("start", text="开始时间")
        tree.heading("end", text="结束时间")
        tree.heading("duration", text="时长 (分钟)")
        tree.heading("cost", text="费用 (元)")
        tree.column("room", width=120, anchor=tk.CENTER)
        tree.column("start", width=170)
        tree.column("end", width=170)
        tree.column("duration", width=110, anchor=tk.CENTER)
        tree.column("cost", width=100, anchor=tk.CENTER)

        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        for s in db.get_all_sessions():
            start_str = datetime.fromtimestamp(s["start_time"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            end_str = datetime.fromtimestamp(s["end_time"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            tree.insert(
                "",
                tk.END,
                values=(
                    s["room_name"],
                    start_str,
                    end_str,
                    f"{s['duration_minutes']:.1f}",
                    f"{s['cost']:.2f}",
                ),
            )

        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        tk.Button(
            btn_frame,
            text="清空历史",
            fg="red",
            command=lambda: self._clear(tree),
        ).pack(side=tk.LEFT)

    def _clear(self, tree: ttk.Treeview) -> None:
        if messagebox.askyesno("确认", "确定要清空所有历史记录吗？", parent=self):
            db.clear_sessions()
            tree.delete(*tree.get_children())


class App:
    """Main application window."""

    # Colours
    _BG_ACTIVE = "#c8f5c8"   # light green – room in use
    _BG_IDLE = "#ffffff"     # white – room free

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("电玩店计时系统")
        self.root.geometry("900x550")
        self.root.resizable(True, True)

        db.init_db()

        # Cache of room data: {room_id: dict}
        self._rooms: dict[int, dict] = {}

        self._build_toolbar()
        self._build_table()
        self._build_bottom_bar()

        self._load_rooms()
        self._tick()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_toolbar(self) -> None:
        bar = tk.Frame(self.root, bd=1, relief=tk.RAISED, bg="#e8e8e8")
        bar.pack(side=tk.TOP, fill=tk.X)

        btn_opts = dict(padx=6, pady=4)
        tk.Button(bar, text="➕ 添加房间", command=self._add_room).pack(
            side=tk.LEFT, **btn_opts
        )
        tk.Button(bar, text="🗑 删除房间", command=self._delete_room).pack(
            side=tk.LEFT, **btn_opts
        )
        tk.Button(bar, text="▶ 开始计时", bg="#4caf50", fg="white", command=self._start).pack(
            side=tk.LEFT, **btn_opts
        )
        tk.Button(bar, text="■ 结束计时", bg="#f44336", fg="white", command=self._stop).pack(
            side=tk.LEFT, **btn_opts
        )
        tk.Button(bar, text="📋 历史记录", command=self._view_history).pack(
            side=tk.LEFT, **btn_opts
        )
        tk.Button(bar, text="⚙ 价格设置", command=self._settings).pack(
            side=tk.LEFT, **btn_opts
        )

    def _build_table(self) -> None:
        container = tk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        cols = ("name", "status", "start_time", "elapsed", "cost")
        self._tree = ttk.Treeview(container, columns=cols, show="headings",
                                  selectmode="browse")

        self._tree.heading("name", text="房间名称")
        self._tree.heading("status", text="状态")
        self._tree.heading("start_time", text="开始时间")
        self._tree.heading("elapsed", text="已用时间")
        self._tree.heading("cost", text="费用 (元)")

        self._tree.column("name", width=160, anchor=tk.CENTER)
        self._tree.column("status", width=80, anchor=tk.CENTER)
        self._tree.column("start_time", width=200, anchor=tk.CENTER)
        self._tree.column("elapsed", width=130, anchor=tk.CENTER)
        self._tree.column("cost", width=110, anchor=tk.CENTER)

        sb = ttk.Scrollbar(container, orient=tk.VERTICAL,
                           command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._tree.tag_configure("active", background=self._BG_ACTIVE)
        self._tree.tag_configure("idle", background=self._BG_IDLE)

    def _build_bottom_bar(self) -> None:
        bar = tk.Frame(self.root, bd=1, relief=tk.SUNKEN, bg="#f0f0f0")
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        self._status_var = tk.StringVar(value="就绪")
        tk.Label(bar, textvariable=self._status_var, bg="#f0f0f0",
                 anchor=tk.W, padx=8).pack(fill=tk.X)

    # ── Data loading ───────────────────────────────────────────────────────────

    def _load_rooms(self) -> None:
        price = db.get_price_per_hour()
        now = time.time()

        self._tree.delete(*self._tree.get_children())
        self._rooms.clear()

        for room in db.get_all_rooms():
            rid = room["id"]
            self._rooms[rid] = dict(room)

            if room["status"] == 1 and room["start_time"]:
                elapsed = now - room["start_time"]
                start_str = datetime.fromtimestamp(room["start_time"]).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                elapsed_str = _format_duration(elapsed)
                cost_str = f"{(elapsed / 3600) * price:.2f}"
                tag = "active"
                status_str = "使用中 🟢"
            else:
                start_str = elapsed_str = cost_str = ""
                tag = "idle"
                status_str = "空闲"

            self._tree.insert(
                "",
                tk.END,
                iid=str(rid),
                values=(room["name"], status_str, start_str, elapsed_str, cost_str),
                tags=(tag,),
            )

        active = sum(1 for r in self._rooms.values() if r["status"] == 1)
        self._status_var.set(
            f"共 {len(self._rooms)} 间房  │  使用中 {active} 间  │  "
            f"空闲 {len(self._rooms) - active} 间  │  "
            f"单价 {price:.1f} 元/小时"
        )

    # ── Real-time tick ─────────────────────────────────────────────────────────

    def _tick(self) -> None:
        """Update elapsed time and cost every second for active rooms."""
        price = db.get_price_per_hour()
        now = time.time()
        for rid, room in self._rooms.items():
            if room["status"] == 1 and room["start_time"]:
                elapsed = now - room["start_time"]
                self._tree.set(str(rid), "elapsed", _format_duration(elapsed))
                self._tree.set(
                    str(rid), "cost", f"{(elapsed / 3600) * price:.2f}"
                )
        self.root.after(1000, self._tick)

    # ── Toolbar actions ────────────────────────────────────────────────────────

    def _add_room(self) -> None:
        name = simpledialog.askstring("添加房间", "请输入新房间名称:", parent=self.root)
        if not name or not name.strip():
            return
        try:
            db.add_room(name.strip())
            self._load_rooms()
        except Exception:
            messagebox.showerror("错误", f"房间 '{name.strip()}' 已存在！", parent=self.root)

    def _delete_room(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择要删除的房间", parent=self.root)
            return
        rid = int(sel[0])
        room = self._rooms.get(rid)
        if not room:
            return
        if room["status"] == 1:
            messagebox.showerror("错误", "房间正在使用中，无法删除！", parent=self.root)
            return
        if messagebox.askyesno("确认", f"确定要删除房间「{room['name']}」吗？", parent=self.root):
            db.delete_room(rid)
            self._load_rooms()

    def _start(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择要开始计时的房间", parent=self.root)
            return
        rid = int(sel[0])
        room = self._rooms.get(rid)
        if not room:
            return
        if room["status"] == 1:
            messagebox.showinfo("提示", "该房间已经在计时中！", parent=self.root)
            return
        db.start_room(rid, time.time())
        self._load_rooms()

    def _stop(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择要结束计时的房间", parent=self.root)
            return
        rid = int(sel[0])
        room = self._rooms.get(rid)
        if not room:
            return
        if room["status"] == 0:
            messagebox.showinfo("提示", "该房间当前没有在计时！", parent=self.root)
            return

        end_time = time.time()
        duration = end_time - room["start_time"]
        cost = (duration / 3600) * db.get_price_per_hour()

        db.stop_room(
            rid,
            room["name"],
            room["start_time"],
            end_time,
            duration / 60,
            cost,
        )

        messagebox.showinfo(
            "计时结束",
            f"房间：{room['name']}\n"
            f"使用时间：{_format_duration(duration)}\n"
            f"费用：{cost:.2f} 元",
            parent=self.root,
        )
        self._load_rooms()

    def _view_history(self) -> None:
        HistoryWindow(self.root)

    def _settings(self) -> None:
        current = db.get_price_per_hour()
        new_price = simpledialog.askfloat(
            "价格设置",
            f"请输入每小时费用（当前：{current:.1f} 元）：",
            minvalue=0.1,
            parent=self.root,
        )
        if new_price is not None:
            db.set_price_per_hour(new_price)
            messagebox.showinfo(
                "已保存", f"价格已更新为 {new_price:.2f} 元/小时", parent=self.root
            )
            self._load_rooms()


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
