# Fully automatic Python packaging tool V4.0

V4.0 优化了桌面界面：重新整理项目和输出设置，增加浅色/深色主题切换、构建进度动画、独立日志页和清空日志功能。无需额外 UI 依赖，使用 Python 自带 Tkinter。

## 启动

已安装 Python 3.10+ 和 Tkinter 时：

```bash
python gui.py
```

V3.0 启动器仍可使用：Windows 双击 `start.bat`；macOS/Linux 运行 `bash start.sh`。启动器检测 Python，必要时在用户确认后尝试通过系统包管理器安装。网络、权限和平台策略可能影响安装。

## 界面功能

- 浅色/深色主题切换。
- 项目目录、Python 入口、图标、应用名称集中配置。
- 输出为当前平台可执行程序（PyInstaller），或 ZIP、TAR.GZ、TAR.BZ2、TAR.XZ。
- 可执行程序支持单文件/目录模式、GUI 隐藏控制台、清理缓存及可选安装 PyInstaller。
- 后台运行构建任务，提供状态、进度动画和实时日志。

## 注意事项

- Windows `.exe` 应在 Windows 上构建；其他系统生成当前系统平台的可执行程序。建议在各目标系统分别构建和测试。
- 自动安装 PyInstaller 使用当前 Python 环境的 pip。
- ZIP/TAR 归档会保留相对路径并排除常见虚拟环境、构建目录、缓存和字节码。分享前请检查是否含有密钥或敏感文件。
- 只对可信项目运行打包；PyInstaller 会分析项目代码。

## 命令行

```bash
python -m pip install pyinstaller
python packager.py --project ./my_app --entry main.py --name MyApp --mode onefile
```

## 测试

```bash
python -m unittest discover -s tests -v
```
