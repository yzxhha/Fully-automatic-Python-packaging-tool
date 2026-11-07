"""Tkinter user interface for the automatic Python packaging tool."""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from archive_builder import ARCHIVE_FORMATS, create_archive
from packager import build_command, discover_entry, ensure_pyinstaller


class PackagerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("全自动多功能打包工具 V2.0")
        self.geometry("800x690")
        self.minsize(700, 600)
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.busy = False

        self.project_var = tk.StringVar(value=str(Path.cwd()))
        self.entry_var = tk.StringVar()
        self.name_var = tk.StringVar(value=Path.cwd().name or "MyApp")
        self.output_var = tk.StringVar()
        self.format_var = tk.StringVar(value="EXE（Windows/Linux/macOS）")
        self.mode_var = tk.StringVar(value="单文件")
        self.windowed_var = tk.BooleanVar(value=False)
        self.clean_var = tk.BooleanVar(value=False)
        self.install_var = tk.BooleanVar(value=False)
        self.icon_var = tk.StringVar()

        self._build_ui()
        self._update_output()
        self.after(100, self._poll_events)

    def _build_ui(self) -> None:
        container = ttk.Frame(self, padding=18)
        container.pack(fill="both", expand=True)
        ttk.Label(container, text="全自动多功能打包工具 V2.0", font=("TkDefaultFont", 18, "bold")).pack(anchor="w")
        ttk.Label(container, text="将 Python 项目打包为可执行程序，或将任意项目文件归档为 ZIP / TAR。", foreground="#555").pack(anchor="w", pady=(3, 14))

        form = ttk.Frame(container)
        form.pack(fill="x")
        self._path_row(form, 0, "项目目录", self.project_var, self._choose_project, "选择目录")
        self._path_row(form, 1, "入口文件", self.entry_var, self._choose_entry, "选择 .py")
        self._path_row(form, 2, "图标文件", self.icon_var, self._choose_icon, "选择图标")
        self._path_row(form, 3, "输出位置", self.output_var, self._choose_output, "选择位置")

        options = ttk.LabelFrame(container, text="打包选项", padding=12)
        options.pack(fill="x", pady=12)
        ttk.Label(options, text="输出格式").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=5)
        format_box = ttk.Combobox(options, textvariable=self.format_var, state="readonly", values=("EXE（Windows/Linux/macOS）", *ARCHIVE_FORMATS.keys()), width=28)
        format_box.grid(row=0, column=1, sticky="w", pady=5)
        format_box.bind("<<ComboboxSelected>>", lambda _event: self._update_output())
        ttk.Label(options, text="EXE 模式").grid(row=0, column=2, sticky="w", padx=(22, 8), pady=5)
        self.mode_box = ttk.Combobox(options, textvariable=self.mode_var, state="readonly", values=("单文件", "目录"), width=12)
        self.mode_box.grid(row=0, column=3, sticky="w", pady=5)
        self.mode_box.bind("<<ComboboxSelected>>", lambda _event: self._update_output())
        self.windowed_check = ttk.Checkbutton(options, text="GUI 程序（隐藏控制台）", variable=self.windowed_var)
        self.windowed_check.grid(row=1, column=0, columnspan=2, sticky="w", pady=5)
        ttk.Checkbutton(options, text="清理构建缓存", variable=self.clean_var).grid(row=1, column=2, columnspan=2, sticky="w", pady=5)
        ttk.Checkbutton(options, text="缺少 PyInstaller 时尝试 pip 安装（需要网络）", variable=self.install_var).grid(row=2, column=0, columnspan=4, sticky="w", pady=5)

        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=(0, 10))
        self.build_button = ttk.Button(actions, text="一键开始打包", command=self._start_build)
        self.build_button.pack(side="left")
        ttk.Button(actions, text="打开输出目录", command=self._open_output).pack(side="left", padx=8)
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(actions, textvariable=self.status_var).pack(side="right")

        log_frame = ttk.LabelFrame(container, text="构建日志", padding=8)
        log_frame.pack(fill="both", expand=True)
        self.log = tk.Text(log_frame, height=14, wrap="word", state="disabled")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._log("选择 EXE 将使用 PyInstaller；选择 ZIP/TAR 格式可归档项目中的多种文件类型。")

    @staticmethod
    def _path_row(parent: ttk.Frame, row: int, label: str, variable: tk.StringVar, command, button_text: str) -> None:
        ttk.Label(parent, text=label, width=11).grid(row=row, column=0, sticky="w", pady=5)
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", padx=6, pady=5)
        ttk.Button(parent, text=button_text, command=command).grid(row=row, column=2, pady=5)
        parent.columnconfigure(1, weight=1)

    def _choose_project(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.project_var.get() or str(Path.cwd()))
        if selected:
            self.project_var.set(selected)
            self.name_var.set(Path(selected).name)
            try:
                self.entry_var.set(str(discover_entry(Path(selected))))
            except ValueError:
                self.entry_var.set("")
            self._update_output()

    def _choose_entry(self) -> None:
        selected = filedialog.askopenfilename(initialdir=self.project_var.get(), filetypes=[("Python 文件", "*.py"), ("所有文件", "*.*")])
        if selected:
            self.entry_var.set(selected)

    def _choose_icon(self) -> None:
        selected = filedialog.askopenfilename(filetypes=[("图标文件", "*.ico *.icns *.png"), ("所有文件", "*.*")])
        if selected:
            self.icon_var.set(selected)

    def _choose_output(self) -> None:
        if self._is_executable():
            selected = filedialog.askdirectory(initialdir=self.output_var.get() or str(Path.cwd()), title="选择 EXE/程序输出目录")
        else:
            selected = filedialog.asksaveasfilename(initialdir=str(Path(self.output_var.get()).parent) if self.output_var.get() else str(Path.cwd()), initialfile=Path(self.output_var.get()).name if self.output_var.get() else "", defaultextension=self._extension(), filetypes=[(self.format_var.get(), "*" + self._extension()), ("所有文件", "*.*")])
        if selected:
            self.output_var.set(selected)

    def _is_executable(self) -> bool:
        return self.format_var.get().startswith("EXE")

    def _extension(self) -> str:
        return ARCHIVE_FORMATS[self.format_var.get()][0]

    def _update_output(self) -> None:
        project = Path(self.project_var.get() or ".").expanduser()
        name = self.name_var.get().strip() or project.name or "MyApp"
        if self._is_executable():
            suffix = ".exe" if sys.platform == "win32" else ""
            filename = name + suffix if self.mode_var.get() == "单文件" else name
            output = project / "dist"
            if self.mode_var.get() == "单文件":
                output = output / filename
        else:
            output = project / "dist" / (name + self._extension())
        self.output_var.set(str(output))
        state = "normal" if self._is_executable() else "disabled"
        self.mode_box.configure(state="readonly" if self._is_executable() else "disabled")
        self.windowed_check.configure(state=state)

    def _settings(self) -> dict:
        project = Path(self.project_var.get()).expanduser().resolve()
        if not project.is_dir():
            raise ValueError(f"项目目录不存在：{project}")
        name = self.name_var.get().strip() or project.name
        if not name or Path(name).name != name or name in {".", ".."}:
            raise ValueError("程序名称需为有效的文件名，不能包含目录路径。")
        output = Path(self.output_var.get()).expanduser().resolve()
        if self._is_executable():
            entry_text = self.entry_var.get().strip()
            entry = Path(entry_text).expanduser() if entry_text else discover_entry(project)
            if not entry.is_absolute():
                entry = project / entry
            entry = entry.resolve()
            if not entry.is_file() or entry.suffix.lower() != ".py":
                raise ValueError("请选择存在的 Python 入口文件。")
            try:
                entry.relative_to(project)
            except ValueError as exc:
                raise ValueError("入口文件必须位于项目目录内。") from exc
            icon = Path(self.icon_var.get()).expanduser().resolve() if self.icon_var.get().strip() else None
            if icon and not icon.is_file():
                raise ValueError(f"图标文件不存在：{icon}")
            return {"kind": "exe", "project": project, "name": name, "output": output, "entry": entry, "icon": icon}
        expected = self._extension()
        if not output.name.lower().endswith(expected):
            raise ValueError(f"输出文件扩展名必须是 {expected}")
        return {"kind": "archive", "project": project, "name": name, "output": output, "format": self.format_var.get()}

    def _start_build(self) -> None:
        if self.busy:
            return
        try:
            settings = self._settings()
        except (ValueError, OSError) as exc:
            messagebox.showerror("设置有误", str(exc))
            return
        self.busy = True
        self.build_button.configure(state="disabled")
        self.status_var.set("正在打包…")
        self._log(f"开始：{settings['project']}")
        threading.Thread(target=self._build_worker, args=(settings,), daemon=True).start()

    def _build_worker(self, settings: dict) -> None:
        try:
            if settings["kind"] == "archive":
                result = create_archive(settings["project"], settings["output"], settings["format"])
                self.events.put(("log", f"归档完成：{result}"))
            else:
                ensure_pyinstaller(self.install_var.get())
                work = settings["project"] / "build" / "auto_packager"
                command = build_command(
                    entry=settings["entry"], project=settings["project"], name=settings["name"],
                    mode="onefile" if self.mode_var.get() == "单文件" else "onedir",
                    output=settings["output"].parent if self.mode_var.get() == "单文件" else settings["output"],
                    work=work, spec=work / "spec", windowed=self.windowed_var.get(),
                    icon=settings["icon"], clean=self.clean_var.get(),
                )
                self.events.put(("log", "运行 PyInstaller：" + subprocess.list2cmdline(command)))
                process = subprocess.Popen(command, cwd=settings["project"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1)
                assert process.stdout is not None
                for line in process.stdout:
                    self.events.put(("log", line.rstrip()))
                return_code = process.wait()
                if return_code:
                    raise RuntimeError(f"PyInstaller 退出，错误代码：{return_code}")
                self.events.put(("log", f"打包完成：{settings['output']}"))
            self.events.put(("done", "成功"))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _poll_events(self) -> None:
        try:
            while True:
                kind, text = self.events.get_nowait()
                if kind == "log":
                    self._log(text)
                else:
                    self.busy = False
                    self.build_button.configure(state="normal")
                    self.status_var.set(text)
                    if kind == "error":
                        self._log("错误：" + text)
                        messagebox.showerror("打包失败", text)
                    else:
                        messagebox.showinfo("打包完成", "任务已完成，请检查输出位置。")
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _open_output(self) -> None:
        path = Path(self.output_var.get()).expanduser()
        folder = path if self._is_executable() and self.mode_var.get() == "目录" else path.parent
        if not folder.exists():
            messagebox.showinfo("输出目录", f"目录尚不存在：{folder}")
            return
        try:
            if sys.platform == "win32":
                import os
                os.startfile(str(folder))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except OSError as exc:
            messagebox.showerror("无法打开目录", str(exc))


def main() -> None:
    PackagerApp().mainloop()


if __name__ == "__main__":
    main()
