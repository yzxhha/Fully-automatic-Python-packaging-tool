"""Dark, responsive Tkinter UI with a lightweight animated welcome page."""
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

VERSION = "6.1.0"
EXE_FORMAT = "可执行程序（当前平台）"
ARCHIVE_EXTENSIONS = {
    "ZIP (.zip)": ".zip",
    "TAR.GZ (.tar.gz)": ".tar.gz",
    "TAR.BZ2 (.tar.bz2)": ".tar.bz2",
    "TAR.XZ (.tar.xz)": ".tar.xz",
}
BG, SURFACE, FIELD = "#080b12", "#111827", "#0c1220"
TEXT, MUTED, ACCENT, BORDER = "#f3f6fc", "#91a0b7", "#60a5fa", "#263247"
PARTICLE_COUNT, FRAME_MS, MAX_LOG_LINES = 22, 50, 2500


class PackagerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"自动打包工作台 · V{VERSION}")
        self.geometry("960x760")
        self.minsize(740, 620)
        self.configure(background=BG)
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.busy = False
        self.closed = False
        self.project_generation = 0
        self.particle_job: str | None = None
        self.output_job: str | None = None
        self.particles: list[list[float]] = []
        self.dots: list[int] = []
        self.links: list[tuple[int, int, int]] = []

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
        self.after(120, self._poll_events)
        self.particle_job = self.after(FRAME_MS, self._animate)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _setup_style(self) -> None:
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure(".", background=BG, foreground=TEXT, font=("TkDefaultFont", 10))
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=TEXT)
        s.configure("Muted.TLabel", background=BG, foreground=MUTED)
        s.configure("Hero.TLabel", background=BG, foreground=TEXT, font=("TkDefaultFont", 27, "bold"))
        s.configure("TLabelframe", background=SURFACE, foreground=TEXT, bordercolor=BORDER, padding=12)
        s.configure("TLabelframe.Label", background=SURFACE, foreground=TEXT, font=("TkDefaultFont", 10, "bold"))
        s.configure("TEntry", fieldbackground=FIELD, foreground=TEXT, insertcolor=TEXT, padding=7)
        s.configure("TCombobox", fieldbackground=FIELD, foreground=TEXT, background=SURFACE, padding=6)
        s.map("TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", TEXT)])
        s.configure("TCheckbutton", background=SURFACE, foreground=TEXT)
        s.configure("TButton", background=SURFACE, foreground=TEXT, bordercolor=BORDER, padding=(10, 7))
        s.map("TButton", background=[("active", BORDER)])
        s.configure("Primary.TButton", background="#2563eb", foreground="#ffffff", padding=(18, 11), font=("TkDefaultFont", 10, "bold"))
        s.map("Primary.TButton", background=[("active", "#3b82f6")])
        s.configure("TNotebook", background=BG, bordercolor=BORDER)
        s.configure("TNotebook.Tab", background=SURFACE, foreground=TEXT, padding=(15, 9))
        s.map("TNotebook.Tab", background=[("selected", "#1d4ed8")], foreground=[("selected", "#ffffff")])
        s.configure("TProgressbar", background=ACCENT, troughcolor=SURFACE)

    def _build_ui(self) -> None:
        shell = ttk.Frame(self, padding=(20, 14))
        shell.pack(fill="both", expand=True)
        bar = ttk.Frame(shell)
        bar.pack(fill="x", pady=(0, 10))
        ttk.Label(bar, text="AUTO PACKAGER", foreground=ACCENT, font=("TkDefaultFont", 11, "bold")).pack(side="left")
        ttk.Label(bar, text=f"VERSION {VERSION}", style="Muted.TLabel").pack(side="right")
        self.tabs = ttk.Notebook(shell)
        self.tabs.pack(fill="both", expand=True)
        self.home = ttk.Frame(self.tabs, padding=14)
        self.settings = ttk.Frame(self.tabs, padding=15)
        self.logs = ttk.Frame(self.tabs, padding=13)
        self.tabs.add(self.home, text="  首页  ")
        self.tabs.add(self.settings, text="  打包设置  ")
        self.tabs.add(self.logs, text="  构建日志  ")
        self._build_home()
        self._build_settings()
        self._build_logs()

    def _build_home(self) -> None:
        self.canvas = tk.Canvas(self.home, height=440, bg=BG, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._resize_particles)
        self._make_particles()
        self.badge = self.canvas.create_text(0, 0, text="FAST  ·  SIMPLE  ·  LOCAL", fill=ACCENT, font=("TkDefaultFont", 9, "bold"))
        self.hero_title = self.canvas.create_text(0, 0, text="从灵感，到构建", fill=TEXT, font=("TkDefaultFont", 28, "bold"))
        self.hero_sub = self.canvas.create_text(0, 0, text="一键打包 Python 项目 · 可执行程序与多格式归档", fill=MUTED, font=("TkDefaultFont", 11))
        self.enter = ttk.Button(self.home, text="进入打包工作台  →", style="Primary.TButton", command=lambda: self.tabs.select(self.settings))
        self.enter_item = self.canvas.create_window(0, 0, window=self.enter)
        self._place_hero(self.canvas.winfo_width(), self.canvas.winfo_height())
        ttk.Label(self.home, text="本地构建 · 支持 EXE / ZIP / TAR.GZ / TAR.BZ2 / TAR.XZ", style="Muted.TLabel").pack(pady=(8, 0))

    def _make_particles(self) -> None:
        for _ in range(PARTICLE_COUNT):
            self.particles.append([random.uniform(0, 900), random.uniform(0, 420), random.uniform(-.45, .45), random.uniform(-.3, .3), random.uniform(1, 2.2), random.uniform(0, math.tau)])
        for a, b in itertools.combinations(range(PARTICLE_COUNT), 2):
            line = self.canvas.create_line(0, 0, 0, 0, fill="#172742", width=1, state="hidden")
            self.links.append((line, a, b))
        for _ in self.particles:
            self.dots.append(self.canvas.create_oval(0, 0, 0, 0, outline="", fill="#4c8dff"))

    def _place_hero(self, width: int, height: int) -> None:
        x, y = max(width, 1) / 2, max(height, 1) / 2
        for item, dy in ((self.badge, -72), (self.hero_title, -30), (self.hero_sub, 18), (self.enter_item, 82)):
            self.canvas.coords(item, x, y + dy)

    def _resize_particles(self, event: tk.Event) -> None:
        for p in self.particles:
            p[0] = min(max(p[0], 1), max(event.width - 1, 1))
            p[1] = min(max(p[1], 1), max(event.height - 1, 1))
        self._place_hero(event.width, event.height)

    def _animate(self) -> None:
        if self.closed:
            return
        try:
            if self.state() != "iconic" and self.canvas.winfo_ismapped():
                w, h = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
                for i, p in enumerate(self.particles):
                    x, y, vx, vy, r, phase = p
                    x += vx; y += vy
                    if x < 1 or x > w - 1: vx, x = -vx, min(max(x, 1), w - 1)
                    if y < 1 or y > h - 1: vy, y = -vy, min(max(y, 1), h - 1)
                    phase += .05
                    p[:] = [x, y, vx, vy, r, phase]
                    radius = r + .25 * (0.5 + .5 * math.sin(phase))
                    self.canvas.coords(self.dots[i], x-radius, y-radius, x+radius, y+radius)
                for item, a, b in self.links:
                    x1, y1 = self.particles[a][0:2]; x2, y2 = self.particles[b][0:2]
                    if (x2-x1)**2 + (y2-y1)**2 < 145**2:
                        self.canvas.coords(item, x1, y1, x2, y2)
                        self.canvas.itemconfigure(item, state="normal")
                    else:
                        self.canvas.itemconfigure(item, state="hidden")
            self.particle_job = self.after(FRAME_MS, self._animate)
        except tk.TclError:
            self.particle_job = None

    def _build_settings(self) -> None:
        project = ttk.LabelFrame(self.settings, text="  项目与文件  ", padding=12)
        project.pack(fill="x", pady=(0, 10))
        self._path_row(project, 0, "项目目录", self.project_var, self._choose_project, "浏览…")
        self._path_row(project, 1, "入口文件", self.entry_var, self._choose_entry, "选择 .py")
        self._path_row(project, 2, "图标文件", self.icon_var, self._choose_icon, "选择图标")
        ttk.Label(project, text="应用名称", width=12).grid(row=3, column=0, sticky="w", pady=5)
        ttk.Entry(project, textvariable=self.name_var).grid(row=3, column=1, columnspan=2, sticky="ew", padx=6, pady=5)
        project.columnconfigure(1, weight=1)
        output = ttk.LabelFrame(self.settings, text="  输出格式与位置  ", padding=12)
        output.pack(fill="x", pady=(0, 10))
        ttk.Label(output, text="输出格式", width=12).grid(row=0, column=0, sticky="w", pady=5)
        self.format_box = ttk.Combobox(output, textvariable=self.format_var, state="readonly", values=(EXE_FORMAT, *ARCHIVE_EXTENSIONS), width=27)
        self.format_box.grid(row=0, column=1, sticky="ew", padx=6, pady=5)
        self.format_box.bind("<<ComboboxSelected>>", lambda _e: self._update_output())
        ttk.Label(output, text="模式").grid(row=0, column=2, sticky="w", padx=(12, 4), pady=5)
        self.mode_box = ttk.Combobox(output, textvariable=self.mode_var, state="readonly", values=("单文件", "目录"), width=11)
        self.mode_box.grid(row=0, column=3, sticky="ew", padx=6, pady=5)
        self.mode_box.bind("<<ComboboxSelected>>", lambda _e: self._update_output())
        self._path_row(output, 1, "输出位置", self.output_var, self._choose_output, "浏览…")
        output.columnconfigure(1, weight=1)
        options = ttk.LabelFrame(self.settings, text="  构建选项  ", padding=12)
        options.pack(fill="x", pady=(0, 10))
        self.windowed = ttk.Checkbutton(options, text="GUI 应用（隐藏控制台）", variable=self.windowed_var)
        self.windowed.grid(row=0, column=0, sticky="w", padx=(0, 16), pady=4)
        ttk.Checkbutton(options, text="清理构建缓存", variable=self.clean_var).grid(row=0, column=1, sticky="w", pady=4)
        self.install = ttk.Checkbutton(options, text="缺少 PyInstaller 时尝试 pip 安装（需要网络）", variable=self.install_var)
        self.install.grid(row=1, column=0, columnspan=2, sticky="w", pady=4)
        actions = ttk.Frame(self.settings); actions.pack(fill="x", pady=2)
        self.build_button = ttk.Button(actions, text="▶  开始打包", style="Primary.TButton", command=self._start_build)
        self.build_button.pack(side="left")
        ttk.Button(actions, text="打开输出目录", command=self._open_output).pack(side="left", padx=8)
        ttk.Label(actions, textvariable=self.status_var, style="Muted.TLabel").pack(side="right")
        self.progress = ttk.Progressbar(self.settings, mode="indeterminate"); self.progress.pack(fill="x", pady=(10, 0))

    def _build_logs(self) -> None:
        head = ttk.Frame(self.logs); head.pack(fill="x", pady=(0, 7))
        ttk.Label(head, text="构建输出", font=("TkDefaultFont", 11, "bold")).pack(side="left")
        ttk.Button(head, text="清空日志", command=self._clear_log).pack(side="right")
        self.log = tk.Text(self.logs, wrap="word", state="disabled", relief="flat", padx=10, pady=9, bg="#05070c", fg="#d7e3f4", insertbackground=TEXT)
        scroll = ttk.Scrollbar(self.logs, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set); self.log.pack(side="left", fill="both", expand=True); scroll.pack(side="right", fill="y")
        self._log("欢迎使用自动打包工作台。")

    @staticmethod
    def _path_row(parent: ttk.Frame, row: int, label: str, variable: tk.StringVar, command, button_text: str) -> None:
        ttk.Label(parent, text=label, width=12).grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=6, pady=5)
        ttk.Button(parent, text=button_text, command=command).grid(row=row, column=2, padx=(2, 0), pady=5)
        parent.columnconfigure(1, weight=1)

    def _schedule_output_update(self, *_args) -> None:
        if self.output_job:
            self.after_cancel(self.output_job)
        self.output_job = self.after(120, self._update_output)

    def _choose_project(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.project_var.get() or str(Path.cwd()))
        if not selected: return
        self.project_generation += 1
        generation = self.project_generation
        project = Path(selected)
        self.project_var.set(selected); self.name_var.set(project.name); self.entry_var.set("")
        self.status_var.set("扫描项目入口…"); self._update_output()
        threading.Thread(target=self._discover_entry, args=(project, generation), daemon=True).start()

    def _discover_entry(self, project: Path, generation: int) -> None:
        try:
            from packager import discover_entry
            value = str(discover_entry(project))
        except ValueError:
            value = ""
        except Exception as exc:
            self.events.put(("error", str(exc))); return
        self.events.put(("entry", f"{generation}\t{value}"))

    def _choose_entry(self) -> None:
        value = filedialog.askopenfilename(initialdir=self.project_var.get(), filetypes=[("Python 文件", "*.py"), ("所有文件", "*.*")])
        if value: self.entry_var.set(value)

    def _choose_icon(self) -> None:
        value = filedialog.askopenfilename(filetypes=[("图标文件", "*.ico *.icns *.png"), ("所有文件", "*.*")])
        if value: self.icon_var.set(value)

    def _is_executable(self) -> bool:
        return self.format_var.get() == EXE_FORMAT

    def _extension(self) -> str:
        return ARCHIVE_EXTENSIONS[self.format_var.get()]

    def _update_output(self) -> None:
        self.output_job = None
        project = Path(self.project_var.get() or ".").expanduser()
        name = self.name_var.get().strip() or project.name or "MyApp"
        if self._is_executable():
            filename = name + (".exe" if sys.platform == "win32" else "") if self.mode_var.get() == "单文件" else name
            output = project / "dist" / filename if self.mode_var.get() == "单文件" else project / "dist"
        else:
            output = project / "dist" / (name + self._extension())
        self.output_var.set(str(output))
        enabled = self._is_executable()
        self.mode_box.configure(state="readonly" if enabled else "disabled")
        self.windowed.configure(state="normal" if enabled else "disabled")
        self.install.configure(state="normal" if enabled else "disabled")

    def _choose_output(self) -> None:
        current = Path(self.output_var.get())
        if self._is_executable():
            selected = filedialog.askdirectory(initialdir=str(current if self.mode_var.get() == "目录" else current.parent), title="选择程序输出目录")
            if selected and self.mode_var.get() == "单文件": selected = str(Path(selected) / current.name)
        else:
            ext = self._extension()
            selected = filedialog.asksaveasfilename(initialdir=str(current.parent), initialfile=current.name, defaultextension=ext, filetypes=[(self.format_var.get(), "*" + ext), ("所有文件", "*.*")])
        if selected: self.output_var.set(selected)

    def _settings_snapshot(self) -> dict:
        project = Path(self.project_var.get()).expanduser().resolve()
        if not project.is_dir(): raise ValueError(f"项目目录不存在：{project}")
        name = self.name_var.get().strip() or project.name
        if not name or Path(name).name != name or name in {".", ".."}: raise ValueError("应用名称需为有效文件名，不能包含目录路径。")
        output = Path(self.output_var.get()).expanduser().resolve()
        result = {"project": project, "name": name, "output": output}
        if self._is_executable():
            from packager import discover_entry
            entry = Path(self.entry_var.get()).expanduser() if self.entry_var.get().strip() else discover_entry(project)
            if not entry.is_absolute(): entry = project / entry
            entry = entry.resolve()
            if not entry.is_file() or entry.suffix.lower() != ".py": raise ValueError("请选择存在的 Python 入口文件。")
            try: entry.relative_to(project)
            except ValueError as exc: raise ValueError("入口文件必须位于项目目录内。") from exc
            icon = Path(self.icon_var.get()).expanduser().resolve() if self.icon_var.get().strip() else None
            if icon and not icon.is_file(): raise ValueError(f"图标文件不存在：{icon}")
            result.update(kind="exe", entry=entry, icon=icon, mode="onefile" if self.mode_var.get() == "单文件" else "onedir", windowed=self.windowed_var.get(), clean=self.clean_var.get(), install=self.install_var.get())
        else:
            fmt = self.format_var.get()
            if not output.name.lower().endswith(ARCHIVE_EXTENSIONS[fmt]): raise ValueError(f"输出文件扩展名必须是 {ARCHIVE_EXTENSIONS[fmt]}")
            result.update(kind="archive", format=fmt)
        return result

    def _start_build(self) -> None:
        if self.busy: return
        try: settings = self._settings_snapshot()
        except (ValueError, OSError) as exc:
            messagebox.showerror("设置有误", str(exc)); return
        self.busy = True; self.build_button.configure(state="disabled"); self.status_var.set("正在打包…"); self.progress.start(12); self.tabs.select(self.logs)
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
                outdir = settings["output"].parent if settings["mode"] == "onefile" else settings["output"]
                command = build_command(entry=settings["entry"], project=settings["project"], name=settings["name"], mode=settings["mode"], output=outdir, work=work, spec=work / "spec", windowed=settings["windowed"], icon=settings["icon"], clean=settings["clean"])
                self.events.put(("log", "运行 PyInstaller：" + subprocess.list2cmdline(command)))
                with subprocess.Popen(command, cwd=settings["project"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1) as proc:
                    assert proc.stdout is not None
                    for line in proc.stdout: self.events.put(("log", line.rstrip()))
                    code = proc.wait()
                if code: raise RuntimeError(f"PyInstaller 退出，错误代码：{code}")
                self.events.put(("log", f"打包完成：{settings['output']}"))
            self.events.put(("done", "成功"))
        except Exception as exc: self.events.put(("error", str(exc)))

    def _poll_events(self) -> None:
        logs: list[str] = []; terminal = None
        for _ in range(250):
            try: kind, text = self.events.get_nowait()
            except queue.Empty: break
            if kind == "log": logs.append(text)
            elif kind == "entry":
                version, entry = text.split("\t", 1)
                if int(version) == self.project_generation: self.entry_var.set(entry); self.status_var.set("就绪")
            else: terminal = (kind, text)
        if logs: self._append_logs(logs)
        if terminal:
            kind, text = terminal; self.busy = False; self.progress.stop(); self.build_button.configure(state="normal"); self.status_var.set(text)
            if kind == "error": self._log("错误：" + text); messagebox.showerror("任务失败", text)
            else: messagebox.showinfo("打包完成", "任务已完成，请检查输出位置。")
        if not self.closed: self.after(120, self._poll_events)

    def _append_logs(self, lines: list[str]) -> None:
        self.log.configure(state="normal"); self.log.insert("end", "\n".join(lines) + "\n")
        count = int(self.log.index("end-1c").split(".", 1)[0])
        if count > MAX_LOG_LINES: self.log.delete("1.0", f"{count - MAX_LOG_LINES}.0")
        self.log.see("end"); self.log.configure(state="disabled")

    def _log(self, line: str) -> None: self._append_logs([line])

    def _clear_log(self) -> None:
        self.log.configure(state="normal"); self.log.delete("1.0", "end"); self.log.configure(state="disabled")

    def _open_output(self) -> None:
        path = Path(self.output_var.get()).expanduser()
        folder = path if self._is_executable() and self.mode_var.get() == "目录" else path.parent
        if not folder.exists(): messagebox.showinfo("输出目录", f"目录尚不存在：{folder}"); return
        try:
            if sys.platform == "win32":
                import os
                os.startfile(str(folder))
            elif sys.platform == "darwin": subprocess.Popen(["open", str(folder)])
            else: subprocess.Popen(["xdg-open", str(folder)])
        except OSError as exc: messagebox.showerror("无法打开目录", str(exc))

    def _close(self) -> None:
        self.closed = True
        for job in (self.particle_job, self.output_job):
            if job:
                try: self.after_cancel(job)
                except tk.TclError: pass
        self.destroy()


def main() -> None:
    PackagerApp().mainloop()


if __name__ == "__main__":
    main()
