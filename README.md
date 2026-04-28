# 电玩店房间计时程序

轻量版电玩店房间计时系统，使用 Python 标准库（tkinter + sqlite3）编写，**无需安装任何数据库服务**。

A lightweight video-game-store room timer written in Python.  
Uses only the standard library (`tkinter` + `sqlite3`) — **no database installation required**.

---

## 功能 / Features

| 功能 | 说明 |
|---|---|
| 添加 / 删除房间 | 管理门店所有计时房间 |
| 开始 / 结束计时 | 一键启停，自动记录开始时间 |
| 实时显示 | 每秒刷新已用时间与当前费用 |
| 历史记录 | 查看所有已完成消费记录，支持清空 |
| 价格设置 | 可随时调整每小时单价 |
| 本地存储 | 数据保存在同目录 `videogame.db`（SQLite） |

---

## 环境要求 / Requirements

- Python 3.9 +
- tkinter（通常随 Python 自带；Ubuntu/Debian 可执行 `sudo apt install python3-tk`）

---

## 运行方式 / Run

```bash
python main.py
```

---

## 文件说明 / Project Structure

```
videogame/
├── main.py        # GUI 主程序
├── db.py          # SQLite 数据库操作
├── videogame.db   # 运行后自动生成的本地数据库
└── README.md
```
