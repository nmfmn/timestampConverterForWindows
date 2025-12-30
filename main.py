import customtkinter as ctk
import time
import pyperclip
import threading
import os
import sys
import winreg
import json
import re
from datetime import datetime
from PIL import Image, ImageDraw
import pystray
import pytz  # --- 新增依赖 ---

# --- 引入 pynput ---
from pynput import keyboard as pynput_kb
from pynput.keyboard import Key, Controller

# --- 控制台日志 ---
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

class ConfigManager:
    def __init__(self):
        self.config_file = "config.json"
        # 默认增加 timezone 字段，默认值为 "Local"
        self.default_config = {
            "hotkey": "<ctrl>+<alt>+h", 
            "timezone": "Local" 
        }
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
                    # 补全可能缺失的字段
                    for k, v in self.default_config.items():
                        if k not in data:
                            data[k] = v
                    return data
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

class TimestampTool:
    def __init__(self):
        console_log("=== 时间戳工具 (时区增强版) 启动 ===")
        self.config = ConfigManager()
        self.current_hotkey_str = self.config.data.get("hotkey", "<ctrl>+<alt>+h")
        self.current_timezone = self.config.data.get("timezone", "Local")
        
        self.root = None
        self.setting_window = None
        self.timezone_window = None # 时区设置窗口
        
        self.kb_controller = Controller()
        self.listener = None

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        self.main_app = ctk.CTk()
        self.main_app.withdraw()
        
        self.start_listener()
        self.setup_autostart()
        
        threading.Thread(target=self.create_tray_icon, daemon=True).start()
        
        console_log(f"监听: {self.current_hotkey_str} | 时区: {self.current_timezone}")
        
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
        except:
            pass

    def start_listener(self):
        if self.listener:
            try: self.listener.stop()
            except: pass

        try:
            hotkey_map = { self.current_hotkey_str: self.on_hotkey_triggered }
            self.listener = pynput_kb.GlobalHotKeys(hotkey_map)
            self.listener.start()
            console_log(f"✅ 监听器已启动")
        except Exception as e:
            console_log(f"❌ 监听启动失败: {e}")

    def on_hotkey_triggered(self):
        console_log(">>> 快捷键触发")
        self.process_logic()

    def process_logic(self):
        try:
            # 1. 强制清空
            pyperclip.copy("") 
            
            # 2. 释放可能干扰的修饰键 (Alt, Shift)
            self.kb_controller.release(Key.alt)
            self.kb_controller.release(Key.alt_l)
            self.kb_controller.release(Key.alt_r)
            self.kb_controller.release(Key.shift)
            time.sleep(0.1)
            
            # 3. 模拟 Ctrl+C
            with self.kb_controller.pressed(Key.ctrl):
                self.kb_controller.tap('c')
            
            # 4. 智能等待
            content = ""
            for _ in range(10):
                time.sleep(0.05)
                content = pyperclip.paste()
                if content: break
            
            if not content:
                console_log("剪切板为空")
                return 

            # 5. 转换并显示
            result_text, is_success = self.extract_and_convert(content)
            self.main_app.after(0, lambda: self.show_popup_ui(result_text, is_success))
            
        except Exception as e:
            console_log(f"❌ 处理错误: {e}")

    def extract_and_convert(self, text):
        if not text: return "内容为空", False
        
        match = re.search(r'(\d{10,13}(?:\.\d+)?)', text)
        if match:
            raw_ts = match.group(1)
        else:
            raw_ts = re.sub(r'[^\d.]', '', text)

        try:
            ts = float(raw_ts)
            if ts > 100000000000: ts = ts / 1000.0
            
            if ts < 0 or ts > 32503680000:
                 return f"数值越界: {raw_ts[:10]}...", False

            # --- 时区处理逻辑 ---
            if self.current_timezone == "Local":
                # 跟随系统本地时间
                dt = datetime.fromtimestamp(ts)
            else:
                # 指定时区
                try:
                    target_tz = pytz.timezone(self.current_timezone)
                    dt = datetime.fromtimestamp(ts, target_tz)
                except:
                    # 如果时区名有误，回退到本地
                    dt = datetime.fromtimestamp(ts)
            # --------------------

            return dt.strftime("%Y-%m-%d %H:%M:%S"), True
        except:
            return f"非时间戳: {text[:15]}...", False

    # --- UI: 结果弹窗 ---
    def show_popup_ui(self, result_text, is_success):
        if self.root:
            try: self.root.destroy()
            except: pass

        self.root = ctk.CTkToplevel(self.main_app)
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        
        w, h = 260, 80
        try:
            mouse_x = self.root.winfo_pointerx()
            mouse_y = self.root.winfo_pointery()
        except:
            mouse_x, mouse_y = 500, 500
            
        final_x = mouse_x + 15
        final_y = mouse_y + 15
        
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        if final_x + w > screen_w: final_x = mouse_x - w - 10
        if final_y + h > screen_h: final_y = mouse_y - h - 10

        self.root.geometry(f'{w}x{h}+{final_x}+{final_y}')
        
        self.root.after(400, lambda: self.root.bind("<FocusOut>", lambda e: self.root.destroy()))
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<Return>", lambda e: self.copy_and_close(result_text))

        frame = ctk.CTkFrame(self.root, fg_color=("gray95", "gray15"), corner_radius=10)
        frame.pack(fill="both", expand=True, padx=1, pady=1)
        
        color = ("#1a1a1a", "#ffffff") if is_success else "#D03030"
        
        # 显示结果
        lbl = ctk.CTkLabel(frame, text=result_text, font=("Consolas", 15, "bold"), text_color=color)
        lbl.pack(pady=(12, 0))

        # 显示当前时区的小字
        tz_display = "本地时间" if self.current_timezone == "Local" else self.current_timezone
        ctk.CTkLabel(frame, text=f"({tz_display}) 按 Enter 复制", font=("Microsoft YaHei UI", 10), text_color="gray").pack()

        self.root.after(50, self.root.focus_force)
        self.root.after(50, self.root.lift)

    def copy_and_close(self, text):
        pyperclip.copy(text)
        if self.root:
            self.root.destroy()
            self.root = None

    # --- 托盘 & 菜单 ---
    def create_tray_icon(self):
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), "#0078D4")
        d = ImageDraw.Draw(image)
        d.rectangle((16, 16, 48, 48), fill="white")
        
        menu = pystray.Menu(
            pystray.MenuItem("修改时区 (Timezone)", self.open_timezone_safe), # 新增菜单
            pystray.MenuItem("设置快捷键 (Hotkey)", self.open_settings_safe),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出 (Exit)", self.quit_app)
        )
        self.icon = pystray.Icon("TimestampTool", image, "时间戳助手", menu)
        self.icon.run()

    def open_settings_safe(self, icon=None, item=None):
        self.main_app.after(0, self.show_settings_ui)

    def open_timezone_safe(self, icon=None, item=None):
        self.main_app.after(0, self.show_timezone_ui)

    def quit_app(self, icon=None, item=None):
        self.icon.stop()
        if self.listener: self.listener.stop()
        self.main_app.quit()
        os._exit(0)

    # --- 界面：设置快捷键 ---
    def show_settings_ui(self):
        if self.setting_window and self.setting_window.winfo_exists():
            self.setting_window.focus(); return

        self.setting_window = ctk.CTkToplevel(self.main_app)
        self.setting_window.title("设置快捷键")
        self.setting_window.geometry("300x180")
        
        ws = self.setting_window.winfo_screenwidth()
        hs = self.setting_window.winfo_screenheight()
        self.setting_window.geometry(f'+{int(ws/2-150)}+{int(hs/2-90)}')
        self.setting_window.attributes('-topmost', True)

        frame = ctk.CTkFrame(self.setting_window)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="修改快捷键", font=("Microsoft YaHei UI", 12, "bold")).pack(pady=5)
        entry = ctk.CTkEntry(frame, placeholder_text=self.current_hotkey_str)
        entry.insert(0, self.current_hotkey_str)
        entry.pack(pady=10, fill="x")

        def save_hotkey():
            new_key = entry.get().strip().lower()
            if new_key:
                try:
                    self.current_hotkey_str = new_key
                    self.config.save_config("hotkey", new_key)
                    self.start_listener()
                    self.setting_window.destroy()
                except:
                    entry.configure(border_color="red")
            
        ctk.CTkButton(frame, text="保存", command=save_hotkey).pack(pady=10)

    # --- 界面：设置时区 ---
    def show_timezone_ui(self):
        if self.timezone_window and self.timezone_window.winfo_exists():
            self.timezone_window.focus(); return

        self.timezone_window = ctk.CTkToplevel(self.main_app)
        self.timezone_window.title("选择时区")
        self.timezone_window.geometry("300x240")
        
        ws = self.timezone_window.winfo_screenwidth()
        hs = self.timezone_window.winfo_screenheight()
        self.timezone_window.geometry(f'+{int(ws/2-150)}+{int(hs/2-120)}')
        self.timezone_window.attributes('-topmost', True)

        frame = ctk.CTkFrame(self.timezone_window)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="选择转换目标时区", font=("Microsoft YaHei UI", 12, "bold")).pack(pady=(5, 10))

        # 准备时区列表：常用时区置顶
        common_tz = ["Local", "UTC", "Asia/Shanghai", "Asia/Tokyo", "America/New_York", "America/Los_Angeles", "Europe/London"]
        all_tz = pytz.common_timezones
        # 合并列表并去重
        tz_list = common_tz + [tz for tz in all_tz if tz not in common_tz]

        # 创建下拉框
        combo = ctk.CTkComboBox(frame, values=tz_list, width=220, height=35)
        combo.set(self.current_timezone)
        combo.pack(pady=10)

        def save_timezone():
            selected = combo.get()
            self.current_timezone = selected
            self.config.save_config("timezone", selected)
            self.timezone_window.destroy()
            console_log(f"时区已更新为: {selected}")
            
        ctk.CTkButton(frame, text="保存设置", command=save_timezone).pack(pady=20)

if __name__ == "__main__":
    TimestampTool()