"""Responsive Tkinter UI with a lightweight animated particle header."""
from __future__ import annotations

import itertools
import math
import queue
import random
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "全自动多功能打包工具"
EXE_FORMAT = "可执行程序（当前平台）"
ARCHIVE_EXTENSIONS = {
    "ZIP (.zip)": ".zip",
    "TAR.GZ (.tar.gz)": ".tar.gz",
    "TAR.BZ2 (.tar.bz2)": ".tar.bz2",
    "TAR.XZ (.tar.xz)": ".tar.xz",
}
PARTICLE_COUNT = 18
PARTICLE_TICK_MS = 40
MAX_LOG_LINES = 2500


class PackagerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE} · V6.0")
        self.geometry("940x740")
        self.minsize(740, 620)
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.busy = False
        self.dark = False
        self._particle_job: str | None = None
        self._particles: list[list[float]] = []
        self._particle_items: list[int] = []
        self._particle_lines: list[tuple[int, int, int]] = []
        self._project_generation = 0

        cwd = Path.cwd()
        self.project_var = tk.StringVar(value=str(cwd))
        self.entry_var = tk.StringVar()
        self.icon_var = tk.StringVar()
        self.name_var = tk.StringVar(value=cwd.name or "MyApp")
        self.output_var = tk.StringVar()
        self.format_var = tk.StringVar(value=EXE_FORMAT)
        self.mode_var = tk.StringVar(value="单文件")
        self.windowed_var = tk.BooleanVar(value=False)
        self.clean_var = tk.BooleanVar(value=False)
        self.install_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="就绪")

        self._setup_style()
        self._build_ui()
        self.name_var.trace_add("write", self._schedule_output_update)
        self._update_output()
        self._apply_theme()
        self._particle_job = self.after(PARTICLE_TICK_MS, self._animate_particles)
        self.after(100, self._poll_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

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
        style.configure("Title.TLabel", font=("TkDefaultFont", 20, "bold"))
        style.configure("Muted.TLabel", font=("TkDefaultFont", 10))

    def _build_ui(self) -> None:
        self.root_frame = ttk.Frame(self, padding=(22, 16))
        self.root_frame.pack(fill="both", expand=True)
        header = ttk.Frame(self.root_frame)
        header.pack(fill="x", pady=(0, 12))
        heading = ttk.Frame(header)
        heading.pack(side="left", fill="x", expand=True)
        ttk.Label(heading, text=APP_TITLE, style="Title.TLabel").pack(anchor="w")
        ttk.Label(heading, text="Python 应用构建 · 多格式项目归档", style="Muted.TLabel").pack(anchor="w", pady=(3, 0))
        self.theme_button = ttk.Button(header, text="☾ 深色模式", command=self._toggle_theme)
        self.theme_button.pack(side="right", anchor="n")

        # One small, fixed-size Canvas hosts pre-created items; animation only
        # updates coordinates and visibility (no per-frame item allocation).
        self.particle_canvas = tk.Canvas(self.root_frame, height=74, highlightthickness=0, bd=0)
        self.particle_canvas.pack(fill="x", pady=(0, 12))
        self.particle_canvas.bind("<Configure>", self._resize_particles)
        self._init_particles()

        self.tabs = ttk.Notebook(self.root_frame)
        self.tabs.pack(fill="both", expand=True)
        settings = ttk.Frame(self.tabs, padding=15)
        self.logs_tab = ttk.Frame(self.tabs, padding=13)
        self.tabs.add(settings, text="  打包设置  ")
        self.tabs.add(self.logs_tab, text="  构建日志  ")

        project = ttk.LabelFrame(settings, text="  项目与文件  ", padding=12)
        project.pack(fill="x", pady=(0, 10))
        self._path_row(project, 0, "项目目录", self.project_var, self._choose_project, "浏览…")
        self._path_row(project, 1, "入口文件", self.entry_var, self._choose_entry, "选择 .py")
        self._path_row(project, 2, "图标文件", self.icon_var, self._choose_icon, "选择图标")
        ttk.Label(project, text="应用名称", width=12).grid(row=3, column=0, sticky="w", pady=5)
        ttk.Entry(project, textvariable=self.name_var).grid(row=3, column=1, columnspan=2, sticky="ew", padx=6, pady=5)
        project.columnconfigure(1, weight=1)

        output = ttk.LabelFrame(settings, text="  输出格式与位置  ", padding=12)
        output.pack(fill="x", pady=(0, 10))
        ttk.Label(output, text="输出格式", width=12).grid(row=0, column=0, sticky="w", pady=5)
        self.format_box = ttk.Combobox(output, textvariable=self.format_var, state="readonly", values=(EXE_FORMAT, *ARCHIVE_EXTENSIONS), width=27)
        self.format_box.grid(row=0, column=1, sticky="ew", padx=6, pady=5)
        self.format_box.bind("<<ComboboxSelected>>", lambda _event: self._update_output())
        ttk.Label(output, text="模式").grid(row=0, column=2, sticky="w", padx=(12, 4), pady=5)
        self.mode_box = ttk.Combobox(output, textvariable=self.mode_var, state="readonly", values=("单文件", "目录"), width=11)
        self.mode_box.grid(row=0, column=3, sticky="ew", padx=6, pady=5)
        self.mode_box.bind("<<ComboboxSelected>>", lambda _event: self._update_output())
        self._path_row(output, 1, "输出位置", self.output_var, self._choose_output, "浏览…")
        output.columnconfigure(1, weight=1)

        options = ttk.LabelFrame(settings, text="  选项  ", padding=12)
        options.pack(fill="x", pady=(0, 10))
        self.windowed_check = ttk.Checkbutton(options, text="GUI 应用（隐藏控制台）", variable=self.windowed_var)
        self.windowed_check.grid(row=0, column=0, sticky="w", padx=(0, 16), pady=4)
        ttk.Checkbutton(options, text="清理构建缓存", variable=self.clean_var).grid(row=0, column=1, sticky="w", pady=4)
        self.install_check = ttk.Checkbutton(options, text="缺少 PyInstaller 时尝试 pip 安装（需要网络）", variable=self.install_var)
        self.install_check.grid(row=1, column=0, columnspan=2, sticky="w", pady=4)

        actions = ttk.Frame(settings)
        actions.pack(fill="x", pady=2)
        self.build_button = ttk.Button(actions, text="▶  开始打包", style="Primary.TButton", command=self._start_build)
        self.build_button.pack(side="left")
        ttk.Button(actions, text="打开输出目录", command=self._open_output).pack(side="left", padx=8)
        ttk.Button(actions, text="查看日志", command=lambda: self.tabs.select(self.logs_tab)).pack(side="left")
        ttk.Label(actions, textvariable=self.status_var, style="Muted.TLabel").pack(side="right")
        self.progress = ttk.Progressbar(settings, mode="indeterminate")
        self.progress.pack(fill="x", pady=(10, 0))

        log_header = ttk.Frame(self.logs_tab)
        log_header.pack(fill="x", pady=(0, 7))
        ttk.Label(log_header, text="构建输出", font=("TkDefaultFont", 11, "bold")).pack(side="left")
        ttk.Button(log_header, text="清空日志", command=self._clear_log).pack(side="right")
        self.log = tk.Text(self.logs_tab, wrap="word", state="disabled", relief="flat", padx=10, pady=9)
        scrollbar = ttk.Scrollbar(self.logs_tab, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._log("欢迎使用。粒子动画使用固定数量 Canvas 对象，尽量减少 UI 开销。")

    @staticmethod
    def _path_row(parent: ttk.Frame, row: int, label: str, variable: tk.StringVar, command, button_text: str) -> None:
        ttk.Label(parent, text=label, width=12).grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=6, pady=5)
        ttk.Button(parent, text=button_text, command=command).grid(row=row, column=2, padx=(2, 0), pady=5)
        parent.columnconfigure(1, weight=1)

    def _init_particles(self) -> None:
        width = max(self.particle_canvas.winfo_width(), 760)
        height = 74
        for _ in range(PARTICLE_COUNT):
            self._particles.append([
                random.uniform(0, width), random.uniform(4, height - 4),
                random.uniform(-0.65, 0.65), random.uniform(-0.35, 0.35),
                random.uniform(1.3, 2.5), random.uniform(0, math.tau),
            ])
        for _ in itertools.combinations(range(PARTICLE_COUNT), 2):
            line_id = self.particle_canvas.create_line(0, 0, 0, 0, state="hidden", width=1)
            self._particle_lines.append((line_id, _[0], _[1]))
        for particle in self._particles:
            radius = particle[4]
            item = self.particle_canvas.create_oval(0, 0, 0, 0, outline="", fill="#4f83e5")
            self._particle_items.append(item)
        self._apply_particle_colors()

    def _resize_particles(self, event: tk.Event) -> None:
        width = max(int(event.width), 1)
        height = max(int(event.height), 1)
        for particle in self._particles:
            particle[0] = min(max(particle[0], 0), width)
            particle[1] = min(max(particle[1], 0), height)

    def _apply_particle_colors(self) -> None:
        if not hasattr(self, "particle_canvas"):
            return
        if self.dark:
            background, dot, line = "#182337", "#78aaff", "#344967"
        else:
            background, dot, line = "#eaf1ff", "#3b73d9", "#c2d5f5"
        self.particle_canvas.configure(background=background)
        for item, _particle in zip(self._particle_items, self._particles):
            self.particle_canvas.itemconfigure(item, fill=dot)
        for line_id, _left, _right in self._particle_lines:
            self.particle_canvas.itemconfigure(line_id, fill=line)

    def _animate_particles(self) -> None:
        if not self.winfo_exists():
            return
        # Do no animation work while minimized/hidden; resume automatically.
        try:
            visible = self.state() != "iconic" and self.particle_canvas.winfo_ismapped()
        except tk.TclError:
            return
        if visible:
            width = max(self.particle_canvas.winfo_width(), 1)
            height = max(self.particle_canvas.winfo_height(), 1)
            for index, particle in enumerate(self._particles):
                x, y, vx, vy, radius, phase = particle
                x += vx
                y += vy
                if x < 1 or x > width - 1:
                    vx = -vx
                    x = min(max(x, 1), width - 1)
                if y < 1 or y > height - 1:
                    vy = -vy
                    y = min(max(y, 1), height - 1)
                phase += 0.055
                particle[:] = [x, y, vx, vy, radius, phase]
                pulse = radius + 0.35 * (0.5 + 0.5 * math.sin(phase))
                self.particle_canvas.coords(self._particle_items[index], x - pulse, y - pulse, x + pulse, y + pulse)
            max_distance_sq = 132 * 132
            for line_id, left, right in self._particle_lines:
                x1, y1 = self._particles[left][0], self._particles[left][1]
                x2, y2 = self._particles[right][0], self._particles[right][1]
                if (x2 - x1) ** 2 + (y2 - y1) ** 2 < max_distance_sq:
                    self.particle_canvas.coords(line_id, x1, y1, x2, y2)
                    self.particle_canvas.itemconfigure(line_id, state="normal")
                else:
                    self.particle_canvas.itemconfigure(line_id, state="hidden")
        self._particle_job = self.after(PARTICLE_TICK_MS, self._animate_particles)

    def _schedule_output_update(self, *_args) -> None:
        job = getattr(self, "_output_after_id", None)
        if job:
            self.after_cancel(job)
        self._output_after_id = self.after(120, self._update_output)

    def _toggle_theme(self) -> None:
        self.dark = not self.dark
        self._apply_theme()

    def _apply_theme(self) -> None:
        colors = ({"bg": "#111827", "card": "#1f2937", "text": "#f3f4f6", "muted": "#aab6c5", "accent": "#60a5fa", "field": "#273449", "log": "#0b1220", "log_text": "#d8e2f0", "border": "#374151"} if self.dark else {"bg": "#f3f6fb", "card": "#ffffff", "text": "#172033", "muted": "#64748b", "accent": "#2563eb", "field": "#ffffff", "log": "#111827", "log_text": "#e5edf7", "border": "#dbe3ee"})
        self.configure(background=colors["bg"])
        style = ttk.Style(self)
        style.configure(".", background=colors["bg"], foreground=colors["text"])
        style.configure("TFrame", background=colors["bg"])
        style.configure("TLabel", background=colors["bg"], foreground=colors["text"])
        style.configure("Muted.TLabel", foreground=colors["muted"])
        style.configure("TLabelframe", background=colors["card"], foreground=colors["text"], bordercolor=colors["border"])
        style.configure("TLabelframe.Label", background=colors["card"], foreground=colors["text"])
        style.configure("TEntry", fieldbackground=colors["field"], foreground=colors["text"], insertcolor=colors["text"])
        style.configure("TCombobox", fieldbackground=colors["field"], foreground=colors["text"], background=colors["card"])
        style.map("TCombobox", fieldbackground=[("readonly", colors["field"])], foreground=[("readonly", colors["text"])])
        style.configure("TCheckbutton", background=colors["card"], foreground=colors["text"])
        style.configure("TNotebook", background=colors["bg"])
        style.configure("TNotebook.Tab", background=colors["card"], foreground=colors["text"], padding=(14, 8))
        style.map("TNotebook.Tab", background=[("selected", colors["accent"])], foreground=[("selected", "#ffffff")])
        style.configure("TButton", background=colors["card"], foreground=colors["text"], bordercolor=colors["border"])
        style.map("TButton", background=[("active", colors["border"])])
        style.configure("Primary.TButton", background=colors["accent"], foreground="#ffffff")
        style.configure("TProgressbar", background=colors["accent"], troughcolor=colors["card"])
        self.log.configure(background=colors["log"], foreground=colors["log_text"], insertbackground=colors["log_text"])
        self.theme_button.configure(text="☀ 浅色模式" if self.dark else "☾ 深色模式")
        self._apply_particle_colors()

    def _choose_project(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.project_var.get() or str(Path.cwd()))
        if not selected:
            return
        self._project_generation += 1
        generation = self._project_generation
        project = Path(selected)
        self.project_var.set(selected)
        self.name_var.set(project.name)
        self.entry_var.set("")
        self.status_var.set("扫描项目入口…")
        self._update_output()
        threading.Thread(target=self._discover_entry, args=(project, generation), daemon=True).start()

    def _discover_entry(self, project: Path, generation: int) -> None:
        try:
            from packager import discover_entry
            entry = str(discover_entry(project))
            self.events.put(("entry", f"{generation}\t{entry}"))
        except ValueError:
            self.events.put(("entry", f"{generation}\t"))
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
            initial = current if self.mode_var.get() == "目录" else current.parent
            selected = filedialog.askdirectory(initialdir=str(initial), title="选择程序输出目录")
            if selected and self.mode_var.get() == "单文件":
                selected = str(Path(selected) / current.name)
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
        settings = {"project": project, "name": name, "output": output}
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
            settings.update(kind="exe", entry=entry, icon=icon, mode="onefile" if self.mode_var.get() == "单文件" else "onedir", windowed=self.windowed_var.get(), clean=self.clean_var.get(), install=self.install_var.get())
        else:
            fmt = self.format_var.get()
            if not output.name.lower().endswith(ARCHIVE_EXTENSIONS[fmt]):
                raise ValueError(f"输出文件扩展名必须是 {ARCHIVE_EXTENSIONS[fmt]}")
            settings.update(kind="archive", format=fmt)
        return settings

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
        batch: list[str] = []
        terminal: tuple[str, str] | None = None
        for _ in range(250):
            try:
                kind, text = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                batch.append(text)
            elif kind == "entry":
                generation_text, entry = text.split("\t", 1)
                if int(generation_text) == self._project_generation:
                    self.entry_var.set(entry)
                    self.status_var.set("就绪")
            else:
                terminal = (kind, text)
        if batch:
            self._append_logs(batch)
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
        self.after(120, self._poll_events)

    def _append_logs(self, lines: list[str]) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", "\n".join(lines) + "\n")
        count = int(self.log.index("end-1c").split(".", 1)[0])
        if count > MAX_LOG_LINES:
            self.log.delete("1.0", f"{count - MAX_LOG_LINES}.0")
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

    def _on_close(self) -> None:
        if self._particle_job is not None:
            try:
                self.after_cancel(self._particle_job)
            except tk.TclError:
                pass
        self.destroy()


def main() -> None:
    PackagerApp().mainloop()


if __name__ == "__main__":
    main()
