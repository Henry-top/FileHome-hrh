# 打包指南：将Python程序转换为Windows可执行文件

## 准备工作

### 1. 安装Python
确保已安装Python 3.7或更高版本。

### 2. 安装依赖
运行以下命令安装所有必要的依赖：
```bash
pip install -r requirements.txt
```

或者双击运行 `install_dependencies.bat`

## 打包方法

### 方法一：使用打包脚本（推荐）

1. 运行打包脚本：
   ```bash
   python build.py
   ```

2. 打包完成后，在 `dist` 文件夹中找到 `FileOrganizer.exe`

### 方法二：手动打包

1. 使用PyInstaller命令：
   ```bash
   pyinstaller --onefile --windowed --name="FileOrganizer" --add-data="config.json;." main.py
   ```

2. 参数说明：
   - `--onefile`：打包成单个exe文件
   - `--windowed`：不显示控制台窗口
   - `--name`：指定输出文件名
   - `--add-data`：包含配置文件

### 方法三：使用spec文件（高级）

1. 生成spec文件：
   ```bash
   pyi-makespec --onefile --windowed --name="FileOrganizer" --add-data="config.json;." main.py
   ```

2. 编辑spec文件（可选）
3. 使用spec文件打包：
   ```bash
   pyinstaller FileOrganizer.spec
   ```

## 打包优化

### 减小文件大小

1. 使用UPX压缩：
   ```bash
   pyinstaller --onefile --windowed --upx-dir="path/to/upx" main.py
   ```

2. 排除不必要的模块：
   ```bash
   pyinstaller --onefile --windowed --exclude-module=unnecessary_module main.py
   ```

### 添加图标

```bash
pyinstaller --onefile --windowed --icon="icon.ico" main.py
```

## 测试打包结果

1. 在干净的Windows系统上测试
2. 检查所有功能是否正常
3. 验证配置文件是否正确包含
4. 测试文件拖拽和分类功能

## 常见问题

### 打包失败
- 检查Python版本兼容性
- 确保所有依赖正确安装
- 检查文件路径是否正确

### 程序无法启动
- 检查是否缺少依赖DLL
- 验证配置文件是否包含在exe中
- 尝试在命令行中运行查看错误信息

### 文件分类功能异常
- 确保目标文件夹路径存在
- 检查文件权限
- 验证配置文件格式

## 发布准备

1. 在多个Windows版本上测试
2. 准备安装说明文档
3. 考虑代码签名（可选）
4. 创建安装程序（可选）

## 注意事项

- 打包后的exe文件可能被某些杀毒软件误报，这是正常现象
- 建议在发布前进行充分的测试
- 保持Python环境和依赖版本的稳定性
