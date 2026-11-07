# Fully automatic Python packaging tool V2.0

V2.0 提供图形界面和一键打包：可将 Python 项目构建为 EXE/平台可执行程序，也可以把 Python、图片、配置、网页等任意项目文件归档为 ZIP、TAR.GZ、TAR.BZ2 或 TAR.XZ。

## 启动图形界面

需要 Python 3.8+ 和 Tkinter（多数 Python 安装自带）：

```bash
python gui.py
```

图形界面支持选择项目目录、入口文件、应用名称、图标、输出格式和输出位置。选择 EXE 时可选单文件/目录模式、GUI 隐藏控制台、清理缓存；缺少 PyInstaller 时可以勾选自动安装（需要网络）。选择 ZIP/TAR 时直接归档项目，不需要额外依赖。

> Windows 的 `.exe` 需要在 Windows 上构建。PyInstaller 不能通常不能跨操作系统交叉编译；macOS/Linux 上生成的是对应平台的可执行程序，不是 Windows EXE。

## 命令行打包 Python 程序

V1.0 命令行仍然可用：

```bash
python -m pip install pyinstaller
python packager.py --project ./my_app --entry main.py --name MyApp --mode onefile
```

## 支持的归档格式

- ZIP (`.zip`)
- TAR + gzip (`.tar.gz`)
- TAR + bzip2 (`.tar.bz2`)
- TAR + xz (`.tar.xz`)

GUI 归档项目时会保留相对目录结构，并自动排除 `.git`、虚拟环境、构建输出、缓存和 Python 字节码；不会修改项目源文件。输出归档可放在项目目录下。

## 测试

```bash
python -m unittest discover -s tests -v
```

## 安全和平台说明

- 仅对你信任的项目运行打包。自动安装 PyInstaller 会通过 pip 安装第三方软件包。
- 归档包包含项目文件，请在分享前检查是否包含密钥、凭据或其他敏感信息。
- EXE 需要在 Windows 环境构建；其他系统请在对应系统分别构建和测试。
