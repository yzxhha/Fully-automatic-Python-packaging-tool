# Fully automatic Python packaging tool V3.0

V3.0 adds startup launchers that detect Python and can guide/attempt to install a compatible runtime before opening the graphical interface. The application can package Python projects as a platform executable or create ZIP/TAR archives from projects containing many file types.

## Start without an existing Python installation

- **Windows:** double-click `start.bat`. If Python 3.10+ is missing, the launcher offers to install Python 3.12 for the current user using Windows Package Manager (`winget`). Installations require explicit confirmation. If `winget` is unavailable, install Python from [python.org](https://www.python.org/downloads/windows/) and retry.
- **macOS/Linux:** run `bash start.sh`. The launcher detects Python 3.10+ and Tkinter. With confirmation, it uses Homebrew on macOS or a supported Linux package manager (apt, dnf, zypper, pacman). Linux package managers may request administrator approval. Unsupported systems require manual installation.

The bootstrap scripts are shell/PowerShell files so they can run before Python is present. They do not silently install software. The GUI requires Tkinter; if the selected Python distribution does not provide it, the launcher explains what is missing.

> Review installation prompts and package-manager output before approving. Package availability and install permissions depend on your operating system and configured package sources.

## GUI features

Start the tool with `start.bat` / `start.sh`, or, if Python 3.10+ is already installed, run:

```bash
python gui.py
```

- **Executable:** package a `.py` entry point as a one-file or one-directory application using PyInstaller. GUI mode can hide the console.
- **Archives:** create ZIP, TAR.GZ, TAR.BZ2, or TAR.XZ project archives. Archives preserve relative paths and omit common VCS directories, virtual environments, build output, caches, and bytecode.
- Choose the project, entry point, icon, output format, and output location in the UI.

For executable output, install PyInstaller with `python -m pip install pyinstaller`, or select the GUI option to let the tool install it. EXE files must be built on Windows; build separately on each target operating system.

## Command-line packaging

The V1 command-line interface remains available:

```bash
python -m pip install pyinstaller
python packager.py --project ./my_app --entry main.py --name MyApp --mode onefile
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Security and platform notes

- Only package projects you trust. PyInstaller analyzes and imports project code during builds.
- Archives include project files; inspect for credentials/secrets before sharing.
- Python installers come from the configured OS package manager (Windows uses the `Python.Python.3.12` winget package). This project does not bundle an interpreter or bypass OS security/permission prompts.
