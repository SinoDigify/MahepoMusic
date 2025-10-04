====================================
音乐下载器 V2 - 开发与使用说明
====================================

【项目简介】
自动下载音乐mp3文件和lrc歌词文件的工具。
使用Selenium自动化从MP3Juice下载音乐，从LRCLib下载歌词。

【快速开始开发】

1. 初始化项目（开发环境执行初始化）
   双击运行 init.bat 脚本，它会：
   - 安装Python依赖（pyperclip, selenium, pyarmor, pyinstaller）
   - 下载Chrome for Testing v141.0.7390.54 (约168MB)
   - 下载ChromeDriver v141.0.7390.54 (约9.2MB)
   - 创建必要的目录结构

2. 直接运行（开发模式）
   python music_downloader_v2.py

3. 打包为exe（发布模式）
   步骤1：pyarmor gen -O obfuscated music_downloader_v2.py
   步骤2：pyinstaller music_downloader.spec

【使用方法】

1. 创建待下载列表
   编辑 todo-download.txt 文件，每行一首歌曲，例如：

   Blinding Lights - The Weeknd
   Shape of You - Ed Sheeran
   Levitating - Dua Lipa

2. 运行程序
   - 开发模式：python music_downloader_v2.py
   - 打包后：双击 music_downloader.exe

3. 查看下载结果
   - 下载文件：download/ 文件夹
   - 成功记录：download-success.txt
   - 错误记录：download-err.txt

【项目结构】

music_downloader_v2.py  - 主程序源代码
README.txt              - 本说明文件
init.bat                - 初始化脚本
.gitignore              - Git忽略规则
doc/                    - 详细文档目录
chrome_bundle/          - Chrome浏览器和驱动（init.bat自动下载）
  ├─ chrome-win64/      - Chrome for Testing
  └─ chromedriver-win64/ - ChromeDriver

运行时生成的文件/目录：
todo-download.txt       - 待下载歌曲列表
download/               - 下载的音乐和歌词
download-success.txt    - 成功记录
download-err.txt        - 错误记录
obfuscated/             - PyArmor混淆后的代码
build/                  - PyInstaller构建目录
dist/                   - PyInstaller输出的exe
music_downloader.spec   - PyInstaller配置文件

【技术说明】

依赖项：
- Python 3.7+
- selenium - 浏览器自动化
- pyperclip - 剪贴板操作
- pyarmor - 代码混淆
- pyinstaller - 打包exe

Chrome Bundle：
- Chrome for Testing v141.0.7390.54 (约168MB)
  下载链接：https://storage.googleapis.com/chrome-for-testing-public/141.0.7390.54/win64/chrome-win64.zip
- ChromeDriver v141.0.7390.54 (约9.2MB)
  下载链接：https://storage.googleapis.com/chrome-for-testing-public/141.0.7390.54/win64/chromedriver-win64.zip

打包说明：
- 程序使用PyArmor进行代码混淆保护
- 使用PyInstaller打包为单文件exe
- 内置Chrome浏览器，无需用户安装
- 自动提取使用说明.txt到exe目录

【Git仓库说明】

仅提交源代码文件：
- music_downloader_v2.py
- README.txt

其他文件通过.gitignore排除：
- chrome_bundle/ （体积大，用户通过init.bat下载）
- build/, dist/, obfuscated/ （构建产物）
- download/ （运行时文件）
- *.spec （PyInstaller配置，可重新生成）

【详细文档】

请查看 doc/ 目录下的详细文档：
- 使用指南
- 开发文档
- 故障排除

====================================
