# yt-dlp GUI Video Downloader

[中文版](README-cn.md)

## Overview

This project is a Windows GUI wrapper for the [yt-dlp](https://github.com/yt-dlp/yt-dlp) command-line video downloader. Users simply paste a video URL into the interface and click "Download" — no command-line knowledge required. Supports Chinese/English UI switching, and allows customizing the download directory and log directory via a settings dialog.

## Table of Contents

- [Overview](#overview)
- [Design Philosophy](#design-philosophy)
  - [Layered Architecture](#layered-architecture)
  - [Key Technical Decisions](#key-technical-decisions)
- [File Structure](#file-structure)
- [Module Details](#module-details)
  - [main.py — Entry Point](#mainpy--entry-point)
  - [gui.py — GUI Module](#guipy--gui-module)
  - [downloader.py — Download Core Module](#downloaderpy--download-core-module)
  - [logger.py — Logging Module](#loggerpy--logging-module)
  - [config.json — Config File](#configjson--config-file)
- [Usage](#usage)
  - [Requirements](#requirements)
  - [Running the Program](#running-the-program)
  - [Steps](#steps)
  - [Language Switching](#language-switching)
  - [Settings](#settings)
- [Using downloader.py as a Standalone Module](#using-downloaderpy-as-a-standalone-module)
- [Notes](#notes)

## Design Philosophy

### Layered Architecture

The program follows a **separation of UI and logic** three-layer architecture:

```
┌─────────────────────────────────────┐
│   gui.py  (UI Layer)                │  GUI interaction + Settings dialog + Multilingual
└──────────┬──────────────────────────┘
           │ calls
┌──────────▼──────────────────────────┐
│   downloader.py (Core Layer)        │  Fully independent, no GUI dependencies
│   logger.py    (Logging Layer)      │  Fully independent, no GUI dependencies
└──────────┬──────────────────────────┘
           │ calls
┌──────────▼──────────────────────────┐
│   core/yt-dlp.exe                   │  External CLI tool
└─────────────────────────────────────┘
```

**Core Design Principles**:
- `downloader.py` does not depend on any GUI library (tkinter/PyQt etc.) and can be directly `import`ed by any Python program as a standalone module
- `logger.py` is equally independent, with no GUI library dependencies
- User configuration is persisted via `config.json`, loaded automatically on startup
- Multilingual support is implemented through a `TRANSLATIONS` dictionary; switching languages instantly refreshes all UI text

### Key Technical Decisions

| Decision | Approach | Rationale |
|----------|----------|-----------|
| GUI library | tkinter | Built into Python, zero extra dependencies |
| Download method | subprocess.Popen calling yt-dlp.exe | Directly uses the provided binary |
| Real-time progress | Popen + readline() + --newline | Parses progress percentage line by line |
| Multithreading | threading.Thread | Prevents UI freezing during download |
| Encoding handling | Auto-detect system encoding + errors='replace' | Compatible with Chinese Windows environments |
| Data transfer | dataclass (DownloadResult) | Structured return value, no third-party libs needed |
| Playlist handling | Truncate URL after "&" | Simulates CMD behavior, identical to running yt-dlp directly in CMD |
| Log ordering | New logs inserted at top of file | Most recent logs always appear first for easy viewing |
| Config persistence | config.json (JSON) | Lightweight, human-readable, supported by Python standard library |
| GUI thread safety | root.after() scheduled to main thread | All tkinter GUI operations must run on the main thread |
| Multilingual | TRANSLATIONS dict + t(key) method | Zero dependencies, instant runtime switching, covers all UI text |

## File Structure

```
ytdlpGUI/
├── main.py          # Entry point: loads config, creates main window, starts main loop
├── gui.py           # GUI module (download/settings buttons, language switch, settings dialog, progress bar)
├── downloader.py    # Download core module (standalone, no GUI dependencies)
├── logger.py        # Logging module (standalone, no GUI dependencies)
├── config.json      # User config file (download dir, log dir, UI language)
├── README.md        # English documentation
├── README-cn.md     # Chinese documentation
├── flow-en.md       # Mermaid program design flowcharts (English)
├── flow-cn.md       # Mermaid program design flowcharts (Chinese)
├── tasks-en.md      # Task checklist (English)
├── tasks-cn.md      # Task checklist (Chinese)
├── core/            # yt-dlp and companion tools
│   ├── yt-dlp.exe
│   ├── ffmpeg.exe
│   ├── ffprobe.exe
│   └── ...
├── downloads/       # Video download directory (auto-created, customizable)
└── logs/            # Log file directory (auto-created, customizable)
```

## Module Details

### main.py — Entry Point
- Loads `config.json` (uses defaults if file does not exist)
- Creates the tkinter main window
- Creates an `App` instance (passing in the config dict)
- Starts the tkinter main event loop

### gui.py — GUI Module
- `App` class: manages the main window and user interaction
- Contains: URL input field, "Download" button, "Settings" button, language selector dropdown, progress bar, status label
- Input field supports a right-click context menu (Paste, Copy, Clear)
- Downloads run in a background thread so the UI remains responsive
- Progress bar shows real-time download percentage (determinate mode) or a processing animation (indeterminate mode)
- Success/failure dialog shown after download completes
- Settings dialog supports customizing download and log directories, saved to config.json
- Multilingual support: switch between Chinese and English via dropdown; all UI text updates instantly

### downloader.py — Download Core Module
- `VideoDownloader` class: encapsulates yt-dlp invocation logic
- `DownloadResult` dataclass: structured download result
- Supports custom yt-dlp path, ffmpeg path, and output directory
- Truncates the URL after `&` to simulate Windows CMD command-line behavior
- Uses Popen + readline() to parse download progress in real time
- `update_output_dir()` method allows changing the output directory at runtime
- **No GUI library dependencies whatsoever**

### logger.py — Logging Module
- `Logger` class: manages log file creation and writing
- Creates log files named by date (e.g. `2026-03-28.log`)
- Supports three log levels: SUCCESS / ERROR / INFO
- Logs are stored in reverse chronological order — newest entry always at the top
- `update_log_dir()` method allows changing the log directory at runtime
- **No GUI library dependencies whatsoever**

### config.json — Config File
- JSON format with three keys: `download_dir`, `log_dir`, and `language`
- Defaults: `"downloads"`, `"logs"`, `"zh"`
- Loaded on startup; written when the settings dialog saves or the language is switched

## Usage

### Requirements

- **OS**: Windows 7 or later
- **Python**: Python 3.8 or later
- **No extra dependencies**: uses only the Python standard library (tkinter, subprocess, threading, etc.)

### Running the Program

```bash
python main.py
```

### Steps

1. Launch the program — the main window appears
2. Paste a video URL into the input field (e.g. `https://www.youtube.com/watch?v=fnblCGXJqC8`)
3. Click "Download" (or press Enter)
4. Wait for the download to finish — a dialog will appear
5. The downloaded video is saved to the `downloads/` directory by default (customizable via Settings)

### Language Switching

1. Find the language selector dropdown in the top-right of the main window
2. Click the dropdown and select a language (🇨🇳 中文 / 🇺🇸 English)
3. All UI text switches instantly, including buttons, menus, status messages, and dialogs
4. The language setting is automatically saved to config.json and restored on the next launch

### Settings

1. Click the "Settings" button in the main window
2. In the settings dialog, change the download directory or log directory
3. Click "Browse..." to use a directory picker
4. Click "Save" to apply (written to `config.json`, loaded automatically next launch)
5. Click "Cancel" to discard changes

## Using downloader.py as a Standalone Module

`downloader.py` can be imported directly by any Python program:

```python
from downloader import VideoDownloader

# Use default config (auto-detects core/ directory)
dl = VideoDownloader()
result = dl.download("https://www.youtube.com/watch?v=xxx")

if result.success:
    print(f"Download successful: {result.video_path}")
else:
    print(f"Download failed: {result.error}")

# Custom config
dl = VideoDownloader(
    ytdlp_path="C:/tools/yt-dlp.exe",  # custom yt-dlp path
    ffmpeg_path="C:/tools/",            # custom ffmpeg directory
    output_dir="C:/videos/"             # custom output directory
)
result = dl.download("https://www.youtube.com/watch?v=xxx")

# With progress callback
def on_progress(percent):
    if percent < 0:
        print("Processing / merging...")
    else:
        print(f"Download progress: {percent:.1f}%")

result = dl.download("https://www.youtube.com/watch?v=xxx", progress_callback=on_progress)

# Update output directory at runtime
dl.update_output_dir("D:/new_downloads")

# DownloadResult dataclass fields
# result.success   : bool   - Whether the download succeeded
# result.message   : str    - Result description
# result.output    : str    - Full yt-dlp output
# result.video_path: str    - Video file path (on success)
# result.error     : str    - Error message (on failure)
```

## Notes

1. Ensure `core/` contains `yt-dlp.exe` and `ffmpeg.exe`
2. If you get a 403 error, yt-dlp may be outdated — run `core\yt-dlp.exe --update` to update it
3. Videos are saved to `downloads/` in the program directory by default; this can be changed in Settings
4. Log files are saved in `logs/`, named by date, with the newest entry at the top; the log directory can also be changed in Settings
5. The program uses the system's default encoding to read yt-dlp output, compatible with Chinese Windows environments
6. URLs are automatically truncated after `&` to simulate Windows CMD behavior, ensuring results match what you'd get running yt-dlp directly in CMD
7. Settings are saved to `config.json`; deleting this file resets all settings including language to defaults
8. Log content is always written in English, regardless of the current UI language
9. Language names in the dropdown are always displayed in their native language (e.g. "中文" always shows as "中文", not translated)
