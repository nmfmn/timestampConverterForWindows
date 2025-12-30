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

# --- 引入新库 pynput ---
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
        # pynput 的快捷键格式略有不同，例如 '<ctrl>+<alt>+h'
        self.default_config = {"hotkey": "<ctrl>+<alt>+h"}
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

class TimestampTool:
    def __init__(self):
        console_log("=== 专业版程序启动 (pynput内核) ===")
        self.config = ConfigManager()
        self.current_hotkey_str = self.config.data.get("hotkey", "<ctrl>+<alt>+h")
        
        self.root = None
        self.setting_window = None
        
        # 初始化 pynput 的键盘控制器（用于模拟按键）
        self.kb_controller = Controller()
        # 监听器实例
        self.listener = None

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        self.main_app = ctk.CTk()
        self.main_app.withdraw()
        
        # 1. 启动监听
        self.start_listener()
        
        # 2. 开机自启
        self.setup_autostart()
        
        # 3. 托盘
        threading.Thread(target=self.create_tray_icon, daemon=True).start()
        
        console_log(f"=== 监听已就绪: {self.current_hotkey_str} ===")
        
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
        """启动 pynput 全局热键监听"""
        # 如果已有监听器，先停止
        if self.listener:
            try: self.listener.stop()
            except: pass

        try:
            # pynput 的热键注册方式
            # 注意：这里需要把字符串转换成 pynput 识别的格式
            # 我们直接传递包含 callback 的字典
            hotkey_map = {
                self.current_hotkey_str: self.on_hotkey_triggered
            }
            
            self.listener = pynput_kb.GlobalHotKeys(hotkey_map)
            self.listener.start() # 非阻塞启动
            console_log(f"✅ 监听服务已启动: {self.current_hotkey_str}")
        except Exception as e:
            console_log(f"❌ 监听启动失败，可能是快捷键格式错误: {e}")

    def on_hotkey_triggered(self):
        """当快捷键按下时触发（在独立线程中运行）"""
        console_log(">>> 快捷键触发 (pynput)")
        
        # pynput 在独立线程，操作 GUI 必须用 after，
        # 操作逻辑也建议放在主线程或者独立工作线程，防止阻塞监听器
        # 这里我们简单起见，直接执行逻辑，但 UI 操作切回主线程
        self.process_logic()

    def process_logic(self):
        try:
            # --- 1. 强制清空剪切板 ---
            pyperclip.copy("") 
            
            # --- 2. 【关键修复】主动释放干扰按键 ---
            # 因为快捷键是 Ctrl+Alt+H，如果不松开 Alt，
            # 发送 Ctrl+C 会变成 Ctrl+Alt+C (导致复制失败)
            self.kb_controller.release(Key.alt)
            self.kb_controller.release(Key.alt_l)
            self.kb_controller.release(Key.alt_r)
            
            # 如果你的快捷键里包含 Shift，最好也释放一下
            self.kb_controller.release(Key.shift)
            
            # 给系统 0.1 秒反应时间，确保 Alt 状态已清除
            time.sleep(0.1)
            
            # --- 3. 模拟 Ctrl+C ---
            with self.kb_controller.pressed(Key.ctrl):
                self.kb_controller.tap('c')
            
            # --- 4. 智能等待 (Retry Loop) ---
            content = ""
            for _ in range(10): # 尝试 10 次
                time.sleep(0.05)
                content = pyperclip.paste()
                if content: 
                    break
            
            # --- 5. 结果判断 ---
            if not content:
                console_log("剪切板为空 (可能是权限不足，请尝试以管理员运行)")
                return 

            # --- 6. 转换并显示 ---
            result_text, is_success = self.extract_and_convert(content)
            self.main_app.after(0, lambda: self.show_popup_ui(result_text, is_success))
            
        except Exception as e:
            console_log(f"处理错误: {e}")

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

    # --- UI 部分 (基本保持不变) ---
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
            
        final_x = mouse_x + 15
        final_y = mouse_y + 15
        # 省略边界检测代码，逻辑同前...
        self.root.geometry(f'{w}x{h}+{final_x}+{final_y}')
        
        self.root.after(400, lambda: self.root.bind("<FocusOut>", lambda e: self.root.destroy()))
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<Return>", lambda e: self.copy_and_close(result_text))

        frame = ctk.CTkFrame(self.root, fg_color=("gray95", "gray15"), corner_radius=10)
        frame.pack(fill="both", expand=True, padx=1, pady=1)
        
        color = ("#1a1a1a", "#ffffff") if is_success else "#D03030"
        ctk.CTkLabel(frame, text=result_text, font=("Consolas", 15, "bold"), text_color=color).pack(pady=(15, 2))
        hint = "按 Enter 复制" if is_success else "未识别到时间戳"
        ctk.CTkLabel(frame, text=hint, font=("Microsoft YaHei UI", 10), text_color="gray").pack()

        self.root.after(50, self.root.focus_force)
        self.root.after(50, self.root.lift)

    def copy_and_close(self, text):
        pyperclip.copy(text)
        if self.root:
            self.root.destroy()
            self.root = None

    # --- 托盘 & 设置 ---
    def create_tray_icon(self):
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), "#0078D4")
        d = ImageDraw.Draw(image)
        d.rectangle((16, 16, 48, 48), fill="white")
        
        menu = pystray.Menu(
            pystray.MenuItem("设置快捷键", self.open_settings_safe),
            pystray.MenuItem("退出", self.quit_app)
        )
        self.icon = pystray.Icon("TimestampTool", image, "时间戳助手", menu)
        self.icon.run()

    def open_settings_safe(self, icon=None, item=None):
        self.main_app.after(0, self.show_settings_ui)

    def quit_app(self, icon=None, item=None):
        self.icon.stop()
        if self.listener: self.listener.stop()
        self.main_app.quit()
        os._exit(0)

    def show_settings_ui(self):
        if self.setting_window and self.setting_window.winfo_exists():
            self.setting_window.focus(); return

        self.setting_window = ctk.CTkToplevel(self.main_app)
        self.setting_window.title("设置")
        self.setting_window.geometry("300x200")
        
        # 居中逻辑省略...
        self.setting_window.attributes('-topmost', True)

        frame = ctk.CTkFrame(self.setting_window)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="修改快捷键 (pynput格式)", font=("Microsoft YaHei UI", 12, "bold")).pack(pady=5)
        ctk.CTkLabel(frame, text="格式示例: <ctrl>+<alt>+h", font=("Consolas", 10), text_color="gray").pack()
        
        entry = ctk.CTkEntry(frame, placeholder_text=self.current_hotkey_str)
        entry.insert(0, self.current_hotkey_str)
        entry.pack(pady=10, fill="x")

        def save_hotkey():
            new_key = entry.get().strip().lower()
            if new_key:
                try:
                    # 验证格式是否正确
                    # pynput 解析格式比较严格，例如 ctrl 必须写成 <ctrl>
                    self.current_hotkey_str = new_key
                    self.config.save_config("hotkey", new_key)
                    
                    # 重启监听器
                    self.start_listener()
                    self.setting_window.destroy()
                except Exception as e:
                    print(e)
                    entry.configure(border_color="red")
            
        ctk.CTkButton(frame, text="保存生效", command=save_hotkey).pack(pady=10)

if __name__ == "__main__":
    TimestampTool()