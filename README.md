# Fully automatic Python packaging tool — performance-focused UI

界面优先保持响应速度：轻量 Tkinter 启动、后台入口扫描/打包、批量处理构建日志并限制日志缓存。支持浅/深色主题、可执行程序构建及 ZIP/TAR 多格式归档。

## 启动

```bash
python gui.py
```

需要 Python 3.10+ 和 Tkinter。Windows/macOS/Linux 均可运行；PyInstaller 可执行文件需要在目标系统分别构建。

## 性能和稳定性

- 启动只导入标准 UI 库；归档器和 PyInstaller 相关模块按功能使用时导入。
- 项目入口扫描及构建/压缩任务放在后台线程，避免长时间 I/O 阻塞窗口。
- 日志按批次更新，每次 UI 轮询最多处理固定数量的事件，并自动限制最近日志行数，避免长构建日志持续占用内存或拖慢界面。
- 应用名称输入采用短暂防抖，避免每个按键都重复计算输出路径。

## 功能

- 单文件/目录模式构建当前平台可执行程序（PyInstaller）。
- 输出 ZIP、TAR.GZ、TAR.BZ2、TAR.XZ 项目归档。
- 深色/浅色主题、输出路径选择、构建进度和实时日志。
- 构建时禁用重复启动，项目/入口路径会进行基本校验。

## 注意事项

- Windows EXE 需在 Windows 上构建。跨系统构建请在对应操作系统执行。
- PyInstaller 会分析项目代码，仅打包你信任的项目。
- 分享归档前检查是否包含密钥或敏感信息。

## 测试

```bash
python -m unittest discover -s tests -v
```
