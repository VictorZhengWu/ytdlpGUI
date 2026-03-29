# yt-dlp GUI Video Downloader — Program Design Flowcharts

## Overall Program Execution Flow

```mermaid
flowchart TD
    A[Program Start main.py] --> B[Load config.json<br/>download_dir + log_dir + language]
    B --> C[Create tkinter Main Window]
    C --> D[Initialize Logger<br/>using configured log_dir]
    D --> E[Initialize App GUI<br/>using configured download_dir and language]
    E --> F[Set UI text based on<br/>language setting]
    F --> G[Show Main Window — Await User Action]
    G --> H{User Action}
    H -->|Enter URL and click Download / press Enter| I[on_download Event Handler]
    H -->|Click Settings button| J[_open_settings — Open Settings Dialog]
    H -->|Switch language dropdown| K[_on_language_change]
    H -->|Close window| Z[Program Exit]

    K --> K2[Update current_lang]
    K2 --> K3[_refresh_ui — Refresh All UI Text<br/>title / buttons / menus / status label]
    K3 --> K4[_save_config — Save language to config.json]
    K4 --> G

    J --> J2[Show Settings Dialog Toplevel<br/>All text in current language]
    J2 --> J3{User Choice}
    J3 -->|Click Save| L[Validate directory path is non-empty]
    L --> M{Validation passed?}
    M -->|No| N[Show warning dialog]
    N --> J2
    M -->|Yes| O[Update downloader.output_dir]
    O --> P[Update logger.log_dir]
    P --> Q[Write to config.json]
    Q --> R[Close Settings Dialog]
    R --> G
    J3 -->|Click Cancel| R

    I --> S{Is URL empty?}
    S -->|Yes| T[Show warning: Please enter a video URL]
    T --> G
    S -->|No| U[Disable Download button, Settings button, and input box]
    U --> V[Update status label: Downloading...]
    V --> W[Create background thread]
    W --> X[_do_download runs in background thread]

    X --> Y[VideoDownloader.validate_url — Validate URL]
    Y --> Z2{Is URL format valid?}
    Z2 -->|No| AA[Return DownloadResult failure]
    Z2 -->|Yes| AB[Build yt-dlp command arguments<br/>Truncate URL after '&'<br/>Simulate CMD behavior<br/>Use Popen + readline for real-time output]
    AB --> AC[subprocess.Popen executes yt-dlp.exe]

    AC --> AD{Execution exception?}
    AD -->|Timeout| AE[Return timeout error result]
    AD -->|Other exception| AF[Return unknown error result]
    AD -->|Completed normally| AG{Return code == 0?}

    AG -->|Yes| AH[Extract video file path]
    AH --> AI[Return success result]
    AG -->|No| AA

    AA --> AJ[_on_download_complete callback]
    AE --> AJ
    AF --> AJ
    AI --> AJ

    AJ --> AK{Download successful?}
    AK -->|Success| AL[Logger.log_success — Write success log<br/>New log inserted at top of file]
    AL --> AM[Restore buttons and input box state]
    AM --> AN[Update status label: Download complete!]
    AN --> AO[Show success dialog]
    AO --> G

    AK -->|Failure| AP[Logger.log_error — Write error log<br/>New log inserted at top of file]
    AP --> AQ[Restore buttons and input box state]
    AQ --> AR[Update status label: Download failed]
    AR --> AS[Show error dialog]
    AS --> G
```

## Module Call Relationships

```mermaid
graph LR
    A[main.py<br/>Entry Point] --> B[gui.py<br/>GUI Module]
    B --> C[downloader.py<br/>Download Core Module]
    B --> D[logger.py<br/>Logger Module]
    B --> E[config.json<br/>Config File]
    C --> F[core/yt-dlp.exe<br/>CLI Tool]
    C --> G[core/ffmpeg.exe<br/>Audio/Video Processing Tool]
```

## Class Structure

```mermaid
classDiagram
    class App {
        -root: tk.Tk
        -config: dict
        -base_dir: str
        -current_lang: str
        -downloader: VideoDownloader
        -logger: Logger
        -url_entry: tk.Entry
        -download_btn: tk.Button
        -settings_btn: tk.Button
        -lang_combo: ttk.Combobox
        -status_label: tk.Label
        -progress_bar: ttk.Progressbar
        +__init__(root, config)
        +t(key) str
        +on_download()
        -_do_download(url)
        -_on_download_complete(result)
        -_open_settings()
        -_on_language_change(event)
        -_refresh_ui()
        -_save_config()
        -_center_window(width, height)
        -_update_progress(percent)
        -_set_progress_indeterminate()
    }

    class VideoDownloader {
        -base_dir: str
        -ytdlp_path: str
        -ffmpeg_path: str
        -output_dir: str
        +__init__(ytdlp_path, ffmpeg_path, output_dir)
        +validate_url(url) tuple
        +download(url, progress_callback) DownloadResult
        +update_output_dir(new_dir)
        -_parse_progress(line, progress_callback)
        -_extract_video_path(stdout, save_dir) str
    }

    class DownloadResult {
        +success: bool
        +message: str
        +output: str
        +video_path: str
        +error: str
    }

    class Logger {
        -base_dir: str
        -log_dir: str
        -log_file: str
        +__init__(log_dir)
        +log(level, message)
        +log_success(url, details)
        +log_error(url, error_msg)
        +log_info(message)
        +update_log_dir(new_dir)
    }

    App --> VideoDownloader : uses
    App --> Logger : uses
    App --> config.json : read/write config
    App --> TRANSLATIONS : multilingual translation
    VideoDownloader --> DownloadResult : returns
```

## Download Flow — Detailed Sequence

```mermaid
sequenceDiagram
    participant User as User
    participant GUI as GUI (gui.py)
    participant Thread as Background Thread
    participant DL as VideoDownloader
    participant YTDLP as yt-dlp.exe
    participant Log as Logger

    User->>GUI: Enter URL and click Download
    GUI->>GUI: Validate URL is non-empty
    GUI->>GUI: Disable Download button, Settings button, and input box
    GUI->>Thread: Start background thread
    GUI->>GUI: Update status: Downloading...

    Thread->>DL: download(url, progress_callback)
    DL->>DL: validate_url(url)
    DL->>DL: Truncate URL after '&'<br/>Simulate CMD behavior
    DL->>DL: Build command arguments (with --newline)
    DL->>YTDLP: Popen(command, stdout=PIPE)
    
    loop Read output line by line
        YTDLP-->>DL: readline() returns one line
        DL->>DL: _parse_progress — parse progress
        DL-->>GUI: root.after(progress callback)
        GUI->>GUI: Update progress bar
    end
    
    YTDLP-->>DL: Process ends, return code received
    DL->>DL: Determine success / failure
    DL-->>Thread: Return DownloadResult

    Thread->>Log: Write log (success / failure)<br/>New log inserted at top of file
    Thread->>GUI: root.after(callback)

    alt Download successful
        GUI->>GUI: Restore all button states
        GUI->>GUI: Update status: Download complete!
        GUI->>User: Show success dialog
    else Download failed
        GUI->>GUI: Restore all button states
        GUI->>GUI: Update status: Download failed
        GUI->>User: Show error dialog
    end
```

## Settings Flow

```mermaid
sequenceDiagram
    participant User as User
    participant GUI as GUI (gui.py)
    participant SettingsWin as Settings Dialog
    participant DL as VideoDownloader
    participant Log as Logger
    participant Config as config.json

    User->>GUI: Click "Settings" button
    GUI->>SettingsWin: Create Toplevel settings dialog<br/>All text in current language
    SettingsWin->>SettingsWin: Load current config into input fields
    
    User->>SettingsWin: Modify directory path or click "Browse..."
    
    alt Click "Browse..."
        SettingsWin->>User: Open filedialog directory picker
        User->>SettingsWin: Select directory
    end
    
    User->>SettingsWin: Click "Save"
    SettingsWin->>SettingsWin: Validate path is non-empty
    SettingsWin->>DL: update_output_dir(new_dir)
    SettingsWin->>Log: update_log_dir(new_dir)
    SettingsWin->>Config: Write to config.json
    SettingsWin->>Log: Log settings change
    SettingsWin->>GUI: Close dialog
```

## Language Switch Flow

```mermaid
sequenceDiagram
    participant User as User
    participant GUI as GUI (gui.py)
    participant Config as config.json
    participant Log as Logger

    User->>GUI: Select language from dropdown
    GUI->>GUI: _on_language_change event triggered
    GUI->>GUI: Update current_lang
    GUI->>GUI: _refresh_ui — Refresh all UI text
    Note over GUI: Updates: window title, labels, buttons<br/>context menu, status label
    GUI->>Config: _save_config — Write to config.json
    GUI->>Log: Log language change
```
