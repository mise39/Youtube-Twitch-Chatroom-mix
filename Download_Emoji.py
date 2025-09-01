import os
import re
import ast
import requests
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk

YT_OUTPUT_DIR = "ytemoji"
TWITCH_OUTPUT_DIR = "tvemoji"

def find_files():
    yt_files = [f for f in os.listdir(".") if f.startswith("extra_youtube_") and f.endswith(".txt")]
    twitch_files = [f for f in os.listdir(".") if f.startswith("extra_twitch_") and f.endswith(".txt")]
    return {'yt': yt_files, 'twitch': twitch_files}

def parse_dict_from_file(filename, platform):
    with open(filename, "r", encoding="utf-8") as f:
        text = f.read()
    var_name = "YOUTUBE_EMOJI_URLS" if platform == 'yt' else "TWITCH_EMOJI_URLS"
    match = re.search(rf"{var_name}\s*=\s*({{.*}})", text, re.S)
    if not match:
        raise ValueError(f"檔案 {filename} 格式錯誤，找不到清單")
    return ast.literal_eval(match.group(1))

def download_emojis(log_widget, progress_bar, file_count_label, start_btn):
    files = find_files()
    yt_files = files['yt']
    twitch_files = files['twitch']
    all_files = yt_files + twitch_files
    if not all_files:
        messagebox.showwarning("找不到檔案", "沒有找到 extra_youtube_*.txt 或 extra_twitch_*.txt 檔案")
        start_btn.config(state=tk.NORMAL)
        return
    
    # 計算總數並過濾已下載的
    total = 0
    to_download = []
    for platform, file_list in files.items():
        for file in file_list:
            try:
                emoji_dict = parse_dict_from_file(file, platform)
                output_dir = YT_OUTPUT_DIR if platform == 'yt' else TWITCH_OUTPUT_DIR
                for name, url in emoji_dict.items():
                    clean_name = name.strip(":")
                    ext = os.path.splitext(url)[1] or ".png" if platform == 'yt' else ".png"
                    filename = os.path.join(output_dir, clean_name + ext)
                    if not os.path.exists(filename):
                        to_download.append((platform, file, name, url, clean_name, ext))
                        total += 1
            except Exception as e:
                log_widget.insert(tk.END, f"⚠️ 解析失敗 {file}: {e}\n")
                continue

    if total == 0:
        messagebox.showinfo("無需下載", "所有 Emoji 都已下載！")
        start_btn.config(state=tk.NORMAL)
        return

    progress_bar["maximum"] = total
    file_count_label.config(text=f"合共 {len(all_files)} 個txt，{total} 個待下載 Emoji")

    done = 0

    for platform, file, name, url, clean_name, ext in to_download:
        output_dir = YT_OUTPUT_DIR if platform == 'yt' else TWITCH_OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)
        
        log_widget.insert(tk.END, f"📂 處理 {file} ({platform.upper()})\n")
        
        filename = os.path.join(output_dir, clean_name + ext)
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            with open(filename, "wb") as f:
                f.write(r.content)
            log_widget.insert(tk.END, f"✅ {clean_name}\n")
        except Exception as e:
            log_widget.insert(tk.END, f"❌ {url}: {e}\n")

        done += 1
        progress_bar["value"] = done
        file_count_label.config(text=f"合共 {len(all_files)}個txt，下載中 → {done} / {total} ")
        log_widget.see(tk.END)
        log_widget.update()
        progress_bar.update()

        # 每處理完一個檔案後記錄
        if done == total or (done < total and to_download[done][1] != file):
            log_widget.insert(tk.END, f"--- 完成下載 {file} ---\n\n")

    messagebox.showinfo("完成", "所有檔案下載完成！")
    start_btn.config(state=tk.NORMAL)

def start_download_thread(log_widget, progress_bar, file_count_label, start_btn):
    start_btn.config(state=tk.DISABLED)
    log_widget.delete("1.0", tk.END)
    progress_bar["value"] = 0
    file_count_label.config(text="掃描中...")
    t = threading.Thread(target=download_emojis, args=(log_widget, progress_bar, file_count_label, start_btn))
    t.daemon = True
    t.start()

def main():
    root = tk.Tk()
    root.title("Emoji Downloader (YouTube & Twitch)")

    frm_top = tk.Frame(root)
    frm_top.pack(pady=5)

    start_btn = tk.Button(frm_top, text="開始下載", font=("Microsoft JhengHei", 12))
    start_btn.pack(side=tk.LEFT, padx=10)

    file_count_label = tk.Label(frm_top, text="待機中", font=("Microsoft JhengHei", 10))
    file_count_label.pack(side=tk.LEFT)

    progress_bar = ttk.Progressbar(root, length=500, mode="determinate")
    progress_bar.pack(pady=5)

    log_area = scrolledtext.ScrolledText(root, width=70, height=20, font=("Consolas", 10))
    log_area.pack(padx=10, pady=10)

    start_btn.config(command=lambda: start_download_thread(log_area, progress_bar, file_count_label, start_btn))

    root.mainloop()

if __name__ == "__main__":
    main()