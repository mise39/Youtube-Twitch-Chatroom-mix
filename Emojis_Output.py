import tkinter as tk
from tkinter import ttk, messagebox
from bs4 import BeautifulSoup
import os
from datetime import datetime

def parse_emoji_from_file(file_path, platform):
    """Parse emoji codes and URLs from an HTML file based on the selected platform."""
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Initialize dictionaries
        emojis = {}
        emoji_urls = {}
        
        if platform == "YouTube":
            # Parse YouTube emojis (img tags with role="option")
            for img in soup.find_all('img', {'role': 'option'}):
                code = img.get('aria-label', '').strip()  # Emoji code, e.g., :_museSun:
                src = img.get('src', '').strip()         # Image URL
                if code and src:
                    filename = code.strip(':') + '.png'
                    emojis[code] = filename
                    emoji_urls[code] = src
        elif platform == "Twitch":
            # Parse Twitch emojis (img tags with class containing "emote-picker__")
            for img in soup.find_all('img', attrs={'class': lambda c: c and 'emote-picker__' in c}):
                emote_name = img.get('alt')
                srcset = img.get('srcset')
                emote_url = None
                
                if srcset:
                    # Extract 2.0x URL from srcset
                    urls = [url.split(' ')[0] for url in srcset.split(', ')]
                    emote_url = next((url for url in urls if '2.0' in url), None)
                
                # Fallback to src if no 2.0x URL
                if not emote_url:
                    emote_url = img.get('src')
                
                if emote_name and emote_url:
                    emojis[emote_name] = f'{emote_name}.png'
                    emoji_urls[emote_name] = emote_url
        
        return emojis, emoji_urls, None
    except Exception as e:
        return {}, {}, f"無法分析資料: {str(e)}"

def save_emoji_list(emojis, emoji_urls, platform, output_file=None):
    """Save emoji mappings to a file in the specified format."""
    try:
        # Generate output filename if not provided
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"extra_{platform.lower()}_emojis_{timestamp}.txt"
        
        # Format content
        content = f"# Extra {platform} emojis configuration\n"
        content += "# Emoji_div_to_list(YouTube/Twitch)\n\n"
        
        emoji_dict_name = f"{platform.upper()}_EMOJIS"
        url_dict_name = f"{platform.upper()}_EMOJI_URLS"
        
        content += f"{emoji_dict_name} = {{\n"
        for code, filename in emojis.items():
            content += f'    "{code}": "{filename}",\n'
        content += "}\n\n"
        
        content += f"{url_dict_name} = {{\n"
        for code, url in emoji_urls.items():
            content += f'    "{code}": "{url}",\n'
        content += "}\n"
        
        # Save to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Emoji list saved to {output_file}"
    except Exception as e:
        return f"Failed to save file: {str(e)}"

class EmojiParserApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Emoji_div_to_list(YouTube/Twitch)")
        self.root.geometry("600x200")
        self.root.configure(bg="#1e1e1e")

        # Style
        style = ttk.Style()
        style.theme_use("clam")

        # Input frame
        input_frame = tk.Frame(self.root, bg="#1e1e1e")
        input_frame.pack(fill="x", padx=5, pady=5)

        # File path input
        tk.Label(input_frame, text="檔案名(只限當前目錄):", bg="#1e1e1e", fg="#cdd6f4", font=("Microsoft JhengHei UI", 12)).pack(side="left")
        self.file_entry = tk.Entry(input_frame, width=10, font=("Microsoft JhengHei UI", 12))
        self.file_entry.pack(side="left", padx=5)
        self.file_entry.insert(0, "div.txt")  # Default value

        # Platform selection dropdown
        tk.Label(input_frame, text="平台:", bg="#1e1e1e", fg="#cdd6f4", font=("Microsoft JhengHei UI", 12)).pack(side="left", padx=5)
        self.platform_var = tk.StringVar(value="YouTube")
        platform_menu = ttk.Combobox(input_frame, textvariable=self.platform_var, values=["YouTube", "Twitch"], state="readonly", font=("Microsoft JhengHei UI", 12))
        platform_menu.pack(side="left", padx=1)

        # Confirm button
        self.confirm_button = tk.Button(input_frame, text="確定", command=self.process_file, font=("Microsoft JhengHei UI", 12))
        self.confirm_button.pack(side="left", padx=5)

        # Result display
        self.result_text = tk.Text(self.root, wrap="word", bg="#252526", fg="white", font=("Microsoft JhengHei UI", 12), height=15)
        self.result_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.result_text.config(state="disabled")

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def add_result(self, message):
        """Add a message to the result text area."""
        self.result_text.config(state="normal")
        self.result_text.insert("end", f"{message}\n")
        self.result_text.config(state="disabled")
        self.result_text.yview_moveto(1)  # Scroll to bottom

    def process_file(self):
        """Process the file when the Confirm button is clicked."""
        file_path = self.file_entry.get().strip()
        platform = self.platform_var.get()
        
        if not file_path:
            messagebox.showerror("錯誤", "請到拖移檔案到相同目錄下操作")
            self.add_result(f"錯誤: 檔案不在 {file_path} ")
            return

        if not os.path.exists(file_path):
            messagebox.showerror("錯誤", f"錯誤 {file_path} 不存在")
            self.add_result(f"錯誤: 錯誤 {file_path} 不存在")
            return

        # Parse emoji list
        emojis, emoji_urls, error = parse_emoji_from_file(file_path, platform)

        if error:
            messagebox.showerror("錯誤", error)
            self.add_result(error)
            return

        if not emojis:
            messagebox.showwarning("錯誤", "找不到emoji")
            self.add_result("找不到emoji")
            return

        # Save emoji list
        result = save_emoji_list(emojis, emoji_urls, platform)
        self.add_result(result)

if __name__ == "__main__":
    root = tk.Tk()
    app = EmojiParserApp(root)
    root.mainloop()