import customtkinter as ctk
import keyboard
import time
import pyperclip
import threading
import os
import sys
import winreg
import json
import re
import traceback
from datetime import datetime
from PIL import Image, ImageDraw
import pystray

# --- 日志 / 控制台输出配置 ---
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def console_log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")

# --- 高分屏适配 ---
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

# --- 配置管理类 ---
class ConfigManager:
    def __init__(self):
        self.config_file = "config.json"
        self.default_config = {"hotkey": "ctrl+alt+h"}
        self.data = self.load_config()

    def get_executable_dir(self):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def get_config_path(self):
        return os.path.join(self.get_executable_dir(), self.config_file)

    def load_config(self):
        path = self.get_config_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data if "hotkey" in data else self.default_config
            except:
                return self.default_config
        return self.default_config

    def save_config(self, key, value):
        self.data[key] = value
        try:
            with open(self.get_config_path(), 'w', encoding='utf-8') as f:
                json.dump(self.data, f)
        except:
            pass

# --- 主程序类 ---
class TimestampTool:
    def __init__(self):
        console_log("=== 程序正在启动 ===")
        self.config = ConfigManager()
        self.current_hotkey = self.config.data.get("hotkey", "ctrl+alt+h")
        self.root = None
        self.setting_window = None
        
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        self.main_app = ctk.CTk()
        self.main_app.withdraw()
        
        # 1. 注册热键
        self.register_hotkey()
        
        # 2. 设置开机自启
        self.setup_autostart()
        
        # 3. 启动托盘
        threading.Thread(target=self.create_tray_icon, daemon=True).start()
        
        # 4. 【新增】启动心跳保活线程
        threading.Thread(target=self.start_heartbeat, daemon=True).start()
        
        console_log(f"=== 初始化完成，监听中: {self.current_hotkey} ===")
        
        self.main_app.mainloop()

    def get_executable_path(self):
        if getattr(sys, 'frozen', False):
            return sys.executable
        return os.path.abspath(__file__)

    def setup_autostart(self):
        try:
            key = "TimestampConverter"
            exe_path = self.get_executable_path()
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(reg_key, key, 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(reg_key)
        except Exception:
            pass

    def register_hotkey(self):
        """注册热键的核心逻辑"""
        try:
            # 先尝试移除所有，防止重复堆叠
            try:
                keyboard.unhook_all_hotkeys()
            except:
                pass
            
            # 重新注册
            keyboard.add_hotkey(self.current_hotkey, self.process_hotkey)
            console_log(f"✅ 热键已(重新)挂载: {self.current_hotkey}")
        except Exception as e:
            console_log(f"❌ 热键挂载失败: {e}")

    # --- 【新增】心跳保活机制 ---
    def start_heartbeat(self):
        """
        每隔 5 分钟醒来一次，强制重新注册一遍快捷键。
        这能有效防止 Windows 因为长时间无响应而把钩子丢掉。
        """
        while True:
            # 300秒 = 5分钟
            time.sleep(300) 
            console_log("❤️ 执行心跳保活：刷新快捷键钩子...")
            
            # 在子线程调用主逻辑通常不安全，但 keyboard 库是线程独立的，
            # 只要不涉及 UI 操作，这里直接重新注册是安全的。
            self.register_hotkey()

    def create_tray_icon(self):
        width = 64
        height = 64
        color1 = "#0078D4"
        color2 = "#FFFFFF"
        image = Image.new('RGB', (width, height), color1)
        d = ImageDraw.Draw(image)
        d.ellipse((8, 8, 56, 56), outline=color2, width=4)
        d.line((32, 32, 32, 16), fill=color2, width=4)
        d.line((32, 32, 44, 32), fill=color2, width=4)
        
        menu = pystray.Menu(
            pystray.MenuItem("设置快捷键", self.open_settings_safe),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self.quit_app)
        )
        self.icon = pystray.Icon("TimestampTool", image, "时间戳助手", menu)
        self.icon.run()

    def open_settings_safe(self, icon=None, item=None):
        self.main_app.after(0, self.show_settings_ui)

    def quit_app(self, icon=None, item=None):
        self.icon.stop()
        self.main_app.quit()
        os._exit(0)

    def extract_and_convert(self, text):
        if not text: return "剪切板为空", False
        match = re.search(r'\b\d{10,13}\b', text)
        if match:
            raw_ts = match.group(0)
        else:
            raw_ts = text.strip()

        try:
            ts = float(raw_ts)
            if ts > 100000000000: ts = ts / 1000.0
            dt = datetime.fromtimestamp(ts)
            return dt.strftime("%Y-%m-%d %H:%M:%S"), True
        except:
            return f"非时间戳: {text[:10]}...", False

    def process_hotkey(self):
        console_log(">>> 触发快捷键")
        try:
            # 1. 释放按键
            keys = self.current_hotkey.replace(' ', '').split('+')
            for k in keys: keyboard.release(k)
            time.sleep(0.05)

            # 2. 复制 (增加容错)
            old_clip = pyperclip.paste()
            keyboard.send('ctrl+c')
            
            # 循环等待剪切板更新，最多等待 0.4 秒
            for _ in range(4):
                time.sleep(0.1)
                if pyperclip.paste() != old_clip:
                    break
            
            content = pyperclip.paste()
            
            # 3. 转换 & 弹窗
            result_text, is_success = self.extract_and_convert(content)
            self.main_app.after(0, lambda: self.show_popup_ui(result_text, is_success))

        except Exception as e:
            console_log(f"❌ 运行错误: {traceback.format_exc()}")
            # 如果出错，尝试立即重置一次钩子，防止下次也挂掉
            self.register_hotkey()

    def show_popup_ui(self, result_text, is_success):
        if self.root:
            try: self.root.destroy()
            except: pass

        self.root = ctk.CTkToplevel(self.main_app)
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        
        w, h = 260, 75
        try:
            mouse_x = self.root.winfo_pointerx()
            mouse_y = self.root.winfo_pointery()
        except:
            mouse_x, mouse_y = 500, 500
            
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        
        final_x = mouse_x + 15
        final_y = mouse_y + 15
        if final_x + w > screen_w: final_x = mouse_x - w - 10
        if final_y + h > screen_h: final_y = mouse_y - h - 10
        
        self.root.geometry(f'{w}x{h}+{final_x}+{final_y}')
        
        self.root.after(400, lambda: self.root.bind("<FocusOut>", lambda e: self.root.destroy()))
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<Return>", lambda e: self.copy_and_close(result_text))

        frame = ctk.CTkFrame(self.root, fg_color=("gray95", "gray15"), corner_radius=10)
        frame.pack(fill="both", expand=True, padx=1, pady=1)
        
        color = ("#1a1a1a", "#ffffff") if is_success else "#D03030"
        lbl = ctk.CTkLabel(frame, text=result_text, font=("Consolas", 15, "bold"), text_color=color)
        lbl.pack(pady=(15, 2))

        hint = "按 Enter 复制" if is_success else "未识别到时间戳"
        ctk.CTkLabel(frame, text=hint, font=("Microsoft YaHei UI", 10), text_color="gray").pack()

        self.root.after(50, self.root.focus_force)
        self.root.after(50, self.root.lift)

    def copy_and_close(self, text):
        pyperclip.copy(text)
        if self.root:
            self.root.destroy()
            self.root = None

    def show_settings_ui(self):
        if self.setting_window and self.setting_window.winfo_exists():
            self.setting_window.focus(); return

        self.setting_window = ctk.CTkToplevel(self.main_app)
        self.setting_window.title("设置")
        self.setting_window.geometry("300x180")
        
        ws = self.setting_window.winfo_screenwidth()
        hs = self.setting_window.winfo_screenheight()
        x = (ws/2) - 150
        y = (hs/2) - 90
        self.setting_window.geometry(f'+{int(x)}+{int(y)}')
        
        self.setting_window.attributes('-topmost', True)
        self.setting_window.focus_force()

        frame = ctk.CTkFrame(self.setting_window)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="修改快捷键", font=("Microsoft YaHei UI", 12, "bold")).pack(pady=5)
        entry = ctk.CTkEntry(frame, placeholder_text=self.current_hotkey)
        entry.insert(0, self.current_hotkey)
        entry.pack(pady=10, fill="x")

        def save_hotkey():
            new_key = entry.get().strip().lower()
            if new_key:
                try:
                    self.current_hotkey = new_key
                    self.config.save_config("hotkey", new_key)
                    self.register_hotkey() # 这里的重新注册也会重置心跳的目标
                    self.setting_window.destroy()
                except Exception:
                    entry.configure(border_color="red")
            
        ctk.CTkButton(frame, text="保存生效", command=save_hotkey).pack(pady=10)

if __name__ == "__main__":
    TimestampTool()