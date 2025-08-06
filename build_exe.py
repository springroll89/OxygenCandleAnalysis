# -*- coding: utf-8 -*-
"""
PyInstaller打包脚本
用于生成Windows可执行文件
"""

import PyInstaller.__main__
import os
import shutil

def build_exe():
    """构建可执行文件"""
    
    # 清理旧文件
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    
    # 打包一键运行程序
    PyInstaller.__main__.run([
        '一键运行全部.py',
        '--onefile',
        '--name=氧烛分析系统',
        '--noconfirm',
        '--clean',
        '--add-data=data;data',
        '--add-data=modules;modules',
        '--hidden-import=pandas',
        '--hidden-import=numpy',
        '--hidden-import=openpyxl',
        '--hidden-import=scipy',
        '--hidden-import=scipy.signal',
        '--hidden-import=scipy.ndimage',
    ])
    
    print("✅ 打包完成！可执行文件在 dist 目录")

if __name__ == "__main__":
    build_exe()
