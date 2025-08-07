@echo off
echo ====================================
echo    氧烛分析系统 - 测试版
echo ====================================
echo.

REM 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到Python
    echo 请安装Python 3.8或更高版本
    pause
    exit /b 1
)

REM 运行Python脚本
echo [运行] 启动分析系统...
python windows_app.py

pause
