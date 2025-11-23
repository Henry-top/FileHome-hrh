import PyInstaller.__main__
import os

# 打包参数
params = [
    'main.py',
    '--name=FileOrganizer',
    '--onefile',
    '--windowed',
    '--icon=NONE',
    '--add-data=config.json;.',
    '--clean',
    '--noconfirm'
]

print("开始打包文件分类器...")
PyInstaller.__main__.run(params)
print("打包完成！可执行文件在 dist 文件夹中")
