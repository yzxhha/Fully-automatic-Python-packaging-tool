#!/usr/bin/env python3
"""A small, cross-platform helper for building Python apps with PyInstaller."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence


PREFERRED_ENTRIES = ("main.py", "app.py", "run.py", "__main__.py")


def discover_entry(project: Path) -> Path:
    """Find a likely application entry point in the project root."""
    for filename in PREFERRED_ENTRIES:
        candidate = project / filename
        if candidate.is_file():
            return candidate

    candidates = sorted(
        path
        for path in project.glob("*.py")
        if path.name not in {"setup.py", "conftest.py"}
        and not path.name.startswith("test_")
    )
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError(f"在项目根目录中没有找到 Python 入口文件：{project}")
    names = ", ".join(path.name for path in candidates)
    raise ValueError(f"检测到多个入口文件（{names}），请使用 --entry 指定。")


def parse_data_mapping(value: str) -> tuple[Path, str]:
    """Parse SRC=DEST, using '=' to remain unambiguous on Windows paths."""
    if "=" not in value:
        raise argparse.ArgumentTypeError("资源格式应为 SRC=DEST，例如 assets=assets")
    source_text, destination = value.split("=", 1)
    if not source_text or not destination:
        raise argparse.ArgumentTypeError("资源来源和打包后的目标路径都不能为空")
    source = Path(source_text).expanduser().resolve()
    if not source.exists():
        raise argparse.ArgumentTypeError(f"资源不存在：{source}")
    return source, destination


def build_command(
    *,
    entry: Path,
    project: Path,
    name: str,
    mode: str,
    output: Path,
    work: Path,
    spec: Path,
    windowed: bool = False,
    icon: Path | None = None,
    add_data: Sequence[tuple[Path, str]] = (),
    hidden_imports: Sequence[str] = (),
    clean: bool = False,
) -> list[str]:
    """Create a PyInstaller argv list (never invoke through a shell)."""
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--name",
        name,
        "--distpath",
        str(output),
        "--workpath",
        str(work),
        "--specpath",
        str(spec),
        "--onefile" if mode == "onefile" else "--onedir",
    ]
    if windowed:
        command.append("--windowed")
    if icon:
        command.extend(("--icon", str(icon)))
    if clean:
        command.append("--clean")

    data_separator = ";" if os.name == "nt" else ":"
    for source, destination in add_data:
        command.extend(("--add-data", f"{source}{data_separator}{destination}"))
    for module in hidden_imports:
        command.extend(("--hidden-import", module))

    command.append(str(entry))
    return command


def ensure_pyinstaller(install: bool) -> None:
    try:
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        if not install:
            raise RuntimeError(
                "当前 Python 环境未安装 PyInstaller。请运行 `python -m pip install pyinstaller`，"
                "或在本工具命令中添加 --install-pyinstaller。"
            )
        print("正在当前 Python 环境中安装 PyInstaller…")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller"], check=True
        )


def run_build(args: argparse.Namespace) -> int:
    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        raise ValueError(f"项目目录不存在：{project}")

    entry = Path(args.entry).expanduser() if args.entry else discover_entry(project)
    if not entry.is_absolute():
        entry = project / entry
    entry = entry.resolve()
    if not entry.is_file() or entry.suffix.lower() != ".py":
        raise ValueError(f"入口文件不存在或不是 .py 文件：{entry}")
    try:
        entry.relative_to(project)
    except ValueError as exc:
        raise ValueError("入口文件必须位于项目目录内。") from exc

    name = args.name or project.name.replace(" ", "_")
    if not name.strip():
        raise ValueError("应用名称不能为空。")
    output = Path(args.output).expanduser().resolve() if args.output else project / "dist"
    work = project / "build" / "auto_packager"
    spec = work / "spec"
    icon = Path(args.icon).expanduser().resolve() if args.icon else None
    if icon and not icon.is_file():
        raise ValueError(f"图标文件不存在：{icon}")

    ensure_pyinstaller(args.install_pyinstaller)
    command = build_command(
        entry=entry,
        project=project,
        name=name,
        mode=args.mode,
        output=output,
        work=work,
        spec=spec,
        windowed=args.windowed,
        icon=icon,
        add_data=args.add_data,
        hidden_imports=args.hidden_import,
        clean=args.clean,
    )
    print(f"项目：{project}\n入口：{entry}\n模式：{args.mode}\n输出：{output}")
    print("开始打包…")
    subprocess.run(command, cwd=project, check=True)
    artifact = output / name
    if sys.platform == "win32":
        artifact = artifact.with_suffix(".exe")
    print(f"打包完成：{artifact}")
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="自动检测 Python 项目入口并调用 PyInstaller 生成可执行程序。"
    )
    parser.add_argument("--project", default=".", help="项目目录（默认：当前目录）")
    parser.add_argument("--entry", help="入口 .py 文件；默认自动检测")
    parser.add_argument("--name", help="输出程序名称；默认使用项目目录名")
    parser.add_argument(
        "--mode", choices=("onefile", "onedir"), default="onefile", help="打包模式"
    )
    parser.add_argument("--output", help="输出目录（默认：项目目录/dist）")
    parser.add_argument("--windowed", action="store_true", help="Windows/macOS GUI 程序不显示控制台")
    parser.add_argument("--icon", help="图标文件（Windows .ico；macOS .icns）")
    parser.add_argument(
        "--add-data",
        action="append",
        type=parse_data_mapping,
        default=[],
        metavar="SRC=DEST",
        help="添加数据文件或目录，可重复指定",
    )
    parser.add_argument(
        "--hidden-import", action="append", default=[], metavar="MODULE", help="补充动态导入模块，可重复指定"
    )
    parser.add_argument("--clean", action="store_true", help="打包前清理 PyInstaller 缓存")
    parser.add_argument(
        "--install-pyinstaller",
        action="store_true",
        help="若未安装则通过 pip 安装 PyInstaller（需要网络）",
    )
    return parser


def interactive_wizard() -> int:
    """A short prompt-based flow for users who launch without arguments."""
    print("Python 自动打包工具（PyInstaller）")
    project_text = input("项目目录 [当前目录]: ").strip() or "."
    project = Path(project_text).expanduser().resolve()
    entry_text = input("入口文件 [自动检测]: ").strip()
    name = input("程序名称 [项目目录名]: ").strip() or None
    mode_text = input("打包模式 onefile/onedir [onefile]: ").strip().lower() or "onefile"
    if mode_text not in {"onefile", "onedir"}:
        raise ValueError("打包模式只能是 onefile 或 onedir。")
    install = input("若缺少 PyInstaller，是否尝试 pip 安装？y/N: ").strip().lower() == "y"
    args = make_parser().parse_args(
        ["--project", str(project), "--mode", mode_text]
        + (["--entry", entry_text] if entry_text else [])
        + (["--name", name] if name else [])
        + (["--install-pyinstaller"] if install else [])
    )
    return run_build(args)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        if argv is None:
            argv = sys.argv[1:]
        if not argv:
            return interactive_wizard()
        return run_build(make_parser().parse_args(argv))
    except (ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已取消。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
