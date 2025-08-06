@echo off
echo ========================================
echo    氧烛产品分析系统 v1.0
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

REM 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo [信息] 激活虚拟环境...
    call venv\Scripts\activate.bat
) else (
    echo [信息] 创建虚拟环境...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [信息] 安装依赖...
    pip install -r requirements.txt
)

echo.
echo 请选择运行模式：
echo 1. 一键运行全部分析
echo 2. Web界面
echo 3. 数据提取
echo 4. 评分排名
echo 5. 对比分析
echo.
set /p choice="请输入选项 (1-5): "

if "%choice%"=="1" (
    echo [运行] 一键分析...
    python 一键运行全部.py
) else if "%choice%"=="2" (
    echo [运行] 启动Web界面...
    echo 浏览器将自动打开 http://localhost:8501
    streamlit run 网页系统.py
) else if "%choice%"=="3" (
    python 简单分析程序.py
) else if "%choice%"=="4" (
    python 评分排名程序.py
) else if "%choice%"=="5" (
    python 对比分析程序.py
) else (
    echo [错误] 无效选项
)

pause
