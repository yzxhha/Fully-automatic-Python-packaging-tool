# Fully automatic Python packaging tool

轻量 Tkinter 图形界面，支持 Python 项目可执行程序构建和 ZIP/TAR 多格式归档。UI 顶部使用低开销 Canvas 粒子动画；构建和项目扫描在后台运行，构建日志批量更新并限制行数。

## 启动

```bash
python gui.py
```

需要 Python 3.10+ 和 Tkinter。PyInstaller 生成的可执行程序应在目标操作系统上分别构建。

## UI 动效与性能

- 顶部粒子横幅通过 Tkinter Canvas 绘制；粒子、连线在启动时创建一次，动画帧仅更新坐标和显示状态，不反复创建图形对象。
- 固定 18 个粒子，约每 40ms 更新；窗口最小化或横幅不可见时暂停绘制。
- 入口扫描和归档/可执行程序构建都在后台线程执行，界面使用事件队列接收结果。
- 实时日志批处理，并限制最多保留 2,500 行，避免长时间构建导致 UI 内存持续增长。

## 功能

- 当前平台可执行程序（PyInstaller，单文件或目录模式）。
- ZIP、TAR.GZ、TAR.BZ2、TAR.XZ 项目归档。
- 浅色/深色主题、输出位置选择、进度提示与构建日志。

## 注意

- Windows `.exe` 应在 Windows 上构建。
- 只打包可信项目；分享归档前检查是否包含凭据或敏感文件。

## 测试

```bash
python -m unittest discover -s tests -v
```
