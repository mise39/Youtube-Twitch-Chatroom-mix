import tkinter as tk
from tkinter import ttk, messagebox, font
import threading
import socket
import re
import pytchat
import time
import random
import urllib.parse as urlparse
import emoji
import urllib.request
from PIL import Image, ImageTk
import io
import os
import sys
from datetime import datetime
import queue
import zipfile
import ast

# Helper function to get the base path (works for both script and executable)
def get_base_path():
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller executable
        return os.path.dirname(sys.executable)
    else:
        # Running as a Python script
        return os.path.dirname(os.path.abspath(__file__))

# --------------------
# YouTube 聊天室
# --------------------
def youtube_chat(video_id, message_queue, status_callback):
    while True:
        try:
            chat = pytchat.create(video_id=video_id, interruptable=False)
            status_callback("YouTube", "OK!")
            while chat.is_alive():
                try:
                    for c in chat.get().sync_items():
                        message = emoji.emojize(c.message, language='alias')
                        message_queue.put(("YouTube", c.author.name, message))
                    time.sleep(1)
                except IndexError as ie:
                    message_queue.put(("YouTube", "SYSTEM", f"索引錯誤：{ie}"))
                    status_callback("YouTube", f"錯誤：索引錯誤")
                    time.sleep(5)
                    break
        except Exception as e:
            message_queue.put(("YouTube", "SYSTEM", f"錯誤：{e}"))
            status_callback("YouTube", f"錯誤：{e}")
            time.sleep(5)

# --------------------
# Twitch 聊天室 (IRC 匿名)
# --------------------
def twitch_chat(channel, message_queue, status_callback):
    while True:
        try:
            server = "irc.chat.twitch.tv"
            port = 6667
            nickname = f"justinfan{random.randint(10000,99999)}"
            token = "SCHMOOPIIE"
            channel = channel.lower()

            sock = socket.socket()
            sock.connect((server, port))
            sock.send(f"PASS {token}\r\n".encode("utf-8"))
            sock.send(f"NICK {nickname}\r\n".encode("utf-8"))
            sock.send(f"JOIN #{channel}\r\n".encode("utf-8"))

            status_callback("Twitch", "OK!")
            #log_file_path = os.path.join(get_base_path(), "twitch_emoji_debug.log")

            #Debug用 初始化日誌檔案
            #with open(log_file_path, "a", encoding="utf-8") as log_file:
                #timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                #log_file.write(f"{timestamp} | Twitch Debug Log Initialized | Channel: {channel}\n")

            while True:
                resp = sock.recv(2048).decode("utf-8", errors="ignore")
                lines = resp.split("\r\n")
                for line in lines:
                    if not line:
                        continue
                    if line.startswith("PING"):
                        sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                    else:
                        match = re.search(r":(.*?)!.* PRIVMSG #.* :(.*)", line)
                        if match:
                            user = match.group(1)
                            raw_msg = match.group(2)  # 原始訊息
                            msg = emoji.emojize(raw_msg, language='alias')
                            # 記錄所有訊息到日誌，標記是否包含 emoji
                            has_emoji = any(emoji.is_emoji(char) for char in msg)
                            #timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            #with open(log_file_path, "a", encoding="utf-8") as log_file:
                                #log_file.write(f"{timestamp} | Twitch | User: {user} | Raw: {raw_msg} | Emojized: {msg} | Contains Emoji: {has_emoji}\n")
                            #print(f"DEBUG: Twitch | User: {user} | Raw: {raw_msg} | Emojized: {msg} | Contains Emoji: {has_emoji}")
                            message_queue.put(("Twitch", user, msg))
        except Exception as e:
            message_queue.put(("Twitch", "SYSTEM", f"錯誤：{e}"))
            status_callback("Twitch", f"錯誤：{e}")
            #timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            #with open(log_file_path, "a", encoding="utf-8") as log_file:
                #log_file.write(f"{timestamp} | Twitch | Error: {e}\n")
            #print(f"DEBUG: Twitch | Error: {e}")
            time.sleep(5)
            continue

# --------------------
# Tkinter GUI
# --------------------
class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YTTVChat v3.0f ▶-YT 🎮-TV")
        self.root.geometry("700x1000")
        self.root.configure(bg="#1e1e1e")

        # Get base path for file operations
        self.base_path = get_base_path()

        # Create emoji directories in the executable's directory
        self.emojis_dir = os.path.join(self.base_path, "emojis")
        self.ytemoji_dir = os.path.join(self.base_path, "ytemoji")
        self.tvemoji_dir = os.path.join(self.base_path, "tvemoji")
        os.makedirs(self.emojis_dir, exist_ok=True)
        os.makedirs(self.ytemoji_dir, exist_ok=True)
        os.makedirs(self.tvemoji_dir, exist_ok=True)

        # Initialize emoji dictionaries
        self.YOUTUBE_EMOJIS = {}
        self.YOUTUBE_EMOJI_URLS = {}
        self.TWITCH_EMOJIS = {}
        self.TWITCH_EMOJI_URLS = {}
        self.load_emoji_config()

        # Message queue for thread-safe message handling
        self.message_queue = queue.Queue()

        # Auto-scroll flag
        self.auto_scroll = True

        # Font settings
        self.available_fonts = sorted(list(font.families()))  # Get all available system fonts
        self.current_font = "Microsoft JhengHei UI"
        self.font_size = 20 #chat 文字大小

        # 樣式
        style = ttk.Style()
        style.theme_use("clam")

        # Combined input frame for YouTube and Twitch
        self.input_frame = tk.Frame(root, bg="#1e1e1e")
        self.input_frame.pack(fill="x", padx=5, pady=5)
        
        # YouTube input
        tk.Label(self.input_frame, text="YT▶", bg="#1e1e1e", fg="#cdd6f4").pack(side="left")
        self.youtube_entry = tk.Entry(self.input_frame, width=30, font=("Microsoft JhengHei UI", 12))
        self.youtube_entry.pack(side="left", padx=5)
        
        # Twitch input
        tk.Label(self.input_frame, text="🎮TV", bg="#1e1e1e", fg="#cdd6f4").pack(side="right")
        self.twitch_entry = tk.Entry(self.input_frame, width=30, font=("Microsoft JhengHei UI", 12))
        self.twitch_entry.pack(side="right", padx=5)

        # 聊天視窗 (使用 Text 代替 Treeview)
        self.text = tk.Text(root, wrap="word", bg="#252526", fg="white", font=(self.current_font, self.font_size), height=22)
        self.text.pack(fill="both", expand=True, padx=10, pady=10)
        self.text.config(state="disabled")  # 設為唯讀

        # 配置 Text 標籤樣式
        self.text.tag_configure("youtube_platform", foreground="#ff0000", font=(self.current_font, self.font_size, "bold"), spacing3=10)
        self.text.tag_configure("twitch_platform", foreground="#9146ff", font=(self.current_font, self.font_size, "bold"), spacing3=10)
        self.text.tag_configure("system_platform", foreground="#ffff00", font=(self.current_font, self.font_size, "bold"), spacing3=10)
        self.text.tag_configure("user", foreground="#55ff55", font=(self.current_font, self.font_size, "bold"), spacing3=10)
        self.text.tag_configure("text", foreground="white", font=(self.current_font, self.font_size), spacing3=10)

        self.scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")

        # 狀態顯示
        status_frame = tk.Frame(root, bg="#1e1e1e")
        status_frame.pack(fill="x", padx=5, pady=5)
        self.youtube_status = tk.Label(status_frame, text="▶ 狀態: 未連接", bg="#1e1e1e", fg="#cdd6f4", font=("Microsoft JhengHei UI", 12))
        self.youtube_status.pack(side="left", padx=10)
        self.twitch_status = tk.Label(status_frame, text="🎮 狀態: 未連接", bg="#1e1e1e", fg="#cdd6f4", font=("Microsoft JhengHei UI", 12))
        self.twitch_status.pack(side="left", padx=10)
        self.scroll_toggle_button = tk.Button(status_frame, text="停止捲動", command=self.toggle_scroll, font=("Microsoft JhengHei UI", 10))
        self.scroll_toggle_button.pack(side="left", padx=5)
        self.start_button = tk.Button(status_frame, text="啟動", command=self.start_chat, font=("Microsoft JhengHei UI", 10))
        self.start_button.pack(side="left", padx=5)
        # Font selection dropdown
        self.font_combobox = ttk.Combobox(status_frame, values=self.available_fonts, state="readonly", width=18, font=("Microsoft JhengHei UI", 10))
        self.font_combobox.set(self.current_font)
        self.font_combobox.pack(side="left", padx=5)
        self.font_combobox.bind("<<ComboboxSelected>>", self.change_font)

        self.platform_icons = {"YouTube": "▶", "Twitch": "🎮", "SYSTEM": "⚙"}
        self.image_cache = {}  # Cache for emoji images

        self.youtube_thread = None
        self.twitch_thread = None
        self.youtube_video_id = None
        self.twitch_channel = None
        self.running = False

        # Start processing the message queue
        self.process_queue()

        # Check and download emojis after GUI is loaded
        self.check_and_download_emojis()

    def toggle_scroll(self):
        """Toggle auto-scrolling on or off."""
        self.auto_scroll = not self.auto_scroll
        self.scroll_toggle_button.config(text="恢復捲動" if not self.auto_scroll else "停止捲動")

    def change_font(self, event=None):
        """Update the font of the text widget and tags based on combobox selection."""
        self.current_font = self.font_combobox.get()
        
        # Update main text widget font
        self.text.configure(font=(self.current_font, self.font_size))
        
        # Update tag fonts
        self.text.tag_configure("youtube_platform", font=(self.current_font, self.font_size, "bold"))
        self.text.tag_configure("twitch_platform", font=(self.current_font, self.font_size, "bold"))
        self.text.tag_configure("system_platform", font=(self.current_font, self.font_size, "bold"))
        self.text.tag_configure("user", font=(self.current_font, self.font_size, "bold"))
        self.text.tag_configure("text", font=(self.current_font, self.font_size))

    def load_emoji_config(self):
        """Load emoji configurations from emojis.info and extra_*.txt files."""
        log_file_path = os.path.join(self.base_path, "download_log.txt")

        # Load emojis.info
        emojis_info_path = os.path.join(self.base_path, "emojis.info")
        try:
            with open(emojis_info_path, "r", encoding="utf-8") as f:
                content = f.read()
                local_namespace = {}
                exec(content, {}, local_namespace)
                self.YOUTUBE_EMOJIS.update(local_namespace.get('YOUTUBE_EMOJIS', {}))
                self.YOUTUBE_EMOJI_URLS.update(local_namespace.get('YOUTUBE_EMOJI_URLS', {}))
                self.TWITCH_EMOJIS.update(local_namespace.get('TWITCH_EMOJIS', {}))
                self.TWITCH_EMOJI_URLS.update(local_namespace.get('TWITCH_EMOJI_URLS', {}))
                
            with open(log_file_path, "a", encoding="utf-8") as log_file:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_file.write(f"{timestamp} | Successfully loaded emojis.info\n")
        except Exception as e:
            with open(log_file_path, "a", encoding="utf-8") as log_file:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_file.write(f"{timestamp} | Failed to load emojis.info: {e}\n")

        # Load extra_*.txt files 下載/載入額外的頻道會員emoji
        for filename in os.listdir(self.base_path):
            if filename.startswith('extra_') and filename.endswith('.txt'):
                filepath = os.path.join(self.base_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    local_namespace = {}
                    exec(content, {}, local_namespace)
                    self.YOUTUBE_EMOJIS.update(local_namespace.get('YOUTUBE_EMOJIS', {}))
                    self.YOUTUBE_EMOJI_URLS.update(local_namespace.get('YOUTUBE_EMOJI_URLS', {}))
                    self.TWITCH_EMOJIS.update(local_namespace.get('TWITCH_EMOJIS', {}))
                    self.TWITCH_EMOJI_URLS.update(local_namespace.get('TWITCH_EMOJI_URLS', {}))
                    
                    with open(log_file_path, "a", encoding="utf-8") as log_file:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log_file.write(f"{timestamp} | Successfully loaded {filename}\n")
                except Exception as e:
                    with open(log_file_path, "a", encoding="utf-8") as log_file:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log_file.write(f"{timestamp} | Failed to load {filename}: {e}\n")



    def check_and_download_emojis(self):
        """Check if emoji folders are empty and download if necessary, with user choice for emojis.zip."""
        need_download_emojis = len(os.listdir(self.emojis_dir)) == 0
        need_download_ytemoji = len(os.listdir(self.ytemoji_dir)) == 0
        need_download_tvemoji = len(os.listdir(self.tvemoji_dir)) == 0  # 新增 Twitch 檢查
        
        # 用於等待 ZIP 下載和解壓縮完成的 Event
        self.download_complete = threading.Event()
        
        if need_download_emojis or need_download_ytemoji or need_download_tvemoji:
            choice = messagebox.askyesno("選擇Emoji", "要選用Google Noto Color Emoji嗎？\n(否：預設twitter twemoji)")
            emojis_zip_url = "https://github.com/mise39/Youtube-Twitch-Chatroom-mix/releases/download/1.0/emojis.zip"
            if choice:
                emojis_zip_url = "https://github.com/mise39/Youtube-Twitch-Chatroom-mix/releases/download/1.0/google_emojis.zip"
            
            # 啟動下載執行緒
            download_thread = threading.Thread(
                target=self.download_and_unzip_emojis_thread,
                args=(emojis_zip_url, need_download_emojis, need_download_ytemoji, need_download_tvemoji),
                daemon=True
            )
            download_thread.start()
            
            # 等待下載和解壓縮完成
            self.download_complete.wait(timeout=10)  # 最多等待 60 秒
        
        # 檢查資料夾是否已包含足夠的表情符號，決定是否需要逐一檢查
        if not need_download_ytemoji:
            self.download_youtube_emojis()  # 僅在必要時逐一檢查
        if not need_download_tvemoji:
            self.download_twitch_emojis()

    def download_and_unzip_emojis_thread(self, emojis_zip_url, need_emojis, need_ytemoji, need_tvemoji):
        """Download and unzip emojis.zip, ytemoji.zip, and tvemoji.zip in a thread if their respective folders are empty."""
        log_file_path = os.path.join(self.base_path, "download_log.txt")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_file_path, "a", encoding="utf-8") as log_file:
            if need_emojis:
                self.message_queue.put(("SYSTEM", "", "開始下載 Emoji..."))
                emojis_zip_path = os.path.join(self.base_path, "emojis.zip")
                try:
                    with urllib.request.urlopen(emojis_zip_url) as response:
                        zip_data = response.read()
                    with open(emojis_zip_path, "wb") as f:
                        f.write(zip_data)
                    log_file.write(f"{timestamp} | Successfully downloaded emojis.zip\n")
                    
                    if zipfile.is_zipfile(emojis_zip_path):
                        with zipfile.ZipFile(emojis_zip_path, 'r') as zip_ref:
                            zip_ref.extractall(self.emojis_dir)
                        log_file.write(f"{timestamp} | Successfully unzipped emojis.zip to {self.emojis_dir}\n")
                        self.message_queue.put(("SYSTEM", "", "Emoji 準備OK!"))
                        os.remove(emojis_zip_path)
                    else:
                        log_file.write(f"{timestamp} | Invalid ZIP file: emojis.zip\n")
                        self.message_queue.put(("SYSTEM", "", "無效的 Emoji ZIP 檔案"))
                except Exception as e:
                    log_file.write(f"{timestamp} | Failed to download or unzip emojis.zip: {e}\n")
                    self.message_queue.put(("SYSTEM", "", f"下載或解壓縮 Emoji 失敗：{e}"))
            
            if need_ytemoji:
                self.message_queue.put(("SYSTEM", "", "開始下載 YouTube emoji..."))
                ytemoji_zip_url = "https://github.com/mise39/Youtube-Twitch-Chatroom-mix/releases/download/1.0/ytemoji.zip"
                ytemoji_zip_path = os.path.join(self.base_path, "ytemoji.zip")
                try:
                    with urllib.request.urlopen(ytemoji_zip_url) as response:
                        zip_data = response.read()
                    with open(ytemoji_zip_path, "wb") as f:
                        f.write(zip_data)
                    log_file.write(f"{timestamp} | Successfully downloaded ytemoji.zip\n")
                    
                    if zipfile.is_zipfile(ytemoji_zip_path):
                        with zipfile.ZipFile(ytemoji_zip_path, 'r') as zip_ref:
                            zip_ref.extractall(self.ytemoji_dir)
                        log_file.write(f"{timestamp} | Successfully unzipped ytemoji.zip to {self.ytemoji_dir}\n")
                        self.message_queue.put(("SYSTEM", "", "YouTube emoji準備OK!"))
                        os.remove(ytemoji_zip_path)
                    else:
                        log_file.write(f"{timestamp} | Invalid ZIP file: ytemoji.zip\n")
                        self.message_queue.put(("SYSTEM", "", "無效的 YouTube emoji ZIP 檔案"))
                except Exception as e:
                    log_file.write(f"{timestamp} | Failed to download or unzip ytemoji.zip: {e}\n")
                    self.message_queue.put(("SYSTEM", "", f"下載或解壓縮 YouTube emoji 失敗：{e}"))
            
            if need_tvemoji:
                self.message_queue.put(("SYSTEM", "", "開始下載 Twitch emoji..."))
                tvemoji_zip_url = "https://github.com/mise39/Youtube-Twitch-Chatroom-mix/releases/download/1.0/tvemoji.zip"
                tvemoji_zip_path = os.path.join(self.base_path, "tvemoji.zip")
                try:
                    with urllib.request.urlopen(tvemoji_zip_url) as response:
                        zip_data = response.read()
                    with open(tvemoji_zip_path, "wb") as f:
                        f.write(zip_data)
                    log_file.write(f"{timestamp} | Successfully downloaded tvemoji.zip\n")
                    
                    if zipfile.is_zipfile(tvemoji_zip_path):
                        with zipfile.ZipFile(tvemoji_zip_path, 'r') as zip_ref:
                            zip_ref.extractall(self.tvemoji_dir)
                        log_file.write(f"{timestamp} | Successfully unzipped tvemoji.zip to {self.tvemoji_dir}\n")
                        self.message_queue.put(("SYSTEM", "", "Twitch emoji準備OK!"))
                        os.remove(tvemoji_zip_path)
                    else:
                        log_file.write(f"{timestamp} | Invalid ZIP file: tvemoji.zip\n")
                        self.message_queue.put(("SYSTEM", "", "無效的 Twitch emoji ZIP 檔案"))
                except Exception as e:
                    log_file.write(f"{timestamp} | Failed to download or unzip tvemoji.zip: {e}\n")
                    self.message_queue.put(("SYSTEM", "", f"下載或解壓縮 Twitch emoji 失敗：{e}"))


    def download_youtube_emojis(self):
        """Download YouTube emojis to ytemoji/ directory if not already present, logging to download_log.txt."""
        log_file_path = os.path.join(self.base_path, "download_log.txt")
        with open(log_file_path, "a", encoding="utf-8") as log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"{timestamp} | Starting YouTube emoji download check\n")
            for label, url in self.YOUTUBE_EMOJI_URLS.items():
                filename = self.YOUTUBE_EMOJIS.get(label)
                if not filename:
                    log_file.write(f"{timestamp} | No filename found for emoji {label} in YOUTUBE_EMOJIS\n")
                    continue
                filepath = os.path.join(self.ytemoji_dir, filename)
                if os.path.exists(filepath):
                    log_file.write(f"{timestamp} | Skipped downloading {label} ({filename} already exists)\n")
                    continue
                try:
                    with urllib.request.urlopen(url) as response:
                        img_data = response.read()
                    with open(filepath, "wb") as f:
                        f.write(img_data)
                    log_file.write(f"{timestamp} | Successfully downloaded {label} to {filepath}\n")
                except Exception as e:
                    log_file.write(f"{timestamp} | Failed to download {label} to {filepath}: {e}\n")

    def download_twitch_emojis(self):
        log_file_path = os.path.join(self.base_path, "download_log.txt")
        with open(log_file_path, "a", encoding="utf-8") as log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"{timestamp} | Starting Twitch emote download check\n")
            for label, url in self.TWITCH_EMOJI_URLS.items():
                filename = self.TWITCH_EMOJIS.get(label)
                if not filename:
                    log_file.write(f"{timestamp} | No filename found for Twitch emote {label}\n")
                    continue
                filepath = os.path.join(self.tvemoji_dir, filename)
                if os.path.exists(filepath):
                    log_file.write(f"{timestamp} | Skipped downloading {label} ({filename} already exists)\n")
                    continue
                try:
                    with urllib.request.urlopen(url) as response:
                        img_data = response.read()
                    with open(filepath, "wb") as f:
                        f.write(img_data)
                    log_file.write(f"{timestamp} | Successfully downloaded {label} to {filepath}\n")
                except Exception as e:
                    log_file.write(f"{timestamp} | Failed to download {label} to {filepath}: {e}\n")

    def load_emoji_image(self, key, is_youtube_emoji=False, is_twitch_emoji=False):
        if key in self.image_cache:
            return self.image_cache[key]
        try:
            if is_youtube_emoji:
                emoji_file = os.path.join(self.ytemoji_dir, key)
            elif is_twitch_emoji:
                emoji_file = os.path.join(self.tvemoji_dir, key)
            else:
                emoji_file = os.path.join(self.emojis_dir, f"{key}.png")
            img = Image.open(emoji_file).resize((20, 20), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.image_cache[key] = photo  # Cache the image
            return photo
        except Exception as e:
            log_file_path = os.path.join(self.base_path, "download_log.txt")
            with open(log_file_path, "a", encoding="utf-8") as log_file:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_file.write(f"{timestamp} | Failed to load emoji image {key}: {e}\n")
            return None

    def add_message(self, platform, user, message):
        icon = self.platform_icons.get(platform, "💬")
        #log_file_path = os.path.join(self.base_path, "twitch_emoji_debug.log")

        if platform == "SYSTEM":
            platform_tag = "system_platform"
            self.text.config(state="normal")  # 啟用編輯
            self.text.insert("end", f"{icon} {message}\n", platform_tag)
            self.text.config(state="disabled")  # 恢復唯讀
        else:
            platform_tag = "youtube_platform" if platform == "YouTube" else "twitch_platform"
            self.text.config(state="normal")  # 啟用編輯
            self.text.insert("end", f"{icon} ", platform_tag)
            self.text.insert("end", f"{user}: ", "user")

            # 處理 YouTube 表情符號和標準表情符號
            pos = 0
            emoji_detected = []
            while pos < len(message):
                # 檢查 YouTube 表情符號
                youtube_emoji_match = None
                for emoji_label in self.YOUTUBE_EMOJIS:
                    if message.startswith(emoji_label, pos):
                        youtube_emoji_match = emoji_label
                        break
                if youtube_emoji_match:
                    photo = self.load_emoji_image(self.YOUTUBE_EMOJIS[youtube_emoji_match], is_youtube_emoji=True)
                    if photo:
                        self.text.image_create("end", image=photo)
                    else:
                        self.text.insert("end", youtube_emoji_match, "text")  # Fallback
                    pos += len(youtube_emoji_match)
                    continue

                # 檢查 Twitch 表情符號
                twitch_emoji_match = None
                for emote_label in self.TWITCH_EMOJIS:
                    if message.startswith(emote_label, pos):
                        twitch_emoji_match = emote_label
                        break
                if twitch_emoji_match:
                    photo = self.load_emoji_image(self.TWITCH_EMOJIS[twitch_emoji_match], is_twitch_emoji=True)
                    if photo:
                        self.text.image_create("end", image=photo)
                        emoji_detected.append((twitch_emoji_match, self.TWITCH_EMOJIS[twitch_emoji_match], "Loaded"))
                    else:
                        self.text.insert("end", twitch_emoji_match, "text")
                        emoji_detected.append((twitch_emoji_match, self.TWITCH_EMOJIS[twitch_emoji_match], "Fallback"))
                    pos += len(twitch_emoji_match)
                    continue

                char = message[pos]
                if emoji.is_emoji(char):
                    unicode_key = "-".join(f"{ord(c):x}" for c in char).lower()
                    photo = self.load_emoji_image(unicode_key, is_youtube_emoji=False)
                    if photo:
                        self.text.image_create("end", image=photo)
                        emoji_detected.append((char, unicode_key, "Loaded"))
                    else:
                        self.text.insert("end", char, "text")  # Fallback to text
                        emoji_detected.append((char, unicode_key, "Fallback"))
                    #if platform == "Twitch":
                        #timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        #DEBUG用 show twitch留言
                        #with open(log_file_path, "a", encoding="utf-8") as log_file:
                            #log_file.write(f"{timestamp} | Twitch Emoji | User: {user} | Char: {char} | Unicode: {unicode_key} | Status: {'Loaded' if photo else 'Fallback'}\n")
                        #print(f"DEBUG: Twitch Emoji | User: {user} | Char: {char} | Unicode: {unicode_key} | Status: {'Loaded' if photo else 'Fallback'}")
                else:
                    self.text.insert("end", char, "text")
                pos += 1

            self.text.insert("end", "\n", "text")
            self.text.config(state="disabled")  # 恢復唯讀

            # DEBUG用 如果檢測到 emoji，記錄完整訊息
            #if platform == "Twitch" and emoji_detected:
                #timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                #with open(log_file_path, "a", encoding="utf-8") as log_file:
                    #log_file.write(f"{timestamp} | Twitch Message | User: {user} | Message: {message} | Emojis: {emoji_detected}\n")
                #print(f"DEBUG: Twitch Message | User: {user} | Message: {message} | Emojis: {emoji_detected}")

        # Only auto-scroll to bottom if auto_scroll is enabled
        if self.auto_scroll:
            self.text.yview_moveto(1)

    def process_queue(self):
        """Process messages from the queue in the main thread."""
        while not self.message_queue.empty():
            try:
                platform, user, message = self.message_queue.get_nowait()
                self.add_message(platform, user, message)
            except queue.Empty:
                break
        self.root.after(100, self.process_queue)  # Check again after 100ms

    def update_status(self, platform, status):
        if platform == "YouTube":
            self.youtube_status.config(text=f"▶ 狀態: {status}")
        elif platform == "Twitch":
            self.twitch_status.config(text=f"🎮 狀態: {status}")

    def start_chat(self):
        if self.running:
            return

        youtube_link = self.youtube_entry.get().strip()
        twitch_link = self.twitch_entry.get().strip()

        self.running = True
        self.start_button.config(state="disabled")
        self.input_frame.pack_forget()  # Hide the input frame

        if youtube_link:
            parsed = urlparse.urlparse(youtube_link)
            video_id = urlparse.parse_qs(parsed.query).get("v")
            if video_id:
                self.youtube_video_id = video_id[0]
                self.youtube_thread = threading.Thread(target=youtube_chat, args=(self.youtube_video_id, self.message_queue, self.update_status), daemon=True)
                self.youtube_thread.start()

        if twitch_link:
            m = re.search(r"twitch.tv/([^/]+)", twitch_link)
            if m:
                self.twitch_channel = m.group(1)
                self.twitch_thread = threading.Thread(target=twitch_chat, args=(self.twitch_channel, self.message_queue, self.update_status), daemon=True)
                self.twitch_thread.start()

    def stop_threads(self):
        self.running = False
        self.start_button.config(state="normal")
        self.input_frame.pack(fill="x", padx=5, pady=5)  # Show the input frame again
        self.youtube_entry.config(state="normal")
        self.twitch_entry.config(state="normal")

# --------------------
# 主程式
# --------------------
def run():
    root = tk.Tk()
    # Set window icon
    try:
        icon_path = os.path.join(get_base_path(), "app.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
        else:
            log_file_path = os.path.join(get_base_path(), "download_log.txt")
            with open(log_file_path, "a", encoding="utf-8") as log_file:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_file.write(f"{timestamp} | Icon file {icon_path} not found\n")
    except Exception as e:
        log_file_path = os.path.join(get_base_path(), "download_log.txt")
        with open(log_file_path, "a", encoding="utf-8") as log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"{timestamp} | Failed to set icon {icon_path}: {e}\n")
    
    app = ChatApp(root)
    root.mainloop()

if __name__ == "__main__":
    run()