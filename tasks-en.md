# yt-dlp GUI Program — Task Checklist

## I. Overall Program Requirements

1. Build a Windows GUI application using Python 3 + tkinter
2. UI must include: a text input field (for pasting video URLs), a "Download" button, a "Settings" button, and a language selector dropdown
3. UI design based on `UI.jpg`
4. Download functionality strictly separated from UI logic — `downloader.py` must not depend on any GUI library and must be usable as a standalone module imported by other programs
5. Downloaded videos stored in the `downloads/` subdirectory of the working directory (customizable via Settings)
6. Log download successes and failures to log files
7. Errors during download must be caught and displayed to the user
8. A completion notice must be shown after a download finishes
9. All code must include detailed comments (block-level comments + inline comments where possible)
10. Save program design flowcharts separately in Mermaid format (`flow.md`)
11. Provide a `README.md` summarizing the design approach and usage instructions
12. Download only a single video file — even if the URL contains playlist parameters (e.g. `&list=...`), only the target video is downloaded
13. Logs are stored in reverse chronological order — the most recent log entry is always at the top of the log file
14. Support customizing download and log directories via a settings dialog; configuration is persisted to `config.json`
15. Support Chinese/English UI switching via a dropdown; switching instantly updates all UI text; language preference is persisted to `config.json`

---

## II. Project File Structure

```
ytdlpGUI/
├── main.py          # Entry point (load config, create window, start main loop)
├── gui.py           # GUI module (download/settings buttons, language switch, settings dialog, progress bar)
├── downloader.py    # Download core module (standalone, no GUI dependencies)
├── logger.py        # Logging module (standalone, no GUI dependencies)
├── config.json      # User config file (download dir, log dir, UI language)
├── flow.md          # Mermaid flowcharts
├── README.md        # Project documentation
├── tasks.md         # This file
├── core/            # yt-dlp and companion tools (pre-existing)
│   ├── yt-dlp.exe
│   ├── ffmpeg.exe
│   ├── ffprobe.exe
│   └── ...
├── downloads/       # Video download directory (auto-created at runtime, customizable)
└── logs/            # Log file directory (auto-created at runtime, customizable)
```

---

## III. Subtask Checklist

### Task 1: Download Core Module `downloader.py`

- [x] Define `DownloadResult` dataclass (success / message / output / video_path / error)
- [x] Implement `VideoDownloader` class
  - [x] `__init__(self, ytdlp_path, ffmpeg_path, output_dir)` — Initialize paths; support custom and auto-detected values
  - [x] `validate_url(self, url)` — Basic URL format validation (non-empty, contains protocol)
  - [x] `download(self, url, output_dir=None, progress_callback=None)` — Core download method
    - [x] Construct full path to yt-dlp.exe (`core/yt-dlp.exe`)
    - [x] Build subprocess command arguments (paths, ffmpeg location, output dir, URL, --newline)
    - [x] Use Popen + readline() to read output in real time and parse progress percentage
    - [x] Truncate URL after "&" to simulate Windows CMD behavior
    - [x] 1-hour timeout timer
    - [x] Return structured `DownloadResult`
  - [x] `update_output_dir(self, new_dir)` — Update download directory at runtime
  - [x] `_parse_progress(self, line, progress_callback)` — Parse progress information
  - [x] `_extract_video_path(self, stdout, save_dir)` — Extract video file path from output
- [x] Ensure this module does not import any GUI libraries (tkinter / PyQt etc.)
- [x] Ensure it can be used directly via `from downloader import VideoDownloader` by other Python programs

### Task 2: Logging Module `logger.py`

- [x] Implement `Logger` class
  - [x] `__init__(self, log_dir)` — Create log directory; name log files by date (e.g. `2026-03-28.log`)
  - [x] `log(self, level, message)` — Write timestamp + level + message (new log inserted at top of file, reverse chronological order)
  - [x] `log_success(self, url, details)` — Log successful download info
  - [x] `log_error(self, url, error_msg)` — Log failed download info + error details
  - [x] `log_info(self, message)` — Log general information
  - [x] `update_log_dir(self, new_dir)` — Update log directory at runtime
- [x] Logs stored in reverse chronological order — newest entry always at the top

### Task 3: GUI Module `gui.py`

- [x] Implement `App` class
  - [x] `__init__(self, root, config=None)` — Initialize window
    - [x] Set window title (based on current language)
    - [x] Set window size and center it on screen
    - [x] Create URL text input field (Entry)
    - [x] Create "Download" button (Button)
    - [x] Create "Settings" button (Button)
    - [x] Create language selector dropdown (ttk.Combobox, with flag emoji + language name)
    - [x] Create progress bar (ttk.Progressbar, supports determinate / indeterminate modes)
    - [x] Create status label (Label)
    - [x] Configure download dir, log dir, and language from passed-in config dict
  - [x] `t(self, key)` — Translation helper: returns UI text for the current language
  - [x] `_refresh_ui(self)` — Refresh all UI text after language switch
  - [x] `_on_language_change(self, event)` — Language dropdown change event handler
    - [x] Update current_lang
    - [x] Call _refresh_ui to refresh UI
    - [x] Call _save_config to persist to config.json
  - [x] `on_download(self)` — Download button click event handler
    - [x] Get URL from input field
    - [x] Validate URL is non-empty
    - [x] Disable Download and Settings buttons (prevent duplicate operations)
    - [x] Start background thread calling `VideoDownloader.download()`
    - [x] Pass progress_callback to update progress bar in real time
  - [x] `_do_download(self, url)` — Execute download in background thread
    - [x] Schedule GUI updates to main thread via root.after()
  - [x] `_on_download_complete(self, result)` — Download completion callback
    - [x] Restore buttons and input field state
    - [x] Show success/failure dialog based on result
  - [x] `_open_settings(self)` — Settings dialog
    - [x] Create modal Toplevel dialog; all text in current language
    - [x] Download directory input + "Browse..." button (filedialog.askdirectory)
    - [x] Log directory input + "Browse..." button (filedialog.askdirectory)
    - [x] Save button: update downloader and logger directories, write to config.json
    - [x] Cancel button: close dialog
  - [x] `_save_config(self)` — Save config to config.json (reusable across multiple call sites)
  - [x] Right-click context menu on input field (Paste, Copy, Clear — text follows language switch)
  - [x] Real-time progress bar display (percentage mode + indeterminate mode)
  - [x] Download state tracking (_downloading / _processing / _last_percent) to correctly update status label on language switch

### Task 4: Multilingual Support

- [x] Define `TRANSLATIONS` dictionary (zh / en languages)
- [x] Define `LANG_OPTIONS` list (flag emoji + native language name)
- [x] Cover all UI text: window title, labels, buttons, menus, status messages, dialog titles and content
- [x] Language dropdown uses ttk.Combobox (readonly mode)
- [x] Language names always displayed in their native language (中文 / English, not translated with UI)
- [x] Switching language instantly refreshes all UI text (including download status text)
- [x] Language selection saved to config.json (`language` key), written immediately
- [x] Language setting loaded from config.json on startup

### Task 5: Entry Point `main.py`

- [x] Load config.json configuration file
- [x] DEFAULT_CONFIG includes `language` key (default `"zh"`)
- [x] Create tkinter main window
- [x] Initialize `App` (pass in config dict)
- [x] Start tkinter main loop (`mainloop()`)

### Task 6: Config File `config.json`

- [x] JSON format with keys: download_dir, log_dir, language
- [x] Defaults: `"downloads"`, `"logs"`, `"zh"`
- [x] Loaded on startup (uses defaults if file not found)
- [x] Written when settings dialog saves
- [x] Written immediately on language switch

### Task 7: Mermaid Flowcharts `flow.md`

- [x] Overall program execution flowchart (includes config loading, language setup, settings flow)
- [x] Module call relationship diagram
- [x] Class structure diagram (includes multilingual-related attributes and methods)
- [x] Download flow sequence diagram (includes Popen + readline loop)
- [x] Settings flow sequence diagram
- [x] Language switch flow sequence diagram

### Task 8: README.md Documentation

- [x] Program overview
- [x] Design philosophy (layered architecture)
- [x] File structure (includes config.json)
- [x] Usage instructions
  - [x] Requirements (Python 3 version)
  - [x] Run command
  - [x] Steps (includes Settings and language switch instructions)
- [x] Sample code for using `downloader.py` as a standalone module
- [x] Config file explanation (includes `language` key)
- [x] Notes

### Task 9: Code Comments

- [x] Add module-level docstring at the top of each file
- [x] Add docstrings to each class and function
- [x] Add inline comments to as many lines of code as possible

---

## IV. Key Design Decisions (Confirmed)

| Decision | Approach |
|----------|----------|
| GUI library | tkinter (zero extra dependencies) |
| UI / logic separation | downloader.py fully independent, no GUI dependencies |
| Multithreading | Download runs in a separate thread to keep UI responsive |
| Video storage | `downloads/` subdirectory, auto-created at runtime, customizable via Settings |
| Log storage | `logs/` subdirectory, named by date, auto-created at runtime, customizable via Settings |
| Log ordering | Newest log at top of file (reverse chronological) |
| Log language | Log content always in English (unaffected by UI language switch) |
| yt-dlp invocation | subprocess.Popen calling `core/yt-dlp.exe`, output read line by line with readline() |
| ffmpeg path | Specified via `--ffmpeg-location` pointing to `core/` |
| Progress parsing | `--newline` flag; Popen + readline() parsing percentage line by line |
| Playlist handling | Truncate URL after "&" to simulate CMD behavior |
| Encoding handling | Auto-detect system encoding + errors='replace'; compatible with Chinese Windows |
| Config persistence | config.json (JSON format); loaded on startup, saved on settings change or language switch |
| Progress bar mode | Determinate mode for download percentage; indeterminate mode for merging/transcoding |
| GUI thread safety | All tkinter operations scheduled to main thread via root.after() |
| Multilingual approach | TRANSLATIONS dict + t(key) method + _refresh_ui() refresh |
| Language option display | Flag emoji + native language name (always shown in native language, not translated) |
| Language persistence | `language` key in config.json, saved immediately on switch |
