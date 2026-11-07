# Fully automatic Python packaging tool

黑色系桌面打包工作台：启动后进入粒子动画欢迎首页，可一键进入构建设置。支持 Python 可执行程序构建及 ZIP/TAR 多格式归档。

## 启动

```bash
python gui.py
```

需要 Python 3.10+ 和 Tkinter。Windows/macOS/Linux 可运行；PyInstaller 可执行文件建议在目标系统分别构建。

## 欢迎首页

- 深黑背景、蓝色粒子网络与呼吸光点组成轻量动画。
- 粒子和连线在启动时创建一次；动画帧只更新已有 Canvas 图元，限制固定粒子数量，降低重绘开销。
- 首页提供“进入打包工作台”按钮；设置页、构建日志可通过顶部标签访问。

## 功能

- 当前平台可执行程序（PyInstaller，单文件或目录模式）。
- ZIP、TAR.GZ、TAR.BZ2、TAR.XZ 项目归档。
- 后台入口扫描与构建、实时日志、输出目录选择。
- 黑色系 UI、低开销粒子动画、日志行数上限。

## 注意

- Windows `.exe` 应在 Windows 上构建。
- PyInstaller 会分析项目代码，只打包可信项目。
- 分享归档前检查是否包含密钥或敏感文件。

## 测试

```bash
python -m unittest discover -s tests -v
```
