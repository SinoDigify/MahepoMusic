@echo off
chcp 65001 >nul
echo ====================================
echo 音乐下载器初始化脚本
echo ====================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

echo [1/4] 安装Python依赖...
pip install pyperclip selenium pyarmor pyinstaller

echo.
echo [2/4] 下载Chrome for Testing...
echo 正在下载 Chrome for Testing v141.0.7390.54 (约168MB)...

REM 创建chrome_bundle目录
if not exist chrome_bundle mkdir chrome_bundle
cd chrome_bundle

REM 下载Chrome for Testing
curl -L -o chrome-win64.zip "https://storage.googleapis.com/chrome-for-testing-public/141.0.7390.54/win64/chrome-win64.zip"
if errorlevel 1 (
    echo [错误] Chrome下载失败
    cd ..
    pause
    exit /b 1
)

echo 正在解压Chrome...
tar -xf chrome-win64.zip
del chrome-win64.zip

echo.
echo [3/4] 下载ChromeDriver...
echo 正在下载 ChromeDriver v141.0.7390.54 (约9.2MB)...

curl -L -o chromedriver-win64.zip "https://storage.googleapis.com/chrome-for-testing-public/141.0.7390.54/win64/chromedriver-win64.zip"
if errorlevel 1 (
    echo [错误] ChromeDriver下载失败
    cd ..
    pause
    exit /b 1
)

echo 正在解压ChromeDriver...
tar -xf chromedriver-win64.zip
del chromedriver-win64.zip

cd ..

echo.
echo [4/4] 创建必要的目录...
if not exist download mkdir download
if not exist doc mkdir doc

echo.
echo ====================================
echo 初始化完成！
echo ====================================
echo.
echo 接下来的步骤：
echo 1. 编辑 todo-download.txt 添加要下载的歌曲
echo 2. 运行 python music_downloader_v2.py 开始下载
echo.
echo 如需打包exe，运行：
echo 1. pyarmor gen -O obfuscated music_downloader_v2.py
echo 2. pyinstaller music_downloader.spec
echo.
pause
