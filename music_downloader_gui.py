#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Music Downloader V2 - GUI Version
使用Selenium自动化下载流程 + 现代化GUI界面
"""

import os
import re
import time
import sys
import shutil
import threading
from datetime import datetime
from tkinter import *
from tkinter import ttk, scrolledtext, filedialog, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from urllib.parse import quote


def get_exe_dir():
    """获取exe所在目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def extract_usage_instructions():
    """每次运行时展开使用说明文件到exe目录"""
    exe_dir = get_exe_dir()
    try:
        if getattr(sys, 'frozen', False):
            bundle_dir = sys._MEIPASS
        else:
            bundle_dir = exe_dir

        bundled_readme = os.path.join(bundle_dir, "使用说明.txt")
        target_readme = os.path.join(exe_dir, "使用说明.txt")

        if os.path.exists(bundled_readme):
            shutil.copy2(bundled_readme, target_readme)
    except Exception as e:
        pass


def extract_bundled_chrome():
    """解压bundled的Chrome文件到exe目录"""
    exe_dir = get_exe_dir()
    chrome_dir = os.path.join(exe_dir, "chrome")

    chrome_exe = os.path.join(chrome_dir, "chrome.exe")
    chromedriver_exe = os.path.join(chrome_dir, "chromedriver.exe")

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

        for item in os.listdir(bundled_chrome_dir):
            s = os.path.join(bundled_chrome_dir, item)
            d = os.path.join(chrome_dir, item)
            if os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)

        chromedriver_src = os.path.join(bundled_chromedriver_dir, "chromedriver.exe")
        if os.path.exists(chromedriver_src):
            shutil.copy2(chromedriver_src, chromedriver_exe)

        return True

    except Exception as e:
        return False


class MusicDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("音乐下载器 V2")
        self.root.geometry("900x700")
        self.root.resizable(True, True)

        # 配置
        exe_dir = get_exe_dir()
        self.download_dir = os.path.join(exe_dir, "download")
        self.todo_file = os.path.join(exe_dir, "todo-download.txt")
        self.success_file = os.path.join(exe_dir, "download-success.txt")
        self.error_file = os.path.join(exe_dir, "download-err.txt")

        # 状态变量
        self.is_downloading = False
        self.driver = None

        # 设置主题颜色
        self.bg_color = "#f0f0f0"
        self.primary_color = "#4a90e2"
        self.success_color = "#5cb85c"
        self.error_color = "#d9534f"

        self.root.configure(bg=self.bg_color)

        self.create_widgets()
        self.load_todo_list()

    def create_widgets(self):
        # 标题区域
        title_frame = Frame(self.root, bg=self.primary_color, height=80)
        title_frame.pack(fill=X, padx=0, pady=0)
        title_frame.pack_propagate(False)

        title_label = Label(
            title_frame,
            text="🎵 音乐下载器",
            font=("Microsoft YaHei UI", 24, "bold"),
            bg=self.primary_color,
            fg="white"
        )
        title_label.pack(pady=20)

        # 主容器
        main_container = Frame(self.root, bg=self.bg_color)
        main_container.pack(fill=BOTH, expand=True, padx=20, pady=20)

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

        self.add_btn = Button(
            list_btn_frame,
            text="➕ 添加歌曲",
            font=("Microsoft YaHei UI", 10),
            bg=self.primary_color,
            fg="white",
            relief=FLAT,
            cursor="hand2",
            command=self.add_song
        )
        self.add_btn.pack(side=LEFT, padx=(0, 5))

        self.clear_btn = Button(
            list_btn_frame,
            text="🗑️ 清空列表",
            font=("Microsoft YaHei UI", 10),
            bg="#95a5a6",
            fg="white",
            relief=FLAT,
            cursor="hand2",
            command=self.clear_list
        )
        self.clear_btn.pack(side=LEFT, padx=(0, 5))

        self.load_btn = Button(
            list_btn_frame,
            text="📂 从文件加载",
            font=("Microsoft YaHei UI", 10),
            bg="#9b59b6",
            fg="white",
            relief=FLAT,
            cursor="hand2",
            command=self.load_from_file
        )
        self.load_btn.pack(side=LEFT)

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

    def log(self, message, level="INFO"):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # 根据级别设置颜色
        color_map = {
            "INFO": "#3498db",
            "SUCCESS": "#2ecc71",
            "ERROR": "#e74c3c",
            "WARNING": "#f39c12"
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
        """加载待下载列表"""
        if os.path.exists(self.todo_file):
            with open(self.todo_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self.song_text.delete(1.0, END)
                self.song_text.insert(1.0, content)

    def save_todo_list(self):
        """保存待下载列表"""
        content = self.song_text.get(1.0, END).strip()
        with open(self.todo_file, 'w', encoding='utf-8') as f:
            f.write(content)

    def add_song(self):
        """添加单首歌曲"""
        dialog = Toplevel(self.root)
        dialog.title("添加歌曲")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.configure(bg=self.bg_color)

        # 居中显示
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
                if current:
                    self.song_text.insert(END, "\n" + song)
                else:
                    self.song_text.insert(END, song)
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
                content = f.read()
                self.song_text.delete(1.0, END)
                self.song_text.insert(1.0, content)

    def start_download(self):
        """开始下载"""
        songs = self.song_text.get(1.0, END).strip().split('\n')
        songs = [s.strip() for s in songs if s.strip()]

        if not songs:
            messagebox.showwarning("警告", "请先添加要下载的歌曲！")
            return

        self.is_downloading = True
        self.start_btn.config(state=DISABLED)
        self.stop_btn.config(state=NORMAL)
        self.progress_bar.start(10)

        # 在新线程中执行下载
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

            # 设置Chrome驱动
            self.setup_driver()

            for i, song in enumerate(songs, 1):
                if not self.is_downloading:
                    break

                self.root.after(0, lambda s=song, idx=i, total=len(songs):
                    self.progress_label.config(text=f"正在下载 [{idx}/{total}]: {s}"))

                self.log(f"[{i}/{len(songs)}] 处理: {song}", "INFO")

                # 下载MP3
                mp3_success = self.download_mp3(song)

                # 下载歌词
                lrc_success, lrc_content = self.download_lrc(song)
                if lrc_success and lrc_content:
                    self.save_lrc(song, lrc_content)

                # 记录结果
                if mp3_success and lrc_success:
                    self.log(f"✓ {song} - 下载完成", "SUCCESS")
                    self.append_to_file(self.success_file, song, "MP3:成功, 歌词:成功")
                elif mp3_success:
                    self.log(f"⚠ {song} - MP3成功，歌词失败", "WARNING")
                    self.append_to_file(self.success_file, song, "MP3:成功, 歌词:失败")
                else:
                    self.log(f"✗ {song} - 下载失败", "ERROR")
                    self.append_to_file(self.error_file, song, "MP3:失败")

                time.sleep(2)

            if self.driver:
                self.driver.quit()

            if self.is_downloading:
                self.log("所有下载任务完成！", "SUCCESS")
                self.root.after(0, lambda: messagebox.showinfo("完成", "所有歌曲下载完成！"))
                self.song_text.delete(1.0, END)
                self.save_todo_list()

        except Exception as e:
            self.log(f"发生错误: {str(e)}", "ERROR")
        finally:
            self.is_downloading = False
            self.root.after(0, self.reset_ui)

    def setup_driver(self):
        """设置Chrome驱动"""
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
            from selenium.webdriver.chrome.service import Service
            chrome_options.binary_location = chrome_path
            service = Service(executable_path=chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            self.driver = webdriver.Chrome(options=chrome_options)

        self.driver.implicitly_wait(10)

    def sanitize_filename(self, name):
        """清理文件名"""
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        name = name.strip()
        if len(name) > 200:
            name = name[:200]
        return name

    def download_mp3(self, song_name):
        """下载MP3"""
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

            first_button_found = self.driver.execute_script("""
                const buttons = document.querySelectorAll('button.rounded.text-indigo-700');
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


def main():
    """主函数"""
    extract_usage_instructions()

    root = Tk()
    app = MusicDownloaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
