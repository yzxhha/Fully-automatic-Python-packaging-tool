# Fully automatic Python packaging tool

一个基于 Python 和 PyInstaller 的轻量级自动打包工具：可交互式快速打包，也可通过命令行指定入口、单文件/目录模式、图标、资源文件和动态导入模块。

## 环境要求

- Python 3.8 或更高版本
- PyInstaller（首次使用前安装，或在运行时选择让工具通过 pip 安装）
- 请在目标操作系统上构建程序；PyInstaller 通常不会跨平台交叉编译

```bash
python -m pip install pyinstaller
```

## 快速开始

将 `packager.py` 放入项目，或从本仓库运行：

```bash
python packager.py
```

按提示输入项目目录，入口文件会优先按 `main.py`、`app.py`、`run.py`、`__main__.py` 自动检测。若这些文件均不存在，且项目根目录恰有一个普通 `.py` 文件，则使用该文件；否则请明确指定入口。

默认生成单文件程序，输出到项目的 `dist/` 目录。

## 命令行用法

```bash
python packager.py --project ./my_app --entry main.py --name MyApp --mode onefile
```

常用选项：

| 选项 | 说明 |
| --- | --- |
| `--project DIR` | 项目目录，默认当前目录 |
| `--entry FILE` | 项目内的 Python 入口文件，默认自动检测 |
| `--name NAME` | 输出程序名称，默认项目目录名 |
| `--mode onefile\|onedir` | 单文件或目录模式，默认 `onefile` |
| `--output DIR` | 输出目录，默认 `<项目>/dist` |
| `--windowed` | GUI 程序不显示控制台窗口 |
| `--icon FILE` | 指定图标（Windows 通常用 `.ico`，macOS 用 `.icns`） |
| `--add-data SRC=DEST` | 添加程序运行所需的资源文件/目录；可多次使用 |
| `--hidden-import MODULE` | 补充 PyInstaller 无法自动发现的动态导入模块；可多次使用 |
| `--clean` | 清理 PyInstaller 缓存后再构建 |
| `--install-pyinstaller` | 缺少 PyInstaller 时通过当前 Python 的 pip 安装（需要网络） |

添加资源和动态导入示例：

```bash
python packager.py \
  --project ./my_app \
  --entry main.py \
  --mode onedir \
  --add-data assets=assets \
  --add-data config/default.json=config \
  --hidden-import my_app.plugins.csv_plugin
```

Windows PowerShell 示例：

```powershell
python .\packager.py --project .\my_app --entry main.py --name MyApp --mode onefile --windowed
```

## 注意事项

- `--add-data` 的 `SRC=DEST` 中，来源可以是文件或目录，目标是程序运行时对应的相对目录；`=` 格式可兼容 Windows 盘符路径。
- `--windowed` 适用于图形界面应用。命令行工具不要启用，否则将看不到控制台输出。
- 打包前请先在项目自身的虚拟环境中安装应用依赖，并验证程序能够正常运行。PyInstaller 会分析入口及其导入，但动态导入可能需要 `--hidden-import`。
- 输出目录会由 PyInstaller 管理；工具不会删除项目源文件。请不要对不信任的项目运行打包或安装依赖。
- 生成的可执行文件通常只能在相同操作系统及兼容环境中运行。不同系统请分别构建和测试。

## 测试

本工具核心逻辑使用 Python 标准库，可运行：

```bash
python -m unittest discover -s tests -v
```
