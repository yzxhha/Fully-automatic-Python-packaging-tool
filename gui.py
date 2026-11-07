"""Dark, responsive Tkinter UI with an animated particle welcome page."""
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

APP_VERSION = "6.1.0"
EXE_FORMAT = "可执行程序（当前平台）"
ARCHIVE_EXTENSIONS = {
    "ZIP (.zip)": ".zip",
    "TAR.GZ (.tar.gz)": ".tar.gz",
    "TAR.BZ2 (.tar.bz2)": ".tar.bz2",
    "TAR.XZ (.tar.xz)": ".tar.xz",
}
BG = "#080b12"
SURFACE = "#111827"
FIELD = "#0c1220"
TEXT = "#f3f6fc"
MUTED = "#91a0b7"
ACCENT = "#60a5fa"
BORDER = "#263247"
PARTICLE_COUNT = 24
PARTICLE_TICK_MS = 40
MAX_LOG_LINES = 2500


class PackagerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"自动打包工作台 · V{APP_VERSION}")
        self.geometry("980x780")
        self.minsize(760, 640)
        self.configure(background=BG)
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.busy = False
        self._closed = False
        self._particle_job: str | None = None
        self._particles: list[list[float]] = []
        self._particle_items: list[int] = []
        self._particle_lines: list[tuple[int, int, int]] = []
        self._project_generation = 0
        self._output_job: str | None = None

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
        self.after(100, self._poll_events)
        self._particle_job = self.after(PARTICLE_TICK_MS, self._animate_particles)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=BG, foreground=TEXT, font=("TkDefaultFont", 10))
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED)
        style.configure("Hero.TLabel", background=BG, foreground=TEXT, font=("TkDefaultFont", 25, "bold"))
        style.configure("TLabelframe", background=SURFACE, foreground=TEXT, bordercolor=BORDER, padding=12)
        style.configure("TLabelframe.Label", background=SURFACE, foreground=TEXT, font=("TkDefaultFont", 10, "bold"))
        style.configure("TEntry", fieldbackground=FIELD, foreground=TEXT, insertcolor=TEXT, padding=7)
        style.configure("TCombobox", fieldbackground=FIELD, foreground=TEXT, background=SURFACE, padding=6)
        style.map("TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", TEXT)])
        style.configure("TCheckbutton", background=SURFACE, foreground=TEXT)
        style.map("TCheckbutton", background=[("active", SURFACE)])
        style.configure("TButton", background=SURFACE, foreground=TEXT, bordercolor=BORDER, padding=(10, 7))
        style.map("TButton", background=[("active", BORDER)])
        style.configure("Primary.TButton", background="#2563eb", foreground="#ffffff", padding=(18, 11), font=("TkDefaultFont", 10, "bold"))
        style.map("Primary.TButton", background=[("active", "#3b82f6")])
        style.configure("TNotebook", background=BG, bordercolor=BORDER)
        style.configure("TNotebook.Tab", background=SURFACE, foreground=TEXT, padding=(16, 9))
        style.map("TNotebook.Tab", background=[("selected", "#1d4ed8")], foreground=[("selected", "#ffffff")])
        style.configure("TProgressbar", background=ACCENT, troughcolor=SURFACE)

    def _build_ui(self) -> None:
        shell = ttk.Frame(self, padding=(22, 16))
        shell.pack(fill="both", expand=True)
        top = ttk.Frame(shell)
        top.pack(fill="x", pady=(0, 12))
        ttk.Label(top, text="AUTO PACKAGER", font=("TkDefaultFont", 11, "bold"), foreground=ACCENT).pack(side="left")
        ttk.Label(top, text=f"VERSION {APP_VERSION}", style="Muted.TLabel").pack(side="right")

        self.tabs = ttk.Notebook(shell)
        self.tabs.pack(fill="both", expand=True)
        self.home_tab = ttk.Frame(self.tabs, padding=14)
        self.settings_tab = ttk.Frame(self.tabs, padding=16)
        self.logs_tab = ttk.Frame(self.tabs, padding=14)
        self.tabs.add(self.home_tab, text="  首页  ")
        self.tabs.add(self.settings_tab, text="  打包设置  ")
        self.tabs.add(self.logs_tab, text="  构建日志  ")
        self._build_home()
        self._build_settings()
        self._build_logs()

    def _build_home(self) -> None:
        self.hero = tk.Canvas(self.home_tab, background=BG, highlightthickness=0, bd=0, height=430)
        self.hero.pack(fill="both", expand=True)
        self.hero.bind("<Configure>", self._resize_particles)
        self._init_particles()
        self.hero_title = self.hero.create_text(0, 0, text="从灵感，到构建", fill=TEXT, font=("TkDefaultFont", 29, "bold"))
        self.hero_subtitle = self.hero.create_text(0, 0, text="一键打包 Python 项目 · 生成可执行程序或多格式归档", fill=MUTED, font=("TkDefaultFont", 11))
        self.hero_badge = self.hero.create_text(0, 0, text="FAST  ·  SIMPLE  ·  LOCAL", fill=ACCENT, font=("TkDefaultFont", 9, "bold"))
        self.enter_button = ttk.Button(self.home_tab, text="进入打包工作台  →", style="Primary.TButton", command=lambda: self.tabs.select(self.settings_tab))
        self.hero_button = self.hero.create_window(0, 0, window=self.enter_button)
        self.hero.bind("<Configure>", self._position_hero, add="+")
        ttk.Label(self.home_tab, text="本地构建 · 支持 EXE / ZIP / TAR.GZ / TAR.BZ2 / TAR.XZ", style="Muted.TLabel").pack(pady=(10, 2))

    def _build_settings(self) -> None:
        project = ttk.LabelFrame(self.settings_tab, text="  项目与文件  ", padding=12)
        project.pack(fill="x", pady=(0, 10))
        self._path_row(project, 0, "项目目录", self.project_var, self._choose_project, "浏览…")
        self._path_row(project, 1, "入口文件", self.entry_var, self._choose_entry, "选择 .py")
        self._path_row(project, 2, "图标文件", self.icon_var, self._choose_icon, "选择图标")
        ttk.Label(project, text="应用名称", width=12).grid(row=3, column=0, sticky="w", pady=5)
        ttk.Entry(project, textvariable=self.name_var).grid(row=3, column=1, columnspan=2, sticky="ew", padx=6, pady=5)
        project.columnconfigure(1, weight=1)

        output = ttk.LabelFrame(self.settings_tab, text="  输出格式与位置  ", padding=12)
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

        options = ttk.LabelFrame(self.settings_tab, text="  构建选项  ", padding=12)
        options.pack(fill="x", pady=(0, 10))
        self.windowed_check = ttk.Checkbutton(options, text="GUI 应用（隐藏控制台）", variable=self.windowed_var)
        self.windowed_check.grid(row=0, column=0, sticky="w", padx=(0, 16), pady=4)
        ttk.Checkbutton(options, text="清理构建缓存", variable=self.clean_var).grid(row=0, column=1, sticky="w", pady=4)
        self.install_check = ttk.Checkbutton(options, text="缺少 PyInstaller 时尝试 pip 安装（需要网络）", variable=self.install_var)
        self.install_check.grid(row=1, column=0, columnspan=2, sticky="w", pady=4)

        actions = ttk.Frame(self.settings_tab)
        actions.pack(fill="x", pady=2)
        self.build_button = ttk.Button(actions, text="▶  开始打包", style="Primary.TButton", command=self._start_build)
        self.build_button.pack(side="left")
        ttk.Button(actions, text="打开输出目录", command=self._open_output).pack(side="left", padx=8)
        ttk.Button(actions, text="查看日志", command=lambda: self.tabs.select(self.logs_tab)).pack(side="left")
        ttk.Label(actions, textvariable=self.status_var, style="Muted.TLabel").pack(side="right")
        self.progress = ttk.Progressbar(self.settings_tab, mode="indeterminate")
        self.progress.pack(fill="x", pady=(10, 0))

    def _build_logs(self) -> None:
        header = ttk.Frame(self.logs_tab)
        header.pack(fill="x", pady=(0, 7))
        ttk.Label(header, text="构建输出", font=("TkDefaultFont", 11, "bold")).pack(side="left")
        ttk.Button(header, text="清空日志", command=self._clear_log).pack(side="right")
        self.log = tk.Text(self.logs_tab, wrap="word", state="disabled", relief="flat", padx=10, pady=9, background="#05070c", foreground="#d7e3f4", insertbackground=TEXT)
        scrollbar = ttk.Scrollbar(self.logs_tab, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._log("欢迎使用自动打包工作台。")

    @staticmethod
    def _path_row(parent: ttk.Frame, row: int, label: str, variable: tk.StringVar, command, button_text: str) -> None:
        ttk.Label(parent, text=label, width=12).grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=6, pady=5)
        ttk.Button(parent, text=button_text, command=command).grid(row=row, column=2, padx=(2, 0), pady=5)
        parent.columnconfigure(1, weight=1)

    def _init_particles(self) -> None:
        # Create canvas objects once: frames only move/update a small fixed set.
        for _ in range(PARTICLE_COUNT):
            self._particles.append([
                random.uniform(0, 900), random.uniform(0, 420),
                random.uniform(-0.55, 0.55), random.uniform(-0.32, 0.32),
                random.uniform(1.0, 2.4), random.uniform(0, math.tau),
            ])
        for left, right in itertools.combinations(range(PARTICLE_COUNT), 2):
            item = self.hero.create_line(0, 0, 0, 0, fill="#172742", width=1, state="hidden")
            self._particle_lines.append((item, left, right))
        for particle in self._particles:
            item = self.hero.create_oval(0, 0, 0, 0, outline="", fill="#4c8dff")
            self._particle_items.append(item)

    def _position_hero(self, event: tk.Event) -> None:
        center_x = max(1, event.width // 2)
        center_y = max(1, event.height // 2)
        self.hero.coords(self.hero_badge, center_x, center_y - 67)
        self.hero.coords(self.hero_title, center_x, center_y - 25)
        self.hero.coords(self.hero_subtitle, center_x, center_y + 20)
        self.hero.coords(self.hero_button, center_x, center_y + 83)

    def _resize_particles(self, event: tk.Event) -> None:
        width, height = max(1, event.width), max(1, event.height)
        for particle in self._particles:
            particle[0] = min(max(particle[0], 1), width - 1)
            particle[1] = min(max(particle[1], 1), height - 1)
        self._position_hero(event)

    def _animate_particles(self) -> None:
        if self._closed:
            return
        try:
            if self.state() != "iconic" and self.hero.winfo_ismapped():
                width, height = max(1, self.hero.winfo_width()), max(1, self.hero.winfo_height())
                for index, particle in enumerate(self._particles):
                    x, y, vx, vy, radius, phase = particle
                    x += vx
                    y += vy
                    if x < 1 or x > width - 1:
                        vx, x = -vx, min(max(x, 1), width - 1)
                    if y < 1 or y > height - 1:
                        vy, y = -vy, min(max(y, 1), height - 1)
                    phase += 0.055
                    particle[:] = [x, y, vx, vy, radius, phase]
                    pulse = radius + 0.3 * (0.5 + 0.5 * math.sin(phase))
                    self.hero.coords(self._particle_items[index], x - pulse, y - pulse, x + pulse, y + pulse)
                max_distance_sq = 145 * 145
                for item, left, right in self._particle_lines:
                    x1, y1 = self._particles[left][0], self._particles[left][1]
                    x2, y2 = self._particles[right][0], self._particles[right][1]
                    if (x2 - x1) ** 2 + (y2 - y1) ** 2 < max_distance_sq:
                        self.hero.coords(item, x1, y1, x2, y2)
                        self.hero.itemconfigure(item, state="normal")
                    else:
                        self.hero.itemconfigure(item, state="hidden")
            self._particle_job = self.after(PARTICLE_TICK_MS, self._animate_particles)
        except tk.TclError:
            self._particle_job = None

    def _schedule_output_update(self, *_args) -> None:
        if self._output_job:
            self.after_cancel(self._output_job)
        self._output_job = self.after(120, self._update_output)

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
        self._output_job = None
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
            extension = self._extension()
            selected = filedialog.asksaveasfilename(initialdir=str(current.parent), initialfile=current.name, defaultextension=extension, filetypes=[(self.format_var.get(), "*" + extension), ("所有文件", "*.*")])
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
        logs: list[str] = []
        terminal: tuple[str, str] | None = None
        for _ in range(250):
            try:
                kind, text = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                logs.append(text)
            elif kind == "entry":
                generation_text, entry = text.split("\t", 1)
                if int(generation_text) == self._project_generation:
                    self.entry_var.set(entry)
                    self.status_var.set("就绪")
            else:
                terminal = (kind, text)
        if logs:
            self._append_logs(logs)
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
        if not self._closed:
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
        self._closed = True
        for job in (self._particle_job, self._output_job):
            if job:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
        self.destroy()


def main() -> None:
    PackagerApp().mainloop()


if __name__ == "__main__":
    main()
