import tkinter as tk
from tkinter import ttk
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
            status_callback("YouTube", "已連接")
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

            status_callback("Twitch", "已連接")

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
                            msg = emoji.emojize(match.group(2), language='alias')
                            message_queue.put(("Twitch", user, msg))
        except Exception as e:
            message_queue.put(("Twitch", "SYSTEM", f"錯誤：{e}"))
            status_callback("Twitch", f"錯誤：{e}")
            time.sleep(5)
            continue

# --------------------
# Tkinter GUI
# --------------------
class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Youtube Twitch Chatroom mix")
        self.root.geometry("700x1000")
        self.root.configure(bg="#1e1e1e")

        # Get base path for file operations
        self.base_path = get_base_path()

        # Create emoji directories in the executable's directory
        self.emojis_dir = os.path.join(self.base_path, "emojis")
        self.ytemoji_dir = os.path.join(self.base_path, "ytemoji")
        os.makedirs(self.emojis_dir, exist_ok=True)
        os.makedirs(self.ytemoji_dir, exist_ok=True)

        # Initialize emoji dictionaries
        self.YOUTUBE_EMOJIS = {}
        self.YOUTUBE_EMOJI_URLS = {}
        self.load_emoji_config()

        # Download and unzip emojis.zip and ytemoji.zip if respective folders are empty
        self.download_and_unzip_emojis()

        # Download YouTube emojis and log to emoji_download_log.txt
        self.download_youtube_emojis()

        # Message queue for thread-safe message handling
        self.message_queue = queue.Queue()

        # 樣式
        style = ttk.Style()
        style.theme_use("clam")

        # YouTube 連結輸入框和開始按鈕
        youtube_frame = tk.Frame(root, bg="#1e1e1e")
        youtube_frame.pack(fill="x", padx=5, pady=5)
        tk.Label(youtube_frame, text="Youtube", bg="#1e1e1e", fg="#cdd6f4").pack(side="left")
        self.youtube_entry = tk.Entry(youtube_frame, width=50, font=("Microsoft JhengHei UI", 12))
        self.youtube_entry.pack(side="left", padx=5)
        self.start_button = tk.Button(youtube_frame, text="啟動", command=self.start_chat, font=("Microsoft JhengHei UI", 12))
        self.start_button.pack(side="left", padx=5)

        # Twitch 連結輸入框和手動重連按鈕
        twitch_frame = tk.Frame(root, bg="#1e1e1e")
        twitch_frame.pack(fill="x", padx=5, pady=5)
        tk.Label(twitch_frame, text=" Twitch ", bg="#1e1e1e", fg="#cdd6f4").pack(side="left")
        self.twitch_entry = tk.Entry(twitch_frame, width=50, font=("Microsoft JhengHei UI", 12))
        self.twitch_entry.pack(side="left", padx=5)
        self.reconnect_yt_button = tk.Button(twitch_frame, text="重連YT", command=self.reconnect_youtube, font=("Microsoft JhengHei UI", 12), state="disabled")
        self.reconnect_yt_button.pack(side="left", padx=5)

        # 聊天視窗 (使用 Text 代替 Treeview)
        self.text = tk.Text(root, wrap="word", bg="#252526", fg="white", font=("Microsoft JhengHei UI", 15), height=30)
        self.text.pack(fill="both", expand=True, padx=10, pady=10)
        self.text.config(state="disabled")  # 設為唯讀

        # 配置 Text 標籤樣式
        self.text.tag_configure("youtube_platform", foreground="#ff0000", font=("Microsoft JhengHei UI", 15, "bold"), spacing3=10)
        self.text.tag_configure("twitch_platform", foreground="#9146ff", font=("Microsoft JhengHei UI", 15, "bold"), spacing3=10)
        self.text.tag_configure("user", foreground="#55ff55", font=("Microsoft JhengHei UI", 15, "bold"), spacing3=10)
        self.text.tag_configure("text", foreground="white", font=("Microsoft JhengHei UI", 15), spacing3=10)

        self.scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")

        # 狀態顯示
        status_frame = tk.Frame(root, bg="#1e1e1e")
        status_frame.pack(fill="x", padx=5, pady=5)
        self.youtube_status = tk.Label(status_frame, text="YouTube 狀態: 未連接", bg="#1e1e1e", fg="#cdd6f4", font=("Microsoft JhengHei UI", 12))
        self.youtube_status.pack(side="left", padx=10)
        self.twitch_status = tk.Label(status_frame, text="Twitch 狀態: 未連接", bg="#1e1e1e", fg="#cdd6f4", font=("Microsoft JhengHei UI", 12))
        self.twitch_status.pack(side="left", padx=10)

        self.platform_icons = {"YouTube": "▶", "Twitch": "🎮"}
        self.image_cache = {}  # Cache for emoji images

        self.youtube_thread = None
        self.twitch_thread = None
        self.youtube_video_id = None
        self.twitch_channel = None
        self.running = False

        # Start processing the message queue
        self.process_queue()

    def load_emoji_config(self):
        """Load emoji configurations from emojis.info and extra_*.txt files."""
        # Log file path in the base directory
        log_file_path = os.path.join(self.base_path, "emoji_download_log.txt")

        # Load emojis.info
        emojis_info_path = os.path.join(self.base_path, "emojis.info")
        try:
            with open(emojis_info_path, "r", encoding="utf-8") as f:
                content = f.read()
                local_namespace = {}
                exec(content, {}, local_namespace)
                self.YOUTUBE_EMOJIS.update(local_namespace.get('YOUTUBE_EMOJIS', {}))
                self.YOUTUBE_EMOJI_URLS.update(local_namespace.get('YOUTUBE_EMOJI_URLS', {}))
            with open(log_file_path, "a", encoding="utf-8") as log_file:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_file.write(f"{timestamp} | Successfully loaded emojis.info\n")
        except Exception as e:
            with open(log_file_path, "a", encoding="utf-8") as log_file:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_file.write(f"{timestamp} | Failed to load emojis.info: {e}\n")

        # Load extra_*.txt files
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
                    with open(log_file_path, "a", encoding="utf-8") as log_file:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log_file.write(f"{timestamp} | Successfully loaded {filename}\n")
                except Exception as e:
                    with open(log_file_path, "a", encoding="utf-8") as log_file:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log_file.write(f"{timestamp} | Failed to load {filename}: {e}\n")

    def download_and_unzip_emojis(self):
        """Download and unzip emojis.zip and ytemoji.zip if their respective folders are empty."""
        log_file_path = os.path.join(self.base_path, "emoji_download_log.txt")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file_path, "a", encoding="utf-8") as log_file:
            # Download emojis.zip if 'emojis' folder is empty
            if len(os.listdir(self.emojis_dir)) == 0:
                emojis_zip_url = "https://github.com/mise39/Youtube-Twitch-Chatroom-mix/releases/download/1.0/emojis.zip"
                emojis_zip_path = os.path.join(self.base_path, "emojis.zip")
                log_file.write(f"{timestamp} | Starting download of emojis.zip\n")
                try:
                    with urllib.request.urlopen(emojis_zip_url) as response:
                        zip_data = response.read()
                    with open(emojis_zip_path, "wb") as f:
                        f.write(zip_data)
                    log_file.write(f"{timestamp} | Successfully downloaded emojis.zip\n")

                    # Unzip the file
                    with zipfile.ZipFile(emojis_zip_path, 'r') as zip_ref:
                        zip_ref.extractall(self.emojis_dir)
                    log_file.write(f"{timestamp} | Successfully unzipped emojis.zip to {self.emojis_dir}\n")

                    # Remove the zip file after extraction
                    os.remove(emojis_zip_path)
                except Exception as e:
                    log_file.write(f"{timestamp} | Failed to download or unzip emojis.zip: {e}\n")
            else:
                log_file.write(f"{timestamp} | Skipped downloading emojis.zip ({self.emojis_dir} not empty)\n")

            # Download ytemoji.zip if 'ytemoji' folder is empty
            if len(os.listdir(self.ytemoji_dir)) == 0:
                ytemoji_zip_url = "https://github.com/mise39/Youtube-Twitch-Chatroom-mix/releases/download/1.0/ytemoji.zip"
                ytemoji_zip_path = os.path.join(self.base_path, "ytemoji.zip")
                log_file.write(f"{timestamp} | Starting download of ytemoji.zip\n")
                try:
                    with urllib.request.urlopen(ytemoji_zip_url) as response:
                        zip_data = response.read()
                    with open(ytemoji_zip_path, "wb") as f:
                        f.write(zip_data)
                    log_file.write(f"{timestamp} | Successfully downloaded ytemoji.zip\n")

                    # Unzip the file
                    with zipfile.ZipFile(ytemoji_zip_path, 'r') as zip_ref:
                        zip_ref.extractall(self.ytemoji_dir)
                    log_file.write(f"{timestamp} | Successfully unzipped ytemoji.zip to {self.ytemoji_dir}\n")

                    # Remove the zip file after extraction
                    os.remove(ytemoji_zip_path)
                except Exception as e:
                    log_file.write(f"{timestamp} | Failed to download or unzip ytemoji.zip: {e}\n")
            else:
                log_file.write(f"{timestamp} | Skipped downloading ytemoji.zip ({self.ytemoji_dir} not empty)\n")

    def download_youtube_emojis(self):
        """Download YouTube emojis to ytemoji/ directory if not already present, logging to emoji_download_log.txt."""
        log_file_path = os.path.join(self.base_path, "emoji_download_log.txt")
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

    def load_emoji_image(self, key, is_youtube_emoji=False):
        if key in self.image_cache:
            return self.image_cache[key]
        try:
            if is_youtube_emoji:
                # Load YouTube emoji from ytemoji/ directory
                emoji_file = os.path.join(self.ytemoji_dir, key)
            else:
                # Load Twemoji from emojis/ directory
                emoji_file = os.path.join(self.emojis_dir, f"{key}.png")
            img = Image.open(emoji_file).resize((20, 20), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.image_cache[key] = photo  # Cache the image
            return photo
        except Exception as e:
            log_file_path = os.path.join(self.base_path, "emoji_download_log.txt")
            with open(log_file_path, "a", encoding="utf-8") as log_file:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_file.write(f"{timestamp} | Failed to load emoji image {key}: {e}\n")
            return None

    def add_message(self, platform, user, message):
        icon = self.platform_icons.get(platform, "💬")
        platform_tag = "youtube_platform" if platform == "YouTube" else "twitch_platform"
        self.text.config(state="normal")  # 啟用編輯
        self.text.insert("end", f"{icon} ", platform_tag)
        self.text.insert("end", f"{user}: ", "user")

        # 處理 YouTube 表情符號和標準表情符號
        pos = 0
        while pos < len(message):
            # 檢查 YouTube 表情符號 (e.g., :hand-pink-waving:)
            youtube_emoji_match = None
            for emoji_label in self.YOUTUBE_EMOJIS:
                if message.startswith(emoji_label, pos):
                    youtube_emoji_match = emoji_label
                    break
            if youtube_emoji_match:
                # 插入 YouTube 表情符號圖片
                photo = self.load_emoji_image(self.YOUTUBE_EMOJIS[youtube_emoji_match], is_youtube_emoji=True)
                if photo:
                    self.text.image_create("end", image=photo)
                else:
                    self.text.insert("end", youtube_emoji_match, "text")  # Fallback
                pos += len(youtube_emoji_match)
            else:
                # 檢查標準表情符號
                char = message[pos]
                if emoji.is_emoji(char):
                    # Convert emoji to Unicode filename (e.g., 😊 U+1F600 → 1f600.png)
                    unicode_key = "-".join(f"{ord(c):x}" for c in char if ord(c) >= 0x1000).lower()
                    photo = self.load_emoji_image(unicode_key, is_youtube_emoji=False)
                    if photo:
                        self.text.image_create("end", image=photo)
                    else:
                        self.text.insert("end", char, "text")  # Fallback to text
                else:
                    self.text.insert("end", char, "text")
                pos += 1

        self.text.insert("end", "\n", "text")
        self.text.config(state="disabled")  # 恢復唯讀
        self.text.yview_moveto(1)  # 滾動到最底部

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
            self.youtube_status.config(text=f"YouTube 狀態: {status}")
            if "錯誤" in status:
                self.reconnect_yt_button.config(state="normal")
            else:
                self.reconnect_yt_button.config(state="disabled")
        elif platform == "Twitch":
            self.twitch_status.config(text=f"Twitch 狀態: {status}")

    def start_chat(self):
        if self.running:
            return

        youtube_link = self.youtube_entry.get().strip()
        twitch_link = self.twitch_entry.get().strip()

        self.running = True
        self.start_button.config(state="disabled")
        self.youtube_entry.config(state="disabled")
        self.twitch_entry.config(state="disabled")

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

    def reconnect_youtube(self):
        if self.youtube_video_id and self.running:
            self.youtube_thread = threading.Thread(target=youtube_chat, args=(self.youtube_video_id, self.message_queue, self.update_status), daemon=True)
            self.youtube_thread.start()

    def stop_threads(self):
        self.running = False
        self.start_button.config(state="normal")
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
            log_file_path = os.path.join(get_base_path(), "emoji_download_log.txt")
            with open(log_file_path, "a", encoding="utf-8") as log_file:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_file.write(f"{timestamp} | Icon file {icon_path} not found\n")
    except Exception as e:
        log_file_path = os.path.join(get_base_path(), "emoji_download_log.txt")
        with open(log_file_path, "a", encoding="utf-8") as log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"{timestamp} | Failed to set icon {icon_path}: {e}\n")
    
    app = ChatApp(root)
    root.mainloop()

if __name__ == "__main__":
    run()