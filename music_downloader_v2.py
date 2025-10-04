#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Music Downloader V2 - 下载音乐和歌词
使用Selenium自动化下载流程 (修复版)
"""

import os
import re
import time
import sys
import pyperclip
import shutil
from datetime import datetime
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
        # 打包后的exe
        return os.path.dirname(sys.executable)
    else:
        # 开发环境
        return os.path.dirname(os.path.abspath(__file__))


def extract_usage_instructions():
    """每次运行时展开使用说明文件到exe目录"""
    exe_dir = get_exe_dir()

    try:
        # 获取bundled资源路径
        if getattr(sys, 'frozen', False):
            bundle_dir = sys._MEIPASS
        else:
            bundle_dir = exe_dir

        bundled_readme = os.path.join(bundle_dir, "使用说明.txt")
        target_readme = os.path.join(exe_dir, "使用说明.txt")

        # 如果bundled文件存在，复制到exe目录（覆盖）
        if os.path.exists(bundled_readme):
            shutil.copy2(bundled_readme, target_readme)
            print(f"使用说明.txt已更新到: {exe_dir}")

    except Exception as e:
        print(f"展开使用说明失败: {str(e)}")


def extract_bundled_chrome():
    """解压bundled的Chrome文件到exe目录"""
    exe_dir = get_exe_dir()
    chrome_dir = os.path.join(exe_dir, "chrome")

    # 检查是否已经解压过
    chrome_exe = os.path.join(chrome_dir, "chrome.exe")
    chromedriver_exe = os.path.join(chrome_dir, "chromedriver.exe")

    if os.path.exists(chrome_exe) and os.path.exists(chromedriver_exe):
        print("Chrome已存在，跳过解压")
        return True

    print("正在解压bundled Chrome...")

    try:
        # 获取bundled资源路径
        if getattr(sys, 'frozen', False):
            # PyInstaller打包后的临时目录
            bundle_dir = sys._MEIPASS
        else:
            # 开发环境
            bundle_dir = exe_dir

        bundled_chrome_dir = os.path.join(bundle_dir, "chrome-win64")
        bundled_chromedriver_dir = os.path.join(bundle_dir, "chromedriver-win64")

        # 检查bundled文件是否存在
        if not os.path.exists(bundled_chrome_dir):
            print("未找到bundled Chrome，将使用系统Chrome")
            return False

        # 创建目标目录
        os.makedirs(chrome_dir, exist_ok=True)

        # 复制Chrome文件夹中的所有文件
        print("正在复制Chrome文件...")
        for item in os.listdir(bundled_chrome_dir):
            s = os.path.join(bundled_chrome_dir, item)
            d = os.path.join(chrome_dir, item)
            if os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)

        # 复制ChromeDriver
        print("正在复制ChromeDriver...")
        chromedriver_src = os.path.join(bundled_chromedriver_dir, "chromedriver.exe")
        if os.path.exists(chromedriver_src):
            shutil.copy2(chromedriver_src, chromedriver_exe)

        print("Chrome解压完成！")
        return True

    except Exception as e:
        print(f"解压Chrome失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


class MusicDownloader:
    def __init__(self, download_dir=None):
        """初始化下载器"""
        exe_dir = get_exe_dir()
        self.download_dir = download_dir or os.path.join(exe_dir, "download")
        self.todo_file = os.path.join(exe_dir, "todo-download.txt")
        self.success_file = os.path.join(exe_dir, "download-success.txt")
        self.error_file = os.path.join(exe_dir, "download-err.txt")
        self.driver = None

    def setup_driver(self):
        """设置Chrome驱动"""
        chrome_options = Options()
        # 设置下载目录
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

        # 尝试解压bundled Chrome（如果需要）
        extract_bundled_chrome()

        # 检查是否有bundled chrome
        exe_dir = get_exe_dir()
        chrome_path = os.path.join(exe_dir, "chrome", "chrome.exe")
        chromedriver_path = os.path.join(exe_dir, "chrome", "chromedriver.exe")

        # 如果存在bundled chrome，使用它
        if os.path.exists(chrome_path) and os.path.exists(chromedriver_path):
            from selenium.webdriver.chrome.service import Service
            print(f"使用bundled Chrome: {chrome_path}")
            chrome_options.binary_location = chrome_path
            service = Service(executable_path=chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            # 使用系统Chrome
            print("使用系统Chrome")
            self.driver = webdriver.Chrome(options=chrome_options)

        self.driver.implicitly_wait(10)

    def sanitize_filename(self, name):
        """清理文件名，移除非法字符"""
        # 移除或替换Windows文件名中的非法字符
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        # 移除前后空格
        name = name.strip()
        # 限制长度
        if len(name) > 200:
            name = name[:200]
        return name

    def get_latest_mp3_file(self):
        """获取下载目录中最新的MP3文件"""
        mp3_files = [f for f in os.listdir(self.download_dir) if f.endswith('.mp3')]
        if not mp3_files:
            return None
        mp3_files_with_time = [(f, os.path.getmtime(os.path.join(self.download_dir, f))) for f in mp3_files]
        latest_file = max(mp3_files_with_time, key=lambda x: x[1])[0]
        return latest_file

    def download_mp3_from_mp3juice(self, song_name):
        """从MP3Juice下载MP3"""
        try:
            print(f"正在搜索: {song_name}")

            # 记录下载前的MP3文件
            before_files = set(f for f in os.listdir(self.download_dir) if f.endswith('.mp3'))

            self.driver.get("https://mp3juice.co/")

            # 等待搜索框加载
            search_box = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="text"]'))
            )

            # 输入搜索内容
            search_query = f"{song_name}"
            search_box.clear()
            search_box.send_keys(search_query)

            # 点击搜索按钮
            search_button = self.driver.find_element(By.XPATH, '//button[contains(text(), "Search")]')
            search_button.click()

            # 等待搜索结果，查找"MP3 Download"链接
            print("等待搜索结果加载...")
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//a[text()="MP3 Download"]'))
            )

            print("搜索结果已加载")

            # 使用JavaScript点击第一个"MP3 Download"按钮，避免元素被遮挡
            download_buttons = self.driver.find_elements(By.XPATH, '//a[text()="MP3 Download"]')
            if download_buttons:
                self.driver.execute_script("arguments[0].click();", download_buttons[0])

                # 等待按钮文字变成"Download" (从initializing变为Download)
                print("等待转换完成（最长90秒）...")
                try:
                    # 一旦出现Download按钮就立即停止等待
                    download_link = WebDriverWait(self.driver, 90).until(
                        EC.presence_of_element_located((By.XPATH, '//a[text()="Download"]'))
                    )
                    print("准备下载")
                except TimeoutException:
                    print("等待Download超时90秒，跳过此歌曲")
                    return False

                print(f"准备下载: {song_name}")
                # 使用JavaScript点击下载链接，避免被遮挡
                self.driver.execute_script("arguments[0].click();", download_link)

                # 等待下载完成并重命名文件
                print("等待文件下载完成...")
                max_wait = 30  # 最多等待30秒
                for i in range(max_wait):
                    time.sleep(1)
                    after_files = set(f for f in os.listdir(self.download_dir) if f.endswith('.mp3'))
                    new_files = after_files - before_files

                    if new_files:
                        # 找到新下载的文件
                        downloaded_file = list(new_files)[0]
                        old_path = os.path.join(self.download_dir, downloaded_file)

                        # 重命名为标准名称
                        safe_name = self.sanitize_filename(song_name)
                        new_path = os.path.join(self.download_dir, f"{safe_name}.mp3")

                        # 如果目标文件已存在，先删除
                        if os.path.exists(new_path):
                            os.remove(new_path)

                        os.rename(old_path, new_path)
                        print(f"文件已重命名: {safe_name}.mp3")
                        return True

                print("下载超时，未检测到新文件")
                return False
            else:
                print("未找到下载")
                return False

        except Exception as e:
            print(f"下载失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def download_lrc_from_lrclib(self, song_name):
        """从LRCLib下载歌词"""
        try:
            print(f"正在搜索歌词: {song_name}")

            # 直接访问搜索URL
            search_url = f"https://lrclib.net/search/{quote(song_name)}"
            self.driver.get(search_url)

            # 等待搜索结果加载
            print("等待搜索结果加载...")
            time.sleep(3)

            # 查找并点击第一个歌词结果按钮
            try:
                # 等待页面加载
                time.sleep(2)

                # 查找class包含"rounded text-"的按钮（搜索结果按钮）
                first_button_found = self.driver.execute_script("""
                    const buttons = document.querySelectorAll('button.rounded.text-indigo-700');
                    if (buttons.length > 0) {
                        buttons[0].click();
                        return true;
                    }
                    return false;
                """)

                if not first_button_found:
                    print("未找到搜索结果")
                    return False, None

                print("找到搜索结果")

            except Exception as e:
                print(f"点击搜索结果失败: {str(e)}")
                return False, None

            # 等待歌词弹窗加载
            print("等待歌词弹窗加载...")
            time.sleep(2)

            # 直接从页面元素获取歌词，不使用复制（避免权限弹窗）
            try:
                print("尝试直接从页面读取歌词")
                lyrics_text = self.driver.execute_script("""
                    // 查找包含 [00: 格式的元素（歌词内容）
                    const elements = document.querySelectorAll('*');
                    for (let elem of elements) {
                        const text = elem.textContent;
                        if (text && text.includes('[00:') && text.length > 100) {
                            // 确保是最接近的、最直接包含歌词的元素
                            if (elem.children.length === 0 || elem.children.length === 1) {
                                return text;
                            }
                        }
                    }
                    return null;
                """)

                if lyrics_text and len(lyrics_text) > 50:
                    print(f"成功从页面获取歌词，长度: {len(lyrics_text)} 字符")
                    return True, lyrics_text
                else:
                    print("未找到有效歌词内容")
                    return False, None

            except TimeoutException:
                print("未找到复制")
                return False, None

        except Exception as e:
            print(f"下载歌词失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, None

    def save_lrc_file(self, filename, lyrics_content):
        """保存LRC文件"""
        try:
            safe_filename = self.sanitize_filename(filename)
            lrc_path = os.path.join(self.download_dir, f"{safe_filename}.lrc")

            with open(lrc_path, 'w', encoding='utf-8') as f:
                f.write(lyrics_content)

            print(f"歌词已保存: {lrc_path}")
            return True
        except Exception as e:
            print(f"保存歌词文件失败: {str(e)}")
            return False

    def read_todo_list(self):
        """读取待下载列表"""
        if not os.path.exists(self.todo_file):
            print(f"未找到 {self.todo_file} 文件，创建默认文件")
            # 创建默认的 todo-download.txt 文件
            with open(self.todo_file, 'w', encoding='utf-8') as f:
                f.write("You Are My Sunshine\n")
            print(f"已创建 {self.todo_file}，包含默认歌曲: You Are My Sunshine")

        with open(self.todo_file, 'r', encoding='utf-8') as f:
            songs = [line.strip() for line in f if line.strip()]

        return songs

    def append_to_file(self, filename, song_name, status="success"):
        """追加记录到文件"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp} - {song_name} - {status}\n")

    def update_todo_list(self, remaining_songs):
        """更新待下载列表"""
        with open(self.todo_file, 'w', encoding='utf-8') as f:
            for song in remaining_songs:
                f.write(f"{song}\n")

    def process_downloads(self):
        """处理所有下载任务"""
        songs = self.read_todo_list()

        if not songs:
            print("没有待下载的歌曲")
            return

        print(f"共有 {len(songs)} 首歌曲待下载")

        self.setup_driver()

        try:
            for i, song_name in enumerate(songs, 1):
                print(f"\n{'='*60}")
                print(f"[{i}/{len(songs)}] 正在处理: {song_name}")
                print(f"{'='*60}")

                # 下载MP3
                mp3_success = self.download_mp3_from_mp3juice(song_name)

                # 下载歌词
                lrc_success, lrc_content = self.download_lrc_from_lrclib(song_name)

                # 保存歌词 - 使用原始歌曲名，而不是从MP3Juice获取的标题
                if lrc_success and lrc_content:
                    safe_name = self.sanitize_filename(song_name)
                    lrc_saved = self.save_lrc_file(safe_name, lrc_content)
                else:
                    lrc_saved = False

                # 记录结果
                status_parts = []
                if mp3_success:
                    status_parts.append("MP3:成功")
                else:
                    status_parts.append("MP3:失败")

                if lrc_saved:
                    status_parts.append("歌词:成功")
                else:
                    status_parts.append("歌词:失败")

                status_msg = ", ".join(status_parts)

                if mp3_success or lrc_saved:
                    # 至少有一个成功就记录到成功文件
                    print(f"[完成] {song_name} - {status_msg}")
                    self.append_to_file(self.success_file, song_name, status_msg)

                if not mp3_success or not lrc_saved:
                    # 有任何失败就记录到错误文件
                    print(f"[部分失败] {song_name} - {status_msg}")
                    self.append_to_file(self.error_file, song_name, status_msg)

                # 等待一下，避免请求过快
                time.sleep(2)

            # 下载完成后，清空todo列表
            self.update_todo_list([])
            print(f"\n{'='*60}")
            print("所有下载任务已完成！")
            print(f"{'='*60}")

        finally:
            if self.driver:
                self.driver.quit()


def main():
    """主函数"""
    print("音乐下载器 V2 启动...")

    # 展开使用说明文件（每次运行都执行）
    extract_usage_instructions()

    # 设置下载目录为exe目录下的download子目录
    exe_dir = get_exe_dir()
    download_dir = os.path.join(exe_dir, "download")
    os.makedirs(download_dir, exist_ok=True)

    downloader = MusicDownloader(download_dir=download_dir)
    downloader.process_downloads()

    print("\n程序结束")


if __name__ == "__main__":
    main()
