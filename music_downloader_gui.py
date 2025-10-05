#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Music Downloader V2 - Enhanced GUI Version
马赫坡音乐 - 使用Selenium自动化下载 + 音乐播放器 + 歌词显示
"""

import os
import re
import time
import sys
import shutil
import threading
import subprocess
from datetime import datetime
from tkinter import *
from tkinter import ttk, scrolledtext, filedialog, messagebox
from urllib.parse import quote

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


def get_exe_dir():
    """获取exe所在目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def extract_usage_instructions():
    """每次运行时展开使用说明文件到exe目录"""
    try:
        exe_dir = get_exe_dir()
        if getattr(sys, 'frozen', False):
            bundle_dir = sys._MEIPASS
        else:
            bundle_dir = exe_dir

        bundled_readme = os.path.join(bundle_dir, "使用说明.txt")
        target_readme = os.path.join(exe_dir, "使用说明.txt")

        if os.path.exists(bundled_readme):
            shutil.copy2(bundled_readme, target_readme)
    except Exception:
        pass


def extract_bundled_chrome():
    """解压bundled的Chrome文件到exe目录（延迟执行）"""
    exe_dir = get_exe_dir()
    chrome_dir = os.path.join(exe_dir, "chrome")

    chrome_exe = os.path.join(chrome_dir, "chrome.exe")
    chromedriver_exe = os.path.join(chrome_dir, "chromedriver.exe")

    # 如果已存在,直接返回
    if os.path.exists(chrome_exe) and os.path.exists(chromedriver_exe):
        return True

    try:
        if getattr(sys, 'frozen', False):
            bundle_dir = sys._MEIPASS
        else:
            bundle_dir = exe_dir

        bundled_chrome_dir = os.path.join(bundle_dir, "chrome-win64")
        bundled_chromedriver_dir = os.path.join(bundle_dir, "chromedriver-win64")

        if not os.path.exists(bundled_chrome_dir):
            return False

        os.makedirs(chrome_dir, exist_ok=True)

        # 使用快速复制
        for item in os.listdir(bundled_chrome_dir):
            s = os.path.join(bundled_chrome_dir, item)
            d = os.path.join(chrome_dir, item)
            if os.path.isdir(s):
                if not os.path.exists(d):
                    shutil.copytree(s, d)
            else:
                if not os.path.exists(d):
                    shutil.copy2(s, d)

        chromedriver_src = os.path.join(bundled_chromedriver_dir, "chromedriver.exe")
        if os.path.exists(chromedriver_src) and not os.path.exists(chromedriver_exe):
            shutil.copy2(chromedriver_src, chromedriver_exe)

        return True

    except Exception:
        return False


def parse_lrc(lrc_content):
    """解析LRC歌词文件"""
    lines = []
    for line in lrc_content.split('\n'):
        line = line.strip()
        if not line:
            continue
        # 匹配时间标签 [mm:ss.xx]
        matches = re.findall(r'\[(\d{2}):(\d{2})\.(\d{2})\](.+)', line)
        for match in matches:
            minutes, seconds, centiseconds, text = match
            total_ms = (int(minutes) * 60 + int(seconds)) * 1000 + int(centiseconds) * 10
            lines.append((total_ms, text))
    return sorted(lines, key=lambda x: x[0])


class MusicDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("马赫坡音乐")
        self.root.geometry("1100x970")

        # 快速启动：最小化窗口初始化
        try:
            import ctypes
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if hwnd == 0:
                hwnd = int(self.root.wm_frame(), 16)
            self.hwnd = hwnd
        except Exception:
            self.hwnd = None

        # 窗口拖动相关变量
        self.dragging = False

        # 桌面歌词窗口
        self.desktop_lyric_window = None
        self.show_desktop_lyric = False

        # 配置
        exe_dir = get_exe_dir()
        self.exe_dir = exe_dir
        self.download_dir = os.path.join(exe_dir, "download")
        self.todo_file = os.path.join(exe_dir, "todo-download.txt")
        self.success_file = os.path.join(exe_dir, "download-success.txt")
        self.error_file = os.path.join(exe_dir, "download-err.txt")
        self.config_file = os.path.join(exe_dir, "player_config.txt")

        # 状态变量
        self.is_downloading = False
        self.driver = None
        self.current_playing = None
        self.current_lrc = []
        self.is_playing = False
        self.play_thread = None
        self.music_length = 0
        self.user_seeking = False
        self.loop_enabled = True
        self.current_page = 0
        self.page_size = 20
        self.total_files = []

        # 延迟初始化pygame（仅在需要时初始化）
        self.pygame_initialized = False

        # 设置主题颜色
        self.bg_color = "#f5f5f7"
        self.primary_color = "#ec4141"
        self.success_color = "#31c27c"
        self.error_color = "#d33a31"
        self.sidebar_color = "#ffffff"
        self.player_bg = "#fafafa"
        self.text_primary = "#333333"
        self.text_secondary = "#666666"
        self.text_muted = "#999999"

        self.root.configure(bg=self.bg_color)

        # 先加载配置
        self.load_config()

        # 创建UI
        self.create_widgets()

        # 延迟加载数据（不阻塞UI）
        self.root.after(50, self._delayed_init)

    def _delayed_init(self):
        """延迟初始化，不阻塞UI启动"""
        self.load_todo_list()
        self.refresh_local_music()

        # 自动播放上次的歌曲
        if self.current_playing and PYGAME_AVAILABLE:
            self._init_pygame()
            self.root.after(100, lambda: self.play_music(self.current_playing))

    def _init_pygame(self):
        """延迟初始化pygame"""
        if not self.pygame_initialized and PYGAME_AVAILABLE:
            try:
                pygame.mixer.quit()
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
                self.pygame_initialized = True
            except Exception:
                pass

    def create_widgets(self):
        # 顶部工具栏（替代自定义标题栏）
        toolbar = Frame(self.root, bg=self.primary_color, height=50)
        toolbar.pack(fill=X)
        toolbar.pack_propagate(False)

        # 左侧应用名称
        title_label = Label(
            toolbar,
            text="♪ 马赫坡音乐",
            font=("Microsoft YaHei UI", 14, "bold"),
            bg=self.primary_color,
            fg="white"
        )
        title_label.pack(side=LEFT, padx=20)

        # 右侧功能按钮
        buttons_frame = Frame(toolbar, bg=self.primary_color)
        buttons_frame.pack(side=RIGHT, padx=20)

        # 桌面歌词开关按钮
        self.desktop_lyric_btn = Button(
            buttons_frame,
            text="📝 桌面歌词",
            font=("Microsoft YaHei UI", 10),
            bg=self.primary_color,
            fg="white",
            relief=FLAT,
            cursor="hand2",
            command=self.toggle_desktop_lyric
        )
        self.desktop_lyric_btn.pack(side=LEFT, padx=5)
        self.bind_hover(self.desktop_lyric_btn, "#d63939", self.primary_color)

        # 关于按钮
        about_btn = Button(
            buttons_frame,
            text="ⓘ 关于",
            font=("Microsoft YaHei UI", 10),
            bg=self.primary_color,
            fg="white",
            relief=FLAT,
            cursor="hand2",
            command=self.show_about
        )
        about_btn.pack(side=LEFT, padx=5)
        self.bind_hover(about_btn, "#d63939", self.primary_color)

        # 标签页容器
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # 先创建本地音乐标签页（默认显示）
        self.create_local_tab()

        # 再创建下载标签页
        self.create_download_tab()

    def create_download_tab(self):
        """创建下载标签页"""
        download_frame = Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(download_frame, text="  📥 下载音乐  ")

        # 主容器
        main_container = Frame(download_frame, bg=self.bg_color)
        main_container.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # 左侧面板 - 歌曲列表
        left_panel = Frame(main_container, bg=self.bg_color)
        left_panel.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))

        # 歌曲列表标签
        list_label = Label(
            left_panel,
            text="待下载歌曲列表",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg=self.bg_color,
            fg="#333"
        )
        list_label.pack(anchor=W, pady=(0, 10))

        # 歌曲列表文本框
        self.song_text = scrolledtext.ScrolledText(
            left_panel,
            font=("Consolas", 10),
            wrap=WORD,
            relief=SOLID,
            borderwidth=1
        )
        self.song_text.pack(fill=BOTH, expand=True)

        # 列表按钮区域
        list_btn_frame = Frame(left_panel, bg=self.bg_color)
        list_btn_frame.pack(fill=X, pady=(10, 0))

        Button(
            list_btn_frame,
            text="➕ 添加",
            font=("Microsoft YaHei UI", 10),
            bg=self.primary_color,
            fg="white",
            relief=FLAT,
            cursor="hand2",
            command=self.add_song
        ).pack(side=LEFT, padx=(0, 5))

        Button(
            list_btn_frame,
            text="🗑️ 清空",
            font=("Microsoft YaHei UI", 10),
            bg="#95a5a6",
            fg="white",
            relief=FLAT,
            cursor="hand2",
            command=self.clear_list
        ).pack(side=LEFT, padx=(0, 5))

        Button(
            list_btn_frame,
            text="📂 加载文件",
            font=("Microsoft YaHei UI", 10),
            bg="#9b59b6",
            fg="white",
            relief=FLAT,
            cursor="hand2",
            command=self.load_from_file
        ).pack(side=LEFT)

        # 右侧面板 - 日志和控制
        right_panel = Frame(main_container, bg=self.bg_color)
        right_panel.pack(side=RIGHT, fill=BOTH, expand=True, padx=(10, 0))

        # 日志标签
        log_label = Label(
            right_panel,
            text="下载日志",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg=self.bg_color,
            fg="#333"
        )
        log_label.pack(anchor=W, pady=(0, 10))

        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(
            right_panel,
            font=("Consolas", 9),
            wrap=WORD,
            relief=SOLID,
            borderwidth=1,
            state=DISABLED,
            bg="#2c3e50",
            fg="#ecf0f1"
        )
        self.log_text.pack(fill=BOTH, expand=True)

        # 进度条
        self.progress_frame = Frame(right_panel, bg=self.bg_color)
        self.progress_frame.pack(fill=X, pady=(10, 0))

        self.progress_label = Label(
            self.progress_frame,
            text="准备就绪",
            font=("Microsoft YaHei UI", 9),
            bg=self.bg_color,
            fg="#7f8c8d"
        )
        self.progress_label.pack(anchor=W)

        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='indeterminate',
            length=300
        )
        self.progress_bar.pack(fill=X, pady=(5, 0))

        # 控制按钮区域
        control_frame = Frame(right_panel, bg=self.bg_color)
        control_frame.pack(fill=X, pady=(15, 0))

        self.start_btn = Button(
            control_frame,
            text="▶️ 开始下载",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg=self.success_color,
            fg="white",
            relief=FLAT,
            cursor="hand2",
            height=2,
            command=self.start_download
        )
        self.start_btn.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))

        self.stop_btn = Button(
            control_frame,
            text="⏹️ 停止",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg=self.error_color,
            fg="white",
            relief=FLAT,
            cursor="hand2",
            height=2,
            state=DISABLED,
            command=self.stop_download
        )
        self.stop_btn.pack(side=RIGHT, fill=X, expand=True, padx=(5, 0))

    def create_local_tab(self):
        """创建本地音乐标签页"""
        local_frame = Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(local_frame, text="  🎧 我的音乐  ")

        # 顶部工具栏
        toolbar = Frame(local_frame, bg=self.bg_color, height=50)
        toolbar.pack(fill=X, padx=10, pady=10)

        Button(
            toolbar,
            text="🔄 刷新",
            font=("Microsoft YaHei UI", 10),
            bg=self.primary_color,
            fg="white",
            relief=FLAT,
            cursor="hand2",
            command=self.refresh_local_music
        ).pack(side=LEFT, padx=(0, 5))

        Button(
            toolbar,
            text="📁 打开文件夹",
            font=("Microsoft YaHei UI", 10),
            bg="#3498db",
            fg="white",
            relief=FLAT,
            cursor="hand2",
            command=self.open_download_folder
        ).pack(side=LEFT, padx=(0, 5))

        Button(
            toolbar,
            text="💾 复制到U盘",
            font=("Microsoft YaHei UI", 10),
            bg="#e67e22",
            fg="white",
            relief=FLAT,
            cursor="hand2",
            command=self.copy_to_usb
        ).pack(side=LEFT)

        # 右侧播放控制按钮
        self.loop_btn = Button(
            toolbar,
            text="🔁 循环",
            font=("Microsoft YaHei UI", 10),
            bg="#9b59b6" if self.loop_enabled else "#95a5a6",
            fg="white",
            relief=FLAT,
            cursor="hand2",
            command=self.toggle_loop
        )
        self.loop_btn.pack(side=RIGHT, padx=(5, 0))

        Button(
            toolbar,
            text="⏹️ 停止",
            font=("Microsoft YaHei UI", 10),
            bg=self.error_color,
            fg="white",
            relief=FLAT,
            cursor="hand2",
            command=self.stop_music
        ).pack(side=RIGHT, padx=(5, 0))

        # 分页控制
        self.page_label = Label(
            toolbar,
            text="1/1",
            font=("Microsoft YaHei UI", 9),
            bg=self.bg_color,
            fg="#7f8c8d"
        )
        self.page_label.pack(side=RIGHT, padx=(10, 5))

        Button(
            toolbar,
            text="▶",
            font=("Microsoft YaHei UI", 10),
            bg="#95a5a6",
            fg="white",
            relief=FLAT,
            cursor="hand2",
            width=2,
            command=self.next_page
        ).pack(side=RIGHT, padx=(2, 0))

        Button(
            toolbar,
            text="◀",
            font=("Microsoft YaHei UI", 10),
            bg="#95a5a6",
            fg="white",
            relief=FLAT,
            cursor="hand2",
            width=2,
            command=self.prev_page
        ).pack(side=RIGHT, padx=(5, 2))

        # 音乐列表区域
        list_container = Frame(local_frame, bg=self.bg_color)
        list_container.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))

        # 创建Treeview显示音乐列表
        columns = ("name", "status", "size", "action", "delete")
        self.music_tree = ttk.Treeview(list_container, columns=columns, show="headings", height=15)
        self.music_tree.heading("name", text="歌曲名称")
        self.music_tree.heading("status", text="状态")
        self.music_tree.heading("size", text="文件大小")
        self.music_tree.heading("action", text="操作")
        self.music_tree.heading("delete", text="删除")

        self.music_tree.column("name", width=300, anchor=W)  # 左对齐
        self.music_tree.column("status", width=100, anchor=CENTER)  # 居中
        self.music_tree.column("size", width=100, anchor=CENTER)  # 居中
        self.music_tree.column("action", width=80, anchor=CENTER)  # 居中
        self.music_tree.column("delete", width=80, anchor=CENTER)  # 居中

        # 配置标签样式 - 突出显示正在播放的歌曲
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        self.music_tree.tag_configure('playing', background='#d4edda', foreground='#155724')

        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_container, orient=VERTICAL, command=self.music_tree.yview)
        self.music_tree.configure(yscrollcommand=scrollbar.set)

        self.music_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # 绑定单击事件到操作列
        self.music_tree.bind('<Button-1>', self.on_tree_click)

        # 播放器控制区域（网易云风格）
        player_frame = Frame(local_frame, bg=self.player_bg, height=450)
        player_frame.pack(fill=X, padx=10, pady=(0, 10))
        player_frame.pack_propagate(False)

        # 顶部分隔线
        separator = Frame(player_frame, bg="#e0e0e0", height=1)
        separator.pack(fill=X)

        # 当前播放信息区域
        info_container = Frame(player_frame, bg=self.player_bg)
        info_container.pack(fill=X, padx=30, pady=(20, 10))

        # 歌曲名称
        self.now_playing_label = Label(
            info_container,
            text="暂无播放",
            font=("Microsoft YaHei UI", 16, "bold"),
            bg=self.player_bg,
            fg=self.text_primary
        )
        self.now_playing_label.pack(anchor=W)

        # 艺术家信息（预留）
        self.artist_label = Label(
            info_container,
            text="",
            font=("Microsoft YaHei UI", 10),
            bg=self.player_bg,
            fg=self.text_secondary
        )
        self.artist_label.pack(anchor=W, pady=(5, 0))

        # 进度条区域
        progress_container = Frame(player_frame, bg=self.player_bg)
        progress_container.pack(fill=X, padx=30, pady=(10, 10))

        self.time_label = Label(
            progress_container,
            text="00:00",
            font=("Microsoft YaHei UI", 10),
            bg=self.player_bg,
            fg=self.text_muted
        )
        self.time_label.pack(side=LEFT, padx=(0, 15))

        # 使用Canvas创建自定义进度条
        progress_canvas = Canvas(
            progress_container,
            height=10,
            bg=self.player_bg,
            highlightthickness=0
        )
        progress_canvas.pack(side=LEFT, fill=X, expand=True)

        # 创建进度条背景和进度线（网易云风格）
        self.progress_bg = progress_canvas.create_rectangle(
            0, 2, 400, 7,
            fill="#e0e0e0",
            outline=""
        )
        self.progress_fill = progress_canvas.create_rectangle(
            0, 2, 0, 7,
            fill=self.primary_color,
            outline=""
        )
        self.progress_handle = progress_canvas.create_oval(
            -6, 0, 6, 10,
            fill=self.primary_color,
            outline="white",
            width=2
        )

        self.progress_canvas = progress_canvas
        self.progress_dragging = False

        # 移除拖动事件绑定（禁用拖动）
        # progress_canvas.bind('<Button-1>', self.on_progress_press)
        # progress_canvas.bind('<B1-Motion>', self.on_progress_drag)
        # progress_canvas.bind('<ButtonRelease-1>', self.on_progress_release)
        progress_canvas.bind('<Configure>', self.on_progress_resize)

        self.total_time_label = Label(
            progress_container,
            text="00:00",
            font=("Microsoft YaHei UI", 10),
            bg=self.player_bg,
            fg=self.text_muted
        )
        self.total_time_label.pack(side=LEFT, padx=(15, 0))

        # 歌词显示区域（网易云风格）
        lrc_container = Frame(player_frame, bg=self.player_bg)
        lrc_container.pack(fill=BOTH, expand=True, padx=30, pady=(15, 20))

        self.lrc_text = Text(
            lrc_container,
            font=("Microsoft YaHei UI", 13),
            bg=self.player_bg,
            fg=self.text_secondary,
            wrap=WORD,
            height=12,
            relief=FLAT,
            state=DISABLED,
            cursor="arrow",
            spacing1=8,
            spacing3=8
        )
        self.lrc_text.pack(fill=BOTH, expand=True)

        # 配置歌词样式（网易云风格）
        self.lrc_text.tag_config("current",
                                 foreground=self.text_primary,
                                 font=("Microsoft YaHei UI", 14, "bold"))
        self.lrc_text.tag_config("past",
                                 foreground=self.text_muted)
        self.lrc_text.tag_config("future",
                                 foreground=self.text_secondary)

    def on_progress_resize(self, event):
        """进度条窗口大小改变"""
        width = event.width
        self.progress_canvas.coords(self.progress_bg, 0, 1, width, 5)
        # 重新计算当前进度位置
        if self.music_length > 0 and self.current_playing:
            try:
                pos = pygame.mixer.music.get_pos()
                progress = (pos / self.music_length)
                self.update_progress_ui(progress)
            except:
                pass

    def on_progress_press(self, event):
        """进度条按下"""
        self.progress_dragging = True
        self.user_seeking = True
        self.seek_to_position(event.x)

    def on_progress_drag(self, event):
        """进度条拖动"""
        if self.progress_dragging:
            self.seek_to_position(event.x)

    def on_progress_release(self, event):
        """进度条释放"""
        self.progress_dragging = False
        self.seek_to_position(event.x)
        # 延迟恢复更新，避免立即被覆盖
        self.root.after(200, lambda: setattr(self, 'user_seeking', False))

    def seek_to_position(self, x):
        """根据X坐标跳转到指定位置"""
        if not PYGAME_AVAILABLE or not self.current_playing or self.music_length == 0:
            return

        width = self.progress_canvas.winfo_width()
        if width <= 0:
            return

        # 计算进度百分比
        progress = max(0, min(1, x / width))
        seek_pos = int(progress * self.music_length)

        try:
            # 重新加载并播放到指定位置
            mp3_path = os.path.join(self.download_dir, f"{self.current_playing}.mp3")
            pygame.mixer.music.load(mp3_path)
            pygame.mixer.music.play(start=seek_pos / 1000.0, loops=-1 if self.loop_enabled else 0)

            if not self.is_playing:
                pygame.mixer.music.pause()

            # 立即更新UI
            self.update_progress_ui(progress)

            # 更新时间标签
            current_time = self.format_time(seek_pos)
            total_time = self.format_time(self.music_length)
            self.time_label.config(text=current_time)
            self.total_time_label.config(text=total_time)

            # 立即更新歌词显示
            if self.current_lrc:
                self.update_lyrics_display(seek_pos)

        except Exception as e:
            print(f"Seek error: {e}")

    def update_progress_ui(self, progress):
        """更新进度条UI"""
        width = self.progress_canvas.winfo_width()
        if width <= 0:
            return

        x = progress * width
        self.progress_canvas.coords(self.progress_fill, 0, 1, x, 5)
        self.progress_canvas.coords(self.progress_handle, x - 6, -2, x + 6, 10)

    def on_progress_change(self, value):
        """进度条拖动事件（旧的，已废弃）"""
        pass

    def format_time(self, ms):
        """格式化时间（毫秒转为 mm:ss）"""
        seconds = int(ms / 1000)
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02d}:{secs:02d}"

    def update_lyrics_display(self, current_pos):
        """更新歌词显示"""
        if not self.current_lrc:
            return

        # 找到当前歌词的索引
        current_index = -1
        for i, (time_ms, text) in enumerate(self.current_lrc):
            if current_pos >= time_ms:
                current_index = i
            else:
                break

        # 清空歌词文本
        self.lrc_text.config(state=NORMAL)
        self.lrc_text.delete(1.0, END)

        # 显示前后各行歌词（总共10行）
        start_index = max(0, current_index - 3)
        end_index = min(len(self.current_lrc), current_index + 7)

        current_lyric_text = ""
        for i in range(start_index, end_index):
            time_ms, text = self.current_lrc[i]

            if i < current_index:
                # 已播放的歌词
                self.lrc_text.insert(END, text + "\n", "past")
            elif i == current_index:
                # 当前播放的歌词
                self.lrc_text.insert(END, text + "\n", "current")
                current_lyric_text = text
            else:
                # 未播放的歌词
                self.lrc_text.insert(END, text + "\n", "future")

        # 滚动到当前歌词位置（让当前歌词显示在中间）
        if current_index >= 0 and current_index >= start_index:
            line_num = current_index - start_index + 1
            self.lrc_text.see(f"{line_num}.0")
            # 使用mark_set确保当前行居中
            self.lrc_text.mark_set("insert", f"{line_num}.0")

        self.lrc_text.config(state=DISABLED)

        # 更新桌面歌词
        if current_lyric_text:
            self.update_desktop_lyric(current_lyric_text)
        elif current_index == -1 and self.current_lrc:
            self.update_desktop_lyric("♪ 即将开始 ♪")

    def get_downloaded_songs(self):
        """获取已下载的歌曲列表"""
        if not os.path.exists(self.download_dir):
            return set()

        mp3_files = [f[:-4] for f in os.listdir(self.download_dir) if f.endswith('.mp3')]
        return set(mp3_files)

    def sanitize_filename(self, name):
        """清理文件名"""
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        name = name.strip()
        if len(name) > 200:
            name = name[:200]
        return name

    def is_song_downloaded(self, song_name):
        """检查歌曲是否已下载"""
        safe_name = self.sanitize_filename(song_name)
        mp3_path = os.path.join(self.download_dir, f"{safe_name}.mp3")
        return os.path.exists(mp3_path)

    def refresh_local_music(self):
        """刷新本地音乐列表（支持分页）"""
        # 清空列表
        for item in self.music_tree.get_children():
            self.music_tree.delete(item)

        if not os.path.exists(self.download_dir):
            return

        # 获取所有MP3文件
        self.total_files = sorted([f for f in os.listdir(self.download_dir) if f.endswith('.mp3')])

        # 计算总页数
        total_pages = max(1, (len(self.total_files) + self.page_size - 1) // self.page_size)

        # 确保当前页在有效范围内
        self.current_page = max(0, min(self.current_page, total_pages - 1))

        # 更新分页标签
        self.page_label.config(text=f"{self.current_page + 1}/{total_pages}")

        # 计算当前页的文件范围
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.total_files))

        files = self.total_files[start_idx:end_idx]

        for file in files:
            name = file[:-4]  # 去掉.mp3扩展名
            lrc_file = os.path.join(self.download_dir, f"{name}.lrc")

            # 检查是否有歌词
            status = "✓ 有歌词" if os.path.exists(lrc_file) else "✗ 无歌词"

            # 获取文件大小
            file_path = os.path.join(self.download_dir, file)
            size = os.path.getsize(file_path)
            size_str = f"{size / 1024 / 1024:.2f} MB"

            # 判断是否正在播放
            if self.current_playing == name and self.is_playing:
                action = "⏸️ 暂停"
                delete_action = "🚫 禁止"  # 正在播放,不可删除
                # 添加标签突出显示正在播放的歌曲
                self.music_tree.insert("", END, values=(name, status, size_str, action, delete_action), tags=('playing',))
            elif self.current_playing == name and not self.is_playing:
                action = "▶️ 继续"
                delete_action = "🚫 禁止"  # 暂停状态,不可删除
                # 添加标签突出显示暂停的歌曲
                self.music_tree.insert("", END, values=(name, status, size_str, action, delete_action), tags=('playing',))
            else:
                action = "▶️ 播放"
                delete_action = "🗑️ 删除"
                self.music_tree.insert("", END, values=(name, status, size_str, action, delete_action))

    def prev_page(self):
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_local_music()

    def next_page(self):
        """下一页"""
        total_pages = max(1, (len(self.total_files) + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.refresh_local_music()

    def open_download_folder(self):
        """打开下载文件夹"""
        if os.path.exists(self.download_dir):
            subprocess.Popen(f'explorer "{self.download_dir}"')
        else:
            messagebox.showinfo("提示", "下载文件夹不存在")

    def get_usb_drives(self):
        """检测所有U盘驱动器"""
        import string
        drives = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                try:
                    # 检查是否为可移动驱动器
                    import ctypes
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
                    # DRIVE_REMOVABLE = 2
                    if drive_type == 2:
                        drives.append(drive)
                except:
                    pass
        return drives

    def copy_to_usb(self):
        """复制所有音乐到U盘"""
        # 检测U盘
        usb_drives = self.get_usb_drives()

        if not usb_drives:
            messagebox.showwarning("未检测到U盘", "请插入U盘后重试")
            return

        # 如果有多个U盘,让用户选择
        if len(usb_drives) == 1:
            target_drive = usb_drives[0]
        else:
            # 创建选择对话框
            dialog = Toplevel(self.root)
            dialog.title("选择U盘")
            dialog.geometry("400x250")
            dialog.resizable(False, False)
            dialog.configure(bg=self.bg_color)
            dialog.transient(self.root)
            dialog.grab_set()

            Label(
                dialog,
                text="检测到多个U盘,请选择目标U盘:",
                font=("Microsoft YaHei UI", 10),
                bg=self.bg_color
            ).pack(pady=(20, 10))

            selected_drive = StringVar(value=usb_drives[0])

            for drive in usb_drives:
                try:
                    # 获取卷标
                    import ctypes
                    volume_name = ctypes.create_unicode_buffer(261)
                    ctypes.windll.kernel32.GetVolumeInformationW(
                        drive, volume_name, 261, None, None, None, None, 0
                    )
                    label = volume_name.value or "未命名"
                    display_text = f"{drive} ({label})"
                except:
                    display_text = drive

                Radiobutton(
                    dialog,
                    text=display_text,
                    variable=selected_drive,
                    value=drive,
                    font=("Microsoft YaHei UI", 10),
                    bg=self.bg_color,
                    cursor="hand2"
                ).pack(anchor=W, padx=40, pady=5)

            result = [None]

            def confirm():
                result[0] = selected_drive.get()
                dialog.destroy()

            Button(
                dialog,
                text="确定",
                font=("Microsoft YaHei UI", 10),
                bg=self.primary_color,
                fg="white",
                relief=FLAT,
                cursor="hand2",
                command=confirm
            ).pack(pady=20)

            dialog.wait_window()

            if not result[0]:
                return

            target_drive = result[0]

        # 开始复制
        if not os.path.exists(self.download_dir):
            messagebox.showwarning("提示", "下载文件夹不存在")
            return

        # 创建目标文件夹
        target_dir = os.path.join(target_drive, "马赫破音乐")
        os.makedirs(target_dir, exist_ok=True)

        # 复制所有音乐文件
        files = [f for f in os.listdir(self.download_dir)
                if f.endswith('.mp3') or f.endswith('.lrc')]

        if not files:
            messagebox.showinfo("提示", "没有音乐文件可复制")
            return

        # 显示进度对话框
        progress_dialog = Toplevel(self.root)
        progress_dialog.title("复制到U盘")
        progress_dialog.geometry("450x180")
        progress_dialog.resizable(False, False)
        progress_dialog.configure(bg=self.bg_color)
        progress_dialog.transient(self.root)
        progress_dialog.grab_set()

        Label(
            progress_dialog,
            text=f"正在复制到 {target_drive}",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg=self.bg_color
        ).pack(pady=20)

        progress_label = Label(
            progress_dialog,
            text="准备复制...",
            font=("Microsoft YaHei UI", 10),
            bg=self.bg_color
        )
        progress_label.pack(pady=10)

        progress_bar = ttk.Progressbar(
            progress_dialog,
            mode='determinate',
            length=380,
            maximum=len(files)
        )
        progress_bar.pack(pady=10)

        # 复制线程
        def copy_thread():
            copied = 0
            errors = 0

            for i, file in enumerate(files):
                try:
                    src = os.path.join(self.download_dir, file)
                    dst = os.path.join(target_dir, file)

                    # 如果目标文件存在,覆盖
                    shutil.copy2(src, dst)
                    copied += 1

                    # 更新进度
                    self.root.after(0, lambda idx=i+1, f=file:
                        progress_label.config(text=f"[{idx}/{len(files)}] {f}"))
                    self.root.after(0, lambda idx=i+1:
                        progress_bar.config(value=idx))

                except Exception as e:
                    errors += 1

            # 完成
            self.root.after(0, lambda: progress_dialog.destroy())
            self.root.after(0, lambda c=copied, e=errors:
                messagebox.showinfo("复制完成",
                    f"成功复制 {c} 个文件\n"
                    f"失败 {e} 个文件\n\n"
                    f"目标位置: {target_dir}"))

        thread = threading.Thread(target=copy_thread)
        thread.daemon = True
        thread.start()

    def on_tree_click(self, event):
        """处理树形列表的点击事件"""
        region = self.music_tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        column = self.music_tree.identify_column(event.x)
        row_id = self.music_tree.identify_row(event.y)

        if not row_id:
            return

        item = self.music_tree.item(row_id)
        song_name = item['values'][0]

        # 检查是否点击了操作列（第4列）
        if column == "#4":
            action = item['values'][3]

            if action == "▶️ 播放":
                self.play_music(song_name)
            elif action == "⏸️ 暂停":
                self.toggle_play_pause()
            elif action == "▶️ 继续":
                self.toggle_play_pause()

        # 检查是否点击了删除列（第5列）
        elif column == "#5":
            delete_action = item['values'][4]
            # 检查是否允许删除
            if delete_action == "🚫 禁止":
                messagebox.showwarning("无法删除", "正在播放或暂停的歌曲不能删除！")
                return
            self.delete_music(song_name)

    def delete_music(self, song_name):
        """删除音乐文件"""
        # 创建确认对话框
        dialog = Toplevel(self.root)
        dialog.title("确认删除")
        dialog.geometry("400x220")
        dialog.resizable(False, False)
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()

        # 居中显示
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 220) // 2
        dialog.geometry(f"+{x}+{y}")

        Label(
            dialog,
            text="⚠️ 确认删除",
            font=("Microsoft YaHei UI", 14, "bold"),
            bg=self.bg_color,
            fg=self.error_color
        ).pack(pady=(15, 10))

        Label(
            dialog,
            text=f"确定要删除以下歌曲吗?\n\n{song_name}",
            font=("Microsoft YaHei UI", 10),
            bg=self.bg_color,
            justify=CENTER
        ).pack(pady=5)

        Label(
            dialog,
            text="此操作不可恢复!",
            font=("Microsoft YaHei UI", 9),
            bg=self.bg_color,
            fg=self.text_muted
        ).pack(pady=5)

        # 按钮区域
        btn_frame = Frame(dialog, bg=self.bg_color)
        btn_frame.pack(pady=15)

        def confirm_delete():
            # 如果正在播放这首歌,先停止
            if self.current_playing == song_name:
                self.stop_music()
                # 等待pygame释放文件
                time.sleep(0.3)

            # 删除MP3和LRC文件
            mp3_path = os.path.join(self.download_dir, f"{song_name}.mp3")
            lrc_path = os.path.join(self.download_dir, f"{song_name}.lrc")

            try:
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
                if os.path.exists(lrc_path):
                    os.remove(lrc_path)

                dialog.destroy()
                self.refresh_local_music()
                messagebox.showinfo("删除成功", f"已删除: {song_name}")
            except PermissionError:
                dialog.destroy()
                messagebox.showerror("删除失败",
                    f"文件被占用，无法删除！\n\n"
                    f"可能原因：\n"
                    f"- 文件正在被其他程序使用\n"
                    f"- 请关闭正在使用该文件的程序后重试")
            except Exception as e:
                dialog.destroy()
                error_msg = str(e)
                if "being used by another process" in error_msg or "WinError 32" in error_msg:
                    messagebox.showerror("删除失败",
                        f"文件被占用，无法删除！\n\n"
                        f"请确保文件未被其他程序使用")
                else:
                    messagebox.showerror("删除失败", f"删除失败: {error_msg}")

        def cancel_delete():
            dialog.destroy()

        Button(
            btn_frame,
            text="确定删除",
            font=("Microsoft YaHei UI", 10),
            bg=self.error_color,
            fg="white",
            relief=FLAT,
            cursor="hand2",
            width=10,
            command=confirm_delete
        ).pack(side=LEFT, padx=5)

        Button(
            btn_frame,
            text="取消",
            font=("Microsoft YaHei UI", 10),
            bg="#95a5a6",
            fg="white",
            relief=FLAT,
            cursor="hand2",
            width=10,
            command=cancel_delete
        ).pack(side=LEFT, padx=5)

        # 绑定ESC键取消
        dialog.bind('<Escape>', lambda e: cancel_delete())

    def play_selected_music(self, event):
        """播放选中的音乐（保留用于双击）"""
        selection = self.music_tree.selection()
        if not selection:
            return

        item = self.music_tree.item(selection[0])
        song_name = item['values'][0]

        self.play_music(song_name)

    def get_next_song(self):
        """获取下一首歌曲"""
        if not self.current_playing or not self.total_files:
            return None

        try:
            # 找到当前歌曲在总列表中的索引
            current_file = f"{self.current_playing}.mp3"
            current_index = self.total_files.index(current_file)

            # 获取下一首
            next_index = (current_index + 1) % len(self.total_files)
            next_file = self.total_files[next_index]

            return next_file[:-4]  # 去掉.mp3扩展名
        except (ValueError, IndexError):
            return None

    def play_music(self, song_name):
        """播放音乐"""
        if not PYGAME_AVAILABLE:
            messagebox.showerror("错误", "pygame未安装,无法播放音乐")
            return

        # 确保pygame已初始化
        self._init_pygame()

        mp3_path = os.path.join(self.download_dir, f"{song_name}.mp3")
        lrc_path = os.path.join(self.download_dir, f"{song_name}.lrc")

        if not os.path.exists(mp3_path):
            messagebox.showerror("错误", "音乐文件不存在")
            return

        try:
            # 停止当前播放的音乐（如果有）
            if self.current_playing:
                pygame.mixer.music.stop()

            # 清除歌词显示
            self.lrc_text.config(state=NORMAL)
            self.lrc_text.delete(1.0, END)
            self.lrc_text.insert(END, "加载中...", "future")
            self.lrc_text.config(state=DISABLED)

            # 更新桌面歌词
            self.update_desktop_lyric(f"正在播放: {song_name}")

            # 加载音乐
            pygame.mixer.music.load(mp3_path)

            # 获取音乐长度（使用mutagen或pygame.mixer.Sound）
            try:
                from mutagen.mp3 import MP3
                audio = MP3(mp3_path)
                self.music_length = int(audio.info.length * 1000)  # 转换为毫秒
            except:
                # 如果mutagen不可用，使用估算值
                self.music_length = 180000  # 默认3分钟

            pygame.mixer.music.play()

            self.current_playing = song_name
            self.is_playing = True
            self.now_playing_label.config(text=f"正在播放: {song_name}")

            # 重置进度条UI
            self.update_progress_ui(0)

            # 加载歌词
            if os.path.exists(lrc_path):
                with open(lrc_path, 'r', encoding='utf-8') as f:
                    lrc_content = f.read()
                self.current_lrc = parse_lrc(lrc_content)
            else:
                self.current_lrc = []
                self.lrc_text.config(state=NORMAL)
                self.lrc_text.delete(1.0, END)
                self.lrc_text.insert(END, "暂无歌词", "future")
                self.lrc_text.config(state=DISABLED)
                # 桌面歌词也显示暂无歌词
                self.update_desktop_lyric("暂无歌词")

            # 启动歌词同步线程
            if self.play_thread and self.play_thread.is_alive():
                pass
            else:
                self.play_thread = threading.Thread(target=self.update_lyrics)
                self.play_thread.daemon = True
                self.play_thread.start()

            # 刷新列表显示，更新按钮状态
            self.refresh_local_music()

            # 保存配置
            self.save_config()

        except Exception as e:
            messagebox.showerror("错误", f"播放失败: {str(e)}")

    def toggle_play_pause(self):
        """播放/暂停切换"""
        if not PYGAME_AVAILABLE:
            return

        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
        else:
            pygame.mixer.music.unpause()
            self.is_playing = True

        # 刷新列表显示，更新按钮状态
        self.refresh_local_music()

    def stop_music(self):
        """停止播放"""
        if PYGAME_AVAILABLE:
            pygame.mixer.music.stop()

        self.is_playing = False
        self.current_playing = None
        self.current_lrc = []
        self.music_length = 0
        self.now_playing_label.config(text="暂无播放")

        # 清除歌词
        self.lrc_text.config(state=NORMAL)
        self.lrc_text.delete(1.0, END)
        self.lrc_text.config(state=DISABLED)

        # 清除桌面歌词
        self.update_desktop_lyric("暂无播放")

        # 重置进度条UI和时间标签
        self.update_progress_ui(0)
        self.time_label.config(text="00:00")
        self.total_time_label.config(text="00:00")

        # 刷新列表显示，更新按钮状态
        self.refresh_local_music()

    def toggle_loop(self):
        """切换循环模式"""
        self.loop_enabled = not self.loop_enabled

        # 更新按钮颜色
        self.loop_btn.config(bg="#9b59b6" if self.loop_enabled else "#95a5a6")

        status = "已开启" if self.loop_enabled else "已关闭"
        messagebox.showinfo("提示", f"循环播放{status}")

        # 保存配置
        self.save_config()

    def save_config(self):
        """保存播放器配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(f"last_song={self.current_playing or ''}\n")
                f.write(f"loop_enabled={self.loop_enabled}\n")
        except:
            pass

    def load_config(self):
        """加载播放器配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('last_song='):
                            song = line.split('=', 1)[1]
                            if song and self.is_song_downloaded(song):
                                self.current_playing = song
                        elif line.startswith('loop_enabled='):
                            self.loop_enabled = line.split('=', 1)[1] == 'True'
        except:
            pass

    def update_lyrics(self):
        """更新歌词显示和进度条"""
        while self.current_playing and PYGAME_AVAILABLE:
            if not self.is_playing:
                time.sleep(0.1)
                continue

            try:
                # 获取当前播放位置（毫秒）
                pos = pygame.mixer.music.get_pos()

                if pos < 0:  # 播放结束
                    if self.loop_enabled:
                        # 列表循环：播放下一首
                        next_song = self.get_next_song()
                        if next_song:
                            time.sleep(0.5)  # 短暂延迟
                            self.root.after(0, lambda s=next_song: self.play_music(s))
                            break
                        else:
                            # 没有下一首，停止播放
                            break
                    else:
                        # 不循环，停止播放
                        break

                # 更新进度条（如果用户没有在拖动）
                if not self.user_seeking and self.music_length > 0:
                    progress = pos / self.music_length
                    self.root.after(0, lambda p=progress: self.update_progress_ui(p))

                    # 更新时间标签
                    current_time = self.format_time(pos)
                    total_time = self.format_time(self.music_length)
                    self.root.after(0, lambda ct=current_time:
                                   self.time_label.config(text=ct))
                    self.root.after(0, lambda tt=total_time:
                                   self.total_time_label.config(text=tt))

                # 更新歌词显示
                if self.current_lrc and not self.user_seeking:
                    self.root.after(0, lambda p=pos: self.update_lyrics_display(p))

                time.sleep(0.1)
            except:
                break

    def log(self, message, level="INFO"):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        color_map = {
            "INFO": "#3498db",
            "SUCCESS": "#2ecc71",
            "ERROR": "#e74c3c",
            "WARNING": "#f39c12",
            "SKIP": "#95a5a6"
        }
        color = color_map.get(level, "#ecf0f1")

        self.log_text.config(state=NORMAL)
        self.log_text.insert(END, f"[{timestamp}] ", "timestamp")
        self.log_text.insert(END, f"{message}\n", level)
        self.log_text.tag_config("timestamp", foreground="#95a5a6")
        self.log_text.tag_config(level, foreground=color)
        self.log_text.see(END)
        self.log_text.config(state=DISABLED)

    def load_todo_list(self):
        """加载待下载列表，并标记已下载"""
        if os.path.exists(self.todo_file):
            with open(self.todo_file, 'r', encoding='utf-8') as f:
                songs = f.read().strip().split('\n')

            # 清空文本框
            self.song_text.delete(1.0, END)

            # 添加歌曲，标记已下载
            for song in songs:
                song = song.strip()
                if not song:
                    continue

                if self.is_song_downloaded(song):
                    self.song_text.insert(END, f"{song} [已下载]\n")
                else:
                    self.song_text.insert(END, f"{song}\n")

    def save_todo_list(self):
        """保存待下载列表"""
        content = self.song_text.get(1.0, END).strip()
        # 移除[已下载]标记
        content = re.sub(r'\s*\[已下载\]', '', content)
        with open(self.todo_file, 'w', encoding='utf-8') as f:
            f.write(content)

    def add_song(self):
        """添加单首歌曲"""
        dialog = Toplevel(self.root)
        dialog.title("添加歌曲")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()

        Label(
            dialog,
            text="请输入歌曲名（建议格式：歌名 - 歌手）",
            font=("Microsoft YaHei UI", 10),
            bg=self.bg_color
        ).pack(pady=(20, 10))

        entry = Entry(dialog, font=("Microsoft YaHei UI", 11), width=35)
        entry.pack(pady=10)
        entry.focus()

        def add():
            song = entry.get().strip()
            if song:
                current = self.song_text.get(1.0, END).strip()

                # 检查是否已下载
                suffix = " [已下载]" if self.is_song_downloaded(song) else ""

                if current:
                    self.song_text.insert(END, f"\n{song}{suffix}")
                else:
                    self.song_text.insert(END, f"{song}{suffix}")
                dialog.destroy()

        entry.bind('<Return>', lambda e: add())

        Button(
            dialog,
            text="添加",
            font=("Microsoft YaHei UI", 10),
            bg=self.primary_color,
            fg="white",
            relief=FLAT,
            cursor="hand2",
            command=add
        ).pack(pady=10)

    def clear_list(self):
        """清空列表"""
        if messagebox.askyesno("确认", "确定要清空歌曲列表吗？"):
            self.song_text.delete(1.0, END)

    def load_from_file(self):
        """从文件加载"""
        filename = filedialog.askopenfilename(
            title="选择歌曲列表文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filename:
            with open(filename, 'r', encoding='utf-8') as f:
                songs = f.read().strip().split('\n')

            self.song_text.delete(1.0, END)

            for song in songs:
                song = song.strip()
                if not song:
                    continue

                suffix = " [已下载]" if self.is_song_downloaded(song) else ""
                self.song_text.insert(END, f"{song}{suffix}\n")

    def start_download(self):
        """开始下载"""
        content = self.song_text.get(1.0, END).strip()
        # 移除[已下载]标记
        content = re.sub(r'\s*\[已下载\]', '', content)
        songs = [s.strip() for s in content.split('\n') if s.strip()]

        if not songs:
            messagebox.showwarning("警告", "请先添加要下载的歌曲！")
            return

        self.is_downloading = True
        self.start_btn.config(state=DISABLED)
        self.stop_btn.config(state=NORMAL)
        self.progress_bar.start(10)

        thread = threading.Thread(target=self.download_thread, args=(songs,))
        thread.daemon = True
        thread.start()

    def stop_download(self):
        """停止下载"""
        self.is_downloading = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.log("用户停止下载", "WARNING")
        self.reset_ui()

    def reset_ui(self):
        """重置UI状态"""
        self.start_btn.config(state=NORMAL)
        self.stop_btn.config(state=DISABLED)
        self.progress_bar.stop()
        self.progress_label.config(text="准备就绪")

    def download_thread(self, songs):
        """下载线程"""
        try:
            self.log(f"开始下载 {len(songs)} 首歌曲...", "INFO")
            os.makedirs(self.download_dir, exist_ok=True)

            self.setup_driver()

            downloaded_count = 0
            skipped_count = 0

            for i, song in enumerate(songs, 1):
                if not self.is_downloading:
                    break

                # 检查是否已下载
                if self.is_song_downloaded(song):
                    self.log(f"⊘ [{i}/{len(songs)}] {song} - 已下载，跳过", "SKIP")
                    skipped_count += 1
                    continue

                self.root.after(0, lambda s=song, idx=i, total=len(songs):
                    self.progress_label.config(text=f"正在下载 [{idx}/{total}]: {s}"))

                self.log(f"[{i}/{len(songs)}] 处理: {song}", "INFO")

                mp3_success = self.download_mp3(song)
                lrc_success, lrc_content = self.download_lrc(song)

                if lrc_success and lrc_content:
                    self.save_lrc(song, lrc_content)

                if mp3_success and lrc_success:
                    self.log(f"✓ {song} - 下载完成", "SUCCESS")
                    self.append_to_file(self.success_file, song, "MP3:成功, 歌词:成功")
                    downloaded_count += 1
                elif mp3_success:
                    self.log(f"⚠ {song} - MP3成功，歌词失败", "WARNING")
                    self.append_to_file(self.success_file, song, "MP3:成功, 歌词:失败")
                    downloaded_count += 1
                else:
                    self.log(f"✗ {song} - 下载失败", "ERROR")
                    self.append_to_file(self.error_file, song, "MP3:失败")

                time.sleep(2)

            if self.driver:
                self.driver.quit()

            if self.is_downloading:
                summary = f"下载完成！成功: {downloaded_count}, 跳过: {skipped_count}"
                self.log(summary, "SUCCESS")
                self.root.after(0, lambda: messagebox.showinfo("完成", summary))
                self.song_text.delete(1.0, END)
                self.save_todo_list()
                self.root.after(0, self.refresh_local_music)

        except Exception as e:
            self.log(f"发生错误: {str(e)}", "ERROR")
        finally:
            self.is_downloading = False
            self.root.after(0, self.reset_ui)

    def setup_driver(self):
        """设置Chrome驱动（延迟导入）"""
        # 延迟导入Selenium模块
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service

        chrome_options = Options()
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        extract_bundled_chrome()

        exe_dir = get_exe_dir()
        chrome_path = os.path.join(exe_dir, "chrome", "chrome.exe")
        chromedriver_path = os.path.join(exe_dir, "chrome", "chromedriver.exe")

        if os.path.exists(chrome_path) and os.path.exists(chromedriver_path):
            chrome_options.binary_location = chrome_path
            service = Service(executable_path=chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            self.driver = webdriver.Chrome(options=chrome_options)

        self.driver.implicitly_wait(10)

    def download_mp3(self, song_name):
        """下载MP3"""
        # 延迟导入Selenium模块
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException

        try:
            before_files = set(f for f in os.listdir(self.download_dir) if f.endswith('.mp3'))

            self.driver.get("https://mp3juice.co/")

            search_box = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="text"]'))
            )

            search_box.clear()
            search_box.send_keys(song_name)

            search_button = self.driver.find_element(By.XPATH, '//button[contains(text(), "Search")]')
            search_button.click()

            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//a[text()="MP3 Download"]'))
            )

            download_buttons = self.driver.find_elements(By.XPATH, '//a[text()="MP3 Download"]')
            if download_buttons:
                self.driver.execute_script("arguments[0].click();", download_buttons[0])

                try:
                    download_link = WebDriverWait(self.driver, 90).until(
                        EC.presence_of_element_located((By.XPATH, '//a[text()="Download"]'))
                    )
                except TimeoutException:
                    return False

                self.driver.execute_script("arguments[0].click();", download_link)

                for i in range(30):
                    time.sleep(1)
                    after_files = set(f for f in os.listdir(self.download_dir) if f.endswith('.mp3'))
                    new_files = after_files - before_files

                    if new_files:
                        downloaded_file = list(new_files)[0]
                        old_path = os.path.join(self.download_dir, downloaded_file)
                        safe_name = self.sanitize_filename(song_name)
                        new_path = os.path.join(self.download_dir, f"{safe_name}.mp3")

                        if os.path.exists(new_path):
                            os.remove(new_path)

                        os.rename(old_path, new_path)
                        return True

                return False
            else:
                return False

        except Exception as e:
            return False

    def download_lrc(self, song_name):
        """下载歌词"""
        try:
            search_url = f"https://lrclib.net/search/{quote(song_name)}"
            self.driver.get(search_url)

            time.sleep(3)

            # 优先查找带"Synced"标识的按钮
            first_button_found = self.driver.execute_script("""
                const buttons = document.querySelectorAll('button.rounded.text-indigo-700');

                // 首先查找带有"Synced"标识的按钮
                for (let button of buttons) {
                    const parentRow = button.closest('tr') || button.closest('div');
                    if (parentRow && parentRow.textContent.includes('Synced')) {
                        button.click();
                        return true;
                    }
                }

                // 如果没有找到Synced的,点击第一个按钮
                if (buttons.length > 0) {
                    buttons[0].click();
                    return true;
                }

                return false;
            """)

            if not first_button_found:
                return False, None

            time.sleep(2)

            lyrics_text = self.driver.execute_script("""
                const elements = document.querySelectorAll('*');
                for (let elem of elements) {
                    const text = elem.textContent;
                    if (text && text.includes('[00:') && text.length > 100) {
                        if (elem.children.length === 0 || elem.children.length === 1) {
                            return text;
                        }
                    }
                }
                return null;
            """)

            if lyrics_text and len(lyrics_text) > 50:
                return True, lyrics_text
            else:
                return False, None

        except Exception as e:
            return False, None

    def save_lrc(self, filename, lyrics_content):
        """保存歌词"""
        try:
            safe_filename = self.sanitize_filename(filename)
            lrc_path = os.path.join(self.download_dir, f"{safe_filename}.lrc")
            with open(lrc_path, 'w', encoding='utf-8') as f:
                f.write(lyrics_content)
            return True
        except Exception as e:
            return False

    def append_to_file(self, filename, song_name, status):
        """追加记录"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp} - {song_name} - {status}\n")

    # 窗口控制函数（简化版，使用系统原生功能）
    def bind_hover(self, widget, hover_color, normal_color):
        """绑定鼠标悬停效果"""
        widget.bind("<Enter>", lambda e: widget.config(bg=hover_color))
        widget.bind("<Leave>", lambda e: widget.config(bg=normal_color))

    def toggle_desktop_lyric(self):
        """切换桌面歌词显示"""
        self.show_desktop_lyric = not self.show_desktop_lyric

        if self.show_desktop_lyric:
            # 创建桌面歌词窗口
            if not self.desktop_lyric_window:
                self.desktop_lyric_window = Toplevel(self.root)
                self.desktop_lyric_window.title("桌面歌词")

                # 设置窗口属性
                self.desktop_lyric_window.overrideredirect(True)
                self.desktop_lyric_window.attributes('-topmost', True)
                self.desktop_lyric_window.attributes('-alpha', 0.85)

                # 窗口大小和位置
                screen_width = self.root.winfo_screenwidth()
                window_width = 800
                window_height = 120
                x = (screen_width - window_width) // 2
                y = 50
                self.desktop_lyric_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

                # 设置背景
                self.desktop_lyric_window.configure(bg='#1a1a1a')

                # 歌词标签
                self.desktop_lyric_label = Label(
                    self.desktop_lyric_window,
                    text="暂无播放",
                    font=("Microsoft YaHei UI", 20, "bold"),
                    bg='#1a1a1a',
                    fg='white',
                    wraplength=750,
                    justify=CENTER
                )
                self.desktop_lyric_label.pack(expand=True, fill=BOTH, padx=20, pady=20)

                # 支持拖动
                self.desktop_lyric_label.bind('<Button-1>', self.desktop_lyric_drag_start)
                self.desktop_lyric_label.bind('<B1-Motion>', self.desktop_lyric_drag)

                # 双击关闭
                self.desktop_lyric_label.bind('<Double-Button-1>', lambda e: self.toggle_desktop_lyric())
            else:
                self.desktop_lyric_window.deiconify()

            # 更新按钮状态
            self.desktop_lyric_btn.config(bg="#d63939")
        else:
            # 隐藏桌面歌词
            if self.desktop_lyric_window:
                self.desktop_lyric_window.withdraw()

            # 更新按钮状态
            self.desktop_lyric_btn.config(bg=self.primary_color)

    def desktop_lyric_drag_start(self, event):
        """桌面歌词拖动开始"""
        self.desktop_lyric_x = event.x
        self.desktop_lyric_y = event.y

    def desktop_lyric_drag(self, event):
        """桌面歌词拖动"""
        x = self.desktop_lyric_window.winfo_x() + event.x - self.desktop_lyric_x
        y = self.desktop_lyric_window.winfo_y() + event.y - self.desktop_lyric_y
        self.desktop_lyric_window.geometry(f"+{x}+{y}")

    def update_desktop_lyric(self, text):
        """更新桌面歌词内容"""
        if self.show_desktop_lyric and self.desktop_lyric_window:
            try:
                self.desktop_lyric_label.config(text=text)
            except:
                pass

    def show_about(self):
        """显示关于信息"""
        messagebox.showinfo(
            "关于 马赫坡音乐",
            "本软件仅供学习交流使用\n\n"
            "请支持正版音乐\n"
            "严禁用于商业盈利及任何违法用途\n\n"
            "技术交流 · 尊重版权 · 合法使用"
        )


def check_single_instance():
    """检查是否已有实例运行，如果有则激活已有窗口"""
    import ctypes
    from ctypes import wintypes

    # 创建互斥锁
    mutex_name = "Global\\MahepoMusicDownloaderMutex"
    kernel32 = ctypes.windll.kernel32

    # 尝试创建互斥锁
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    last_error = kernel32.GetLastError()

    # ERROR_ALREADY_EXISTS = 183
    if last_error == 183:
        # 已有实例运行，查找并激活窗口
        user32 = ctypes.windll.user32

        def find_window_callback(hwnd, lParam):
            """窗口枚举回调函数"""
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                if "马赫坡音乐" in buffer.value:
                    # 找到窗口，激活它
                    SW_RESTORE = 9
                    if user32.IsIconic(hwnd):  # 如果最小化了
                        user32.ShowWindow(hwnd, SW_RESTORE)
                    user32.SetForegroundWindow(hwnd)
                    return False  # 停止枚举
            return True  # 继续枚举

        # 定义回调函数类型
        EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        callback = EnumWindowsProc(find_window_callback)

        # 枚举所有顶层窗口
        user32.EnumWindows(callback, 0)

        return False  # 返回False表示已有实例

    return True  # 返回True表示是第一个实例


def main():
    """主函数"""
    # 检查单例
    if not check_single_instance():
        return

    # 异步提取使用说明（不阻塞）
    threading.Thread(target=extract_usage_instructions, daemon=True).start()

    # 快速启动GUI
    root = Tk()
    app = MusicDownloaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
