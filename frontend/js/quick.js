/* 常用设置面板：把最常用的 yt-dlp 选项包装成友好控件（值最终仍写入 options 注册表，
   与高级面板共用同一 state.options，界面与功能分离原则不变）。
   文案软编码：每项 {zh,en,ja,ko}，缺失语言回退 zh。 */
"use strict";

const QUICK_GROUPS = [
  {
    title: { zh: "保存位置", en: "Save Location", ja: "保存先", ko: "저장 위치" },
    items: [
      { flag: "__downloaddir", label: { zh: "下载目录", en: "Download directory", ja: "保存先ディレクトリ", ko: "다운로드 폴더" }, widget: "dir" },
      { flag: "__filenametpl", label: { zh: "文件名模板", en: "Filename template", ja: "ファイル名テンプレート", ko: "파일명 템플릿" }, widget: "cfgtext", configKey: "filename_template",
        ph: { zh: "%(title)s [%(id)s].%(ext)s", en: "%(title)s [%(id)s].%(ext)s", ja: "%(title)s [%(id)s].%(ext)s", ko: "%(title)s [%(id)s].%(ext)s" } },
    ],
  },
  {
    title: { zh: "画质与格式", en: "Quality & Format", ja: "画質と形式", ko: "화질과 포맷" },
    items: [
      { flag: "__quality", label: { zh: "画质", en: "Quality", ja: "画質", ko: "화질" }, widget: "select", def: "best",
        choices: [
          { v: "best",   l: { zh: "最佳画质（自动）", en: "Best (auto)", ja: "最高画質（自動）", ko: "최고 화질 (자동)" } },
          { v: "2160",   l: { zh: "4K 2160p", en: "4K 2160p", ja: "4K 2160p", ko: "4K 2160p" } },
          { v: "1080",   l: { zh: "1080p 全高清", en: "1080p FHD", ja: "1080p フルHD", ko: "1080p FHD" } },
          { v: "720",    l: { zh: "720p 高清", en: "720p HD", ja: "720p HD", ko: "720p HD" } },
          { v: "480",    l: { zh: "480p 标清（省空间）", en: "480p", ja: "480p 標準", ko: "480p" } } ] },
      { flag: "--merge-output-format", label: { zh: "容器格式", en: "Container", ja: "コンテナ形式", ko: "컨테이너" }, widget: "select", def: "mp4",
        choices: [
          { v: "mp4", l: "MP4" }, { v: "mkv", l: "MKV" }, { v: "webm", l: "WebM" } ] },
      { flag: "--extract-audio", label: { zh: "仅提取音频（MP3 等）", en: "Audio only", ja: "音声のみ抽出（MP3 など）", ko: "오디오만 추출 (MP3 등)" }, widget: "check" },
      { flag: "--audio-format", label: { zh: "音频格式", en: "Audio format", ja: "音声形式", ko: "오디오 포맷" }, widget: "select", def: "mp3",
        choices: ["mp3", "m4a", "opus", "wav", "flac"].map(v => ({ v, l: v.toUpperCase() })) },
      { flag: "--audio-quality", label: { zh: "音频质量", en: "Audio quality", ja: "音声品質", ko: "오디오 품질" }, widget: "select", def: "0",
        choices: [
          { v: "0", l: { zh: "最好（VBR 0）", en: "Best (VBR 0)", ja: "最高（VBR 0）", ko: "최고 (VBR 0)" } },
          { v: "192K", l: "192 kbps" }, { v: "320K", l: "320 kbps" } ] },
    ],
  },
  {
    title: { zh: "字幕", en: "Subtitles", ja: "字幕", ko: "자막" },
    items: [
      { flag: "--write-subs", label: { zh: "下载字幕文件", en: "Download subtitles", ja: "字幕ファイルを保存", ko: "자막 파일 저장" }, widget: "check" },
      { flag: "--write-auto-subs", label: { zh: "下载自动生成字幕（语音识别）", en: "Auto subtitles", ja: "自動生成字幕を保存", ko: "자동 생성 자막 저장" }, widget: "check" },
      { flag: "--sub-langs", label: { zh: "字幕语言", en: "Subtitle languages", ja: "字幕の言語", ko: "자막 언어" }, widget: "text",
        ph: { zh: "如：zh-Hans,en.*（逗号分隔，all=全部）", en: "e.g. zh-Hans,en.*", ja: "例: ja,en.*", ko: "예: ko,en.*" } },
      { flag: "--embed-subs", label: { zh: "字幕嵌入视频内", en: "Embed subtitles", ja: "字幕を動画に埋め込む", ko: "자막을 영상에 삽입" }, widget: "check" },
      { flag: "--convert-subs", label: { zh: "字幕转为", en: "Convert subs to", ja: "字幕の変換先", ko: "자막 변환" }, widget: "select", def: "srt",
        choices: ["srt", "vtt", "ass", "lrc"].map(v => ({ v, l: v.toUpperCase() })) },
    ],
  },
  {
    title: { zh: "播放列表", en: "Playlist", ja: "プレイリスト", ko: "재생목록" },
    items: [
      { flag: "--playlist-items", label: { zh: "只下载列表中的第几项", en: "Playlist items", ja: "取得する項目", ko: "가져올 항목" }, widget: "text",
        ph: { zh: "如：1,3-5（留空=全部）", en: "e.g. 1,3-5", ja: "例: 1,3-5", ko: "예: 1,3-5" } },
      { flag: "--playlist-reverse", label: { zh: "倒序下载播放列表", en: "Reverse order", ja: "逆順でダウンロード", ko: "역순 다운로드" }, widget: "check" },
      { flag: "--download-archive", label: { zh: "已下载记录（自动跳过重复）", en: "Archive file", ja: "ダウンロード記録（重複スキップ）", ko: "다운로드 기록 (중복 건너뛰기)" }, widget: "text",
        ph: { zh: "如：archive.txt（强烈推荐）", en: "e.g. archive.txt", ja: "例: archive.txt", ko: "예: archive.txt" } },
    ],
  },
  {
    title: { zh: "网络与登录", en: "Network & Auth", ja: "ネットワークとログイン", ko: "네트워크와 로그인" },
    items: [
      { flag: "--proxy", label: { zh: "代理服务器", en: "Proxy", ja: "プロキシ", ko: "프록시" }, widget: "text",
        ph: { zh: "如：socks5://127.0.0.1:1080", en: "e.g. socks5://127.0.0.1:1080", ja: "例: socks5://127.0.0.1:1080", ko: "예: socks5://127.0.0.1:1080" } },
      { flag: "__jsruntime", label: { zh: "YouTube 解析引擎", en: "YouTube JS runtime", ja: "YouTube 解析エンジン", ko: "YouTube 파싱 엔진" },
        widget: "select", dyn: "js" },
      { flag: "__cookiebrowser", label: { zh: "浏览器登录态（会员内容）", en: "Browser cookies", ja: "ブラウザのログイン情報", ko: "브라우저 로그인 상태" },
        widget: "select", dyn: "cookie", choices: [
          { v: "chrome", l: "Chrome" }, { v: "edge", l: "Edge" }, { v: "firefox", l: "Firefox" }, { v: "safari", l: "Safari" } ] },
      { flag: "--limit-rate", label: { zh: "限速", en: "Speed limit", ja: "速度制限", ko: "속도 제한" }, widget: "text",
        ph: { zh: "如：4M（留空=不限）", en: "e.g. 4M", ja: "例: 4M", ko: "예: 4M" } },
      { flag: "--concurrent-fragments", label: { zh: "并发连接数（加速）", en: "Concurrency", ja: "並列接続数", ko: "동시 연결 수" }, widget: "select", def: "1",
        choices: ["1", "3", "5", "8", "16"].map(v => ({ v, l: v })) },
    ],
  },
  {
    title: { zh: "增强功能", en: "Extras", ja: "拡張機能", ko: "부가 기능" },
    items: [
      { flag: "--sponsorblock-remove", label: { zh: "自动跳过广告/片头（SponsorBlock）", en: "Skip sponsors", ja: "スポンサー部分を自動スキップ", ko: "광고 자동 건너뛰기" },
        widget: "select", def: "", choices: [
          { v: "", l: { zh: "不跳过", en: "Off", ja: "スキップしない", ko: "끄기" } },
          { v: "sponsor,selfpromo", l: { zh: "跳过赞助与自我推广", en: "Sponsor+selfpromo", ja: "スポンサーと自己宣伝をスキップ", ko: "스폰서+자체 홍보" } },
          { v: "sponsor,selfpromo,interaction,intro,outro", l: { zh: "跳过赞助+互动+片头片尾", en: "Aggressive", ja: "広範囲スキップ", ko: "적극적 건너뛰기" } } ] },
      { flag: "--embed-thumbnail", label: { zh: "封面嵌入视频", en: "Embed thumbnail", ja: "サムネイルを埋め込む", ko: "썸네일 삽입" }, widget: "check" },
      { flag: "--embed-metadata", label: { zh: "写入标题等元数据", en: "Embed metadata", ja: "メタデータを書き込む", ko: "메타데이터 기록" }, widget: "check" },
      { flag: "--embed-chapters", label: { zh: "保留章节标记", en: "Embed chapters", ja: "チャプターを保持", ko: "챕터 유지" }, widget: "check" },
    ],
  },
];
