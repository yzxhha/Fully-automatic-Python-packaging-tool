"""Fast, dependency-free Tkinter interface for the automatic packager.

Keep startup imports small, do filesystem/build work off the UI thread, and batch
log updates so high-volume PyInstaller output does not make the window sluggish.
"""
from __future__ import annotations

import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

VERSION = "4.1.0"
EXE_FORMAT = "可执行程序（当前平台）"
ARCHIVE_EXTENSIONS = {
    "ZIP (.zip)": ".zip",
    "TAR.GZ (.tar.gz)": ".tar.gz",
    "TAR.BZ2 (.tar.bz2)": ".tar.bz2",
    "TAR.XZ (.tar.xz)": ".tar.xz",
}
PALETTES = {
    "light": {"bg": "#f3f6fb", "card": "#ffffff", "text": "#172033", "muted": "#64748b", "accent": "#2563eb", "field": "#ffffff", "log": "#111827", "log_text": "#e5edf7", "border": "#dbe3ee"},
    "dark": {"bg": "#111827", "card": "#1f2937", "text": "#f3f4f6", "muted": "#aab6c5", "accent": "#60a5fa", "field": "#273449", "log": "#0b1220", "log_text": "#d8e2f0", "border": "#374151"},
}
MAX_LOG_LINES = 3000
POLL_INTERVAL_MS = 120
MAX_EVENTS_PER_TICK = 250


class PackagerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"自动打包工作台 · V{VERSION}")
        self.geometry("960x760")
        self.minsize(760, 630)
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.busy = False
        self.theme = "light"
        cwd = Path.cwd()
        self.project_var = tk.StringVar(value=str(cwd))
        self.entry_var = tk.StringVar()
        self.icon_var = tk.StringVar()
        self.name_var = tk.StringVar(value=cwd.name or "MyApp")
        self.output_var = tk.StringVar()
        self.format_var = tk.StringVar(value=EXE_FORMAT)
        self.mode_var = tk.StringVar(value="单文件")
        self.windowed_var = tk.BooleanVar()
        self.clean_var = tk.BooleanVar()
        self.install_var = tk.BooleanVar()
        self.status_var = tk.StringVar(value="就绪")
        self._setup_style()
        self._build_ui()
        self.name_var.trace_add("write", self._schedule_output_update)
        self._update_output()
        self._apply_theme()
        self.after(POLL_INTERVAL_MS, self._poll_events)

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", padding=(10, 7), font=("TkDefaultFont", 10))
        style.configure("Primary.TButton", padding=(16, 10), font=("TkDefaultFont", 10, "bold"))
        style.configure("TEntry", padding=7)
        style.configure("TCombobox", padding=6)
        style.configure("TLabelframe", padding=12)
        style.configure("TLabelframe.Label", font=("TkDefaultFont", 10, "bold"))
        style.configure("Title.TLabel", font=("TkDefaultFont", 21, "bold"))
        style.configure("Muted.TLabel", font=("TkDefaultFont", 10))

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=(22, 18))
        root.pack(fill="both", expand=True)
        header = ttk.Frame(root)
        header.pack(fill="x", pady=(0, 16))
        heading = ttk.Frame(header)
        heading.pack(side="left", fill="x", expand=True)
        ttk.Label(heading, text="自动打包工作台", style="Title.TLabel").pack(anchor="w")
        ttk.Label(heading, text="Python 应用一键构建 · 多格式项目归档", style="Muted.TLabel").pack(anchor="w", pady=(4, 0))
        self.theme_button = ttk.Button(header, text="☾ 深色模式", command=self._toggle_theme)
        self.theme_button.pack(side="right", anchor="n")

        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill="both", expand=True)
        settings = ttk.Frame(self.tabs, padding=16)
        self.logs_tab = ttk.Frame(self.tabs, padding=14)
        self.tabs.add(settings, text="  打包设置  ")
        self.tabs.add(self.logs_tab, text="  构建日志  ")

        project = ttk.LabelFrame(settings, text="  01  项目与文件  ", padding=13)
        project.pack(fill="x", pady=(0, 11))
        self._path_row(project, 0, "项目目录", self.project_var, self._choose_project, "浏览…")
        self._path_row(project, 1, "入口文件", self.entry_var, self._choose_entry, "选择 .py")
        self._path_row(project, 2, "图标文件", self.icon_var, self._choose_icon, "选择图标")
        ttk.Label(project, text="应用名称", width=12).grid(row=3, column=0, sticky="w", pady=5)
        ttk.Entry(project, textvariable=self.name_var).grid(row=3, column=1, columnspan=2, sticky="ew", padx=6, pady=5)
        project.columnconfigure(1, weight=1)

        output = ttk.LabelFrame(settings, text="  02  输出格式与位置  ", padding=13)
        output.pack(fill="x", pady=(0, 11))
        ttk.Label(output, text="输出格式", width=12).grid(row=0, column=0, sticky="w", pady=5)
        self.format_box = ttk.Combobox(output, textvariable=self.format_var, state="readonly", values=(EXE_FORMAT, *ARCHIVE_EXTENSIONS), width=28)
        self.format_box.grid(row=0, column=1, sticky="ew", padx=6, pady=5)
        self.format_box.bind("<<ComboboxSelected>>", lambda _event: self._update_output())
        ttk.Label(output, text="构建模式").grid(row=0, column=2, sticky="w", padx=(14, 4), pady=5)
        self.mode_box = ttk.Combobox(output, textvariable=self.mode_var, state="readonly", values=("单文件", "目录"), width=12)
        self.mode_box.grid(row=0, column=3, sticky="ew", padx=6, pady=5)
        self.mode_box.bind("<<ComboboxSelected>>", lambda _event: self._update_output())
        self._path_row(output, 1, "输出位置", self.output_var, self._choose_output, "浏览…")
        output.columnconfigure(1, weight=1)

        options = ttk.LabelFrame(settings, text="  03  高级选项  ", padding=13)
        options.pack(fill="x", pady=(0, 11))
        self.windowed_check = ttk.Checkbutton(options, text="GUI 应用：隐藏控制台", variable=self.windowed_var)
        self.windowed_check.grid(row=0, column=0, sticky="w", padx=(0, 18), pady=4)
        ttk.Checkbutton(options, text="清理构建缓存", variable=self.clean_var).grid(row=0, column=1, sticky="w", pady=4)
        self.install_check = ttk.Checkbutton(options, text="缺少 PyInstaller 时尝试 pip 安装（需要网络）", variable=self.install_var)
        self.install_check.grid(row=1, column=0, columnspan=2, sticky="w", pady=4)

        actions = ttk.Frame(settings)
        actions.pack(fill="x", pady=(1, 0))
        self.build_button = ttk.Button(actions, text="▶  开始打包", style="Primary.TButton", command=self._start_build)
        self.build_button.pack(side="left")
        ttk.Button(actions, text="打开输出目录", command=self._open_output).pack(side="left", padx=8)
        ttk.Button(actions, text="查看日志", command=lambda: self.tabs.select(self.logs_tab)).pack(side="left")
        ttk.Label(actions, textvariable=self.status_var, style="Muted.TLabel").pack(side="right")
        self.progress = ttk.Progressbar(settings, mode="indeterminate")
        self.progress.pack(fill="x", pady=(13, 0))

        log_head = ttk.Frame(self.logs_tab)
        log_head.pack(fill="x", pady=(0, 8))
        ttk.Label(log_head, text="构建输出", font=("TkDefaultFont", 11, "bold")).pack(side="left")
        ttk.Button(log_head, text="清空日志", command=self._clear_log).pack(side="right")
        self.log = tk.Text(self.logs_tab, wrap="word", state="disabled", relief="flat", padx=12, pady=10)
        scrollbar = ttk.Scrollbar(self.logs_tab, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._log("欢迎使用。选择项目与输出格式，然后点击“开始打包”。")

    @staticmethod
    def _path_row(parent: ttk.Frame, row: int, label: str, variable: tk.StringVar, command, button_text: str) -> None:
        ttk.Label(parent, text=label, width=12).grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=6, pady=5)
        ttk.Button(parent, text=button_text, command=command).grid(row=row, column=2, padx=(2, 0), pady=5)
        parent.columnconfigure(1, weight=1)

    def _schedule_output_update(self, *_args) -> None:
        if getattr(self, "_output_after_id", None):
            self.after_cancel(self._output_after_id)
        self._output_after_id = self.after(120, self._update_output)

    def _toggle_theme(self) -> None:
        self.theme = "dark" if self.theme == "light" else "light"
        self._apply_theme()

    def _apply_theme(self) -> None:
        c = PALETTES[self.theme]
        self.configure(background=c["bg"])
        style = ttk.Style(self)
        style.configure(".", background=c["bg"], foreground=c["text"])
        style.configure("TFrame", background=c["bg"])
        style.configure("TLabel", background=c["bg"], foreground=c["text"])
        style.configure("Muted.TLabel", foreground=c["muted"])
        style.configure("TLabelframe", background=c["card"], foreground=c["text"], bordercolor=c["border"])
        style.configure("TLabelframe.Label", background=c["card"], foreground=c["text"])
        style.configure("TEntry", fieldbackground=c["field"], foreground=c["text"], insertcolor=c["text"])
        style.configure("TCombobox", fieldbackground=c["field"], foreground=c["text"], background=c["card"])
        style.map("TCombobox", fieldbackground=[("readonly", c["field"])], foreground=[("readonly", c["text"])])
        style.configure("TCheckbutton", background=c["card"], foreground=c["text"])
        style.configure("TNotebook", background=c["bg"])
        style.configure("TNotebook.Tab", background=c["card"], foreground=c["text"], padding=(14, 8))
        style.map("TNotebook.Tab", background=[("selected", c["accent"])], foreground=[("selected", "#ffffff")])
        style.configure("TButton", background=c["card"], foreground=c["text"], bordercolor=c["border"])
        style.map("TButton", background=[("active", c["border"])])
        style.configure("Primary.TButton", background=c["accent"], foreground="#ffffff")
        style.configure("TProgressbar", background=c["accent"], troughcolor=c["card"])
        self.log.configure(background=c["log"], foreground=c["log_text"], insertbackground=c["log_text"])
        self.theme_button.configure(text="☀ 浅色模式" if self.theme == "dark" else "☾ 深色模式")

    def _choose_project(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.project_var.get() or str(Path.cwd()))
        if not selected:
            return
        self.project_var.set(selected)
        self.name_var.set(Path(selected).name)
        # Entry discovery can touch slow/network drives; do it outside Tk's event loop.
        self.status_var.set("扫描项目入口…")
        threading.Thread(target=self._discover_entry_worker, args=(Path(selected),), daemon=True).start()
        self._update_output()

    def _discover_entry_worker(self, project: Path) -> None:
        try:
            from packager import discover_entry
            entry = str(discover_entry(project))
            self.events.put(("entry", entry))
        except ValueError:
            self.events.put(("entry", ""))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _choose_entry(self) -> None:
        selected = filedialog.askopenfilename(initialdir=self.project_var.get(), filetypes=[("Python 文件", "*.py"), ("所有文件", "*.*")])
        if selected:
            self.entry_var.set(selected)

    def _choose_icon(self) -> None:
        selected = filedialog.askopenfilename(filetypes=[("图标文件", "*.ico *.icns *.png"), ("所有文件", "*.*")])
        if selected:
            self.icon_var.set(selected)

    def _is_executable(self) -> bool:
        return self.format_var.get() == EXE_FORMAT

    def _extension(self) -> str:
        return ARCHIVE_EXTENSIONS[self.format_var.get()]

    def _update_output(self) -> None:
        self._output_after_id = None
        project = Path(self.project_var.get() or ".").expanduser()
        name = self.name_var.get().strip() or project.name or "MyApp"
        if self._is_executable():
            filename = name + (".exe" if sys.platform == "win32" else "") if self.mode_var.get() == "单文件" else name
            output = project / "dist"
            if self.mode_var.get() == "单文件":
                output /= filename
        else:
            output = project / "dist" / (name + self._extension())
        self.output_var.set(str(output))
        enabled = self._is_executable()
        self.mode_box.configure(state="readonly" if enabled else "disabled")
        self.windowed_check.configure(state="normal" if enabled else "disabled")
        self.install_check.configure(state="normal" if enabled else "disabled")

    def _choose_output(self) -> None:
        current = Path(self.output_var.get())
        if self._is_executable():
            selected = filedialog.askdirectory(initialdir=str(current if self.mode_var.get() == "目录" else current.parent), title="选择程序输出目录")
        else:
            selected = filedialog.asksaveasfilename(initialdir=str(current.parent), initialfile=current.name, defaultextension=self._extension(), filetypes=[(self.format_var.get(), "*" + self._extension()), ("所有文件", "*.*")])
        if selected:
            self.output_var.set(selected)

    def _settings(self) -> dict:
        project = Path(self.project_var.get()).expanduser().resolve()
        if not project.is_dir():
            raise ValueError(f"项目目录不存在：{project}")
        name = self.name_var.get().strip() or project.name
        if not name or Path(name).name != name or name in {".", ".."}:
            raise ValueError("应用名称需为有效文件名，不能包含目录路径。")
        output = Path(self.output_var.get()).expanduser().resolve()
        result = {"project": project, "name": name, "output": output}
        if self._is_executable():
            from packager import discover_entry
            text = self.entry_var.get().strip()
            entry = Path(text).expanduser() if text else discover_entry(project)
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
            result.update(kind="exe", entry=entry, icon=icon, mode="onefile" if self.mode_var.get() == "单文件" else "onedir", windowed=self.windowed_var.get(), clean=self.clean_var.get(), install=self.install_var.get())
        else:
            from archive_builder import ARCHIVE_FORMATS
            fmt = self.format_var.get()
            if not output.name.lower().endswith(ARCHIVE_FORMATS[fmt][0]):
                raise ValueError(f"输出文件扩展名必须是 {ARCHIVE_FORMATS[fmt][0]}")
            result.update(kind="archive", format=fmt)
        return result

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
        self.progress.start(12)
        self.tabs.select(self.logs_tab)
        self._log(f"开始：{settings['project']}")
        threading.Thread(target=self._build_worker, args=(settings,), daemon=True).start()

    def _build_worker(self, settings: dict) -> None:
        try:
            if settings["kind"] == "archive":
                from archive_builder import create_archive
                result = create_archive(settings["project"], settings["output"], settings["format"])
                self.events.put(("log", f"归档完成：{result}"))
            else:
                from packager import build_command, ensure_pyinstaller
                ensure_pyinstaller(settings["install"])
                work = settings["project"] / "build" / "auto_packager"
                destination = settings["output"].parent if settings["mode"] == "onefile" else settings["output"]
                command = build_command(entry=settings["entry"], project=settings["project"], name=settings["name"], mode=settings["mode"], output=destination, work=work, spec=work / "spec", windowed=settings["windowed"], icon=settings["icon"], clean=settings["clean"])
                self.events.put(("log", "运行 PyInstaller：" + subprocess.list2cmdline(command)))
                with subprocess.Popen(command, cwd=settings["project"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1) as process:
                    assert process.stdout is not None
                    for line in process.stdout:
                        self.events.put(("log", line.rstrip()))
                    code = process.wait()
                if code:
                    raise RuntimeError(f"PyInstaller 退出，错误代码：{code}")
                self.events.put(("log", f"打包完成：{settings['output']}"))
            self.events.put(("done", "成功"))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _poll_events(self) -> None:
        lines: list[str] = []
        terminal: tuple[str, str] | None = None
        for _ in range(MAX_EVENTS_PER_TICK):
            try:
                kind, text = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                lines.append(text)
            elif kind == "entry":
                self.entry_var.set(text)
                self.status_var.set("就绪")
            else:
                terminal = (kind, text)
        if lines:
            self._append_logs(lines)
        if terminal:
            kind, text = terminal
            self.busy = False
            self.progress.stop()
            self.build_button.configure(state="normal")
            self.status_var.set(text)
            if kind == "error":
                self._log("错误：" + text)
                messagebox.showerror("任务失败", text)
            else:
                messagebox.showinfo("打包完成", "任务已完成，请检查输出位置。")
        self.after(POLL_INTERVAL_MS, self._poll_events)

    def _append_logs(self, lines: list[str]) -> None:
        """Append a batch, then trim old lines to bound Text widget memory."""
        self.log.configure(state="normal")
        self.log.insert("end", "\n".join(lines) + "\n")
        line_count = int(self.log.index("end-1c").split(".", 1)[0])
        if line_count > MAX_LOG_LINES:
            self.log.delete("1.0", f"{line_count - MAX_LOG_LINES}.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _log(self, text: str) -> None:
        self._append_logs([text])

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
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
