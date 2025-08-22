#!/bin/bash

echo "========================================="
echo "   AWK分析系统 - 公网访问启动器"
echo "========================================="
echo ""

# 启动Streamlit（后台运行）
echo "1. 启动分析系统..."
streamlit run 网页系统.py --server.headless true > streamlit.log 2>&1 &
STREAMLIT_PID=$!

# 等待Streamlit启动
echo "2. 等待系统启动..."
sleep 5

# 检查是否启动成功
if ! curl -s http://localhost:8501 > /dev/null; then
    echo "❌ 系统启动失败，请检查错误"
    cat streamlit.log
    exit 1
fi

echo "✅ 系统启动成功！"
echo ""

# 启动ngrok
echo "3. 创建公网访问通道..."
echo "========================================="
echo ""
echo "📡 公网地址将在下方显示："
echo ""

# 启动ngrok（前台运行，显示地址）
ngrok http 8501

# 用户按Ctrl+C后，清理进程
echo ""
echo "正在关闭系统..."
kill $STREAMLIT_PID 2>/dev/null
echo "已关闭，再见！"