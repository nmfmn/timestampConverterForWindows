import customtkinter as ctk
import time
import pyperclip
import threading
import os
import sys
import winreg
import json
import re
import webbrowser # --- 新增: 浏览器控制 ---
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse # --- 新增: URL处理 ---
from datetime import datetime
from PIL import Image, ImageDraw
import pystray
import pytz

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
        # 默认配置增加 trace 相关配置
        self.default_config = {
            "time_hotkey": "<ctrl>+<alt>+h",
            "json_hotkey": "<ctrl>+<alt>+j",
            "trace_hotkey": "<ctrl>+<alt>+k", # 新快捷键
            "timezone": "Local",
            # Trace 默认配置 (示例)
            "trace_url": "https://www.google.com/search", 
            "trace_key": "q",           # traceId 对应的参数名
            "time_key": "startTime"     # 开始时间 对应的参数名
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
        console_log("=== DevTools Pro v4.0 启动 ===")
        self.config = ConfigManager()
        
        # 读取配置
        self.time_hotkey = self.config.data.get("time_hotkey", "<ctrl>+<alt>+h")
        self.json_hotkey = self.config.data.get("json_hotkey", "<ctrl>+<alt>+j")
        self.trace_hotkey = self.config.data.get("trace_hotkey", "<ctrl>+<alt>+k")
        self.current_timezone = self.config.data.get("timezone", "Local")
        
        # Trace 配置
        self.trace_url = self.config.data.get("trace_url", "")
        self.trace_key = self.config.data.get("trace_key", "traceId")
        self.time_key = self.config.data.get("time_key", "startTime")
        
        self.root = None
        self.setting_window = None
        self.timezone_window = None
        self.trace_config_window = None
        
        self.kb_controller = Controller()
        self.listener = None

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        self.main_app = ctk.CTk()
        self.main_app.withdraw()
        
        self.start_listener()
        self.setup_autostart()
        
        threading.Thread(target=self.create_tray_icon, daemon=True).start()
        
        console_log(f"监听 Time:{self.time_hotkey} | JSON:{self.json_hotkey} | Trace:{self.trace_hotkey}")
        
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
            # 注册三个快捷键
            hotkey_map = {
                self.time_hotkey: lambda: self.dispatch_action("time"),
                self.json_hotkey: lambda: self.dispatch_action("json"),
                self.trace_hotkey: lambda: self.dispatch_action("trace") # 新增
            }
            self.listener = pynput_kb.GlobalHotKeys(hotkey_map)
            self.listener.start()
            console_log(f"✅ 监听器已更新")
        except Exception as e:
            console_log(f"❌ 监听启动失败: {e}")

    def dispatch_action(self, action_type):
        console_log(f">>> 触发动作: {action_type}")
        self.perform_copy_and_process(action_type)

    def perform_copy_and_process(self, action_type):
        try:
            # 1. 强制清空
            pyperclip.copy("") 
            
            # 2. 释放干扰键
            self.kb_controller.release(Key.alt)
            self.kb_controller.release(Key.alt_l)
            self.kb_controller.release(Key.alt_r)
            self.kb_controller.release(Key.shift)
            self.kb_controller.release(Key.ctrl) # 有些组合键可能需要释放Ctrl
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

            # 5. 分发处理
            if action_type == "time":
                result, success = self.process_timestamp(content)
                self.main_app.after(0, lambda: self.show_time_ui(result, success))
            elif action_type == "json":
                result, success = self.process_json(content)
                self.main_app.after(0, lambda: self.show_json_ui(result, success))
            elif action_type == "trace":
                # Trace 逻辑直接在后台打开浏览器，不需要弹窗显示结果，
                # 但如果打开失败或者配置没填，可以弹窗提示
                self.process_trace(content)
            
        except Exception as e:
            console_log(f"❌ 处理错误: {e}")

    # --- 逻辑：Trace 跳转 (新增) ---
    def process_trace(self, text):
        # 原始文本清理
        text = text.strip()
        
        if not self.trace_url:
            self.main_app.after(0, lambda: self.show_time_ui("未配置 Trace URL", False))
            return

        try:
            # 1. 准备基础 URL
            url_parts = list(urlparse(self.trace_url))
            query = parse_qs(url_parts[4])

            # --- 【关键修改】深度清洗 TraceId ---
            # 第一步：去除字符串内部的所有空白字符（防止跨行选中）
            clean_trace_id = re.sub(r'\s+', '', text)
            
            # 第二步：去除首尾的 英文引号、单引号、逗号、冒号、分号
            # 这样哪怕你双击选中了 "traceId", 也能清理干净
            clean_trace_id = clean_trace_id.strip('"\' ,:;')
            # ----------------------------------

            # 2. 添加 TraceId 参数
            query[self.trace_key] = clean_trace_id

            # 3. 添加时间参数 (当前时间 - 15分钟)
            if self.time_key:
                now_ts = time.time()
                start_ts_sec = now_ts - (15 * 60) # 15分钟前
                
                # 默认生成毫秒级时间戳 (如需秒级，去掉 * 1000 即可)
                start_ts_ms = int(start_ts_sec * 1000)
                
                query[self.time_key] = start_ts_ms

            # 4. 重新构建 URL
            url_parts[4] = urlencode(query, doseq=True)
            final_url = urlunparse(url_parts)
            
            console_log(f"打开网页: {final_url}")
            
            # 5. 调用系统默认浏览器打开
            webbrowser.open(final_url)
            
        except Exception as e:
            console_log(f"Trace 跳转失败: {e}")
            self.main_app.after(0, lambda: self.show_time_ui("链接生成失败", False))

    # --- 逻辑：时间戳 ---
    def process_timestamp(self, text):
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

            if self.current_timezone == "Local":
                dt = datetime.fromtimestamp(ts)
            else:
                try:
                    target_tz = pytz.timezone(self.current_timezone)
                    dt = datetime.fromtimestamp(ts, target_tz)
                except:
                    dt = datetime.fromtimestamp(ts)

            return dt.strftime("%Y-%m-%d %H:%M:%S"), True
        except:
            return f"非时间戳: {text[:15]}...", False

    # --- 逻辑：JSON ---
    def process_json(self, text):
        try:
            text = text.strip()
            parsed = json.loads(text)
            formatted = json.dumps(parsed, indent=4, ensure_ascii=False)
            return formatted, True
        except json.JSONDecodeError as e:
            return f"JSON 解析失败:\n{e}\n\n原始内容:\n{text[:100]}...", False
        except Exception as e:
            return f"未知错误:\n{e}", False

    # --- UI: 弹窗方法 ---
    def _create_popup_window(self, w, h, auto_close=True):
        if self.root:
            try: self.root.destroy()
            except: pass

        self.root = ctk.CTkToplevel(self.main_app)
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        
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
        if final_y < 0: final_y = 10
        
        self.root.geometry(f'{w}x{h}+{final_x}+{final_y}')
        
        if auto_close:
            self.root.after(400, lambda: self.root.bind("<FocusOut>", lambda e: self.root.destroy()))
        
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.after(50, self.root.focus_force)
        self.root.after(50, self.root.lift)

    def show_time_ui(self, result_text, is_success):
        self._create_popup_window(260, 80, auto_close=True)
        frame = ctk.CTkFrame(self.root, fg_color=("gray95", "gray15"), corner_radius=10)
        frame.pack(fill="both", expand=True, padx=1, pady=1)
        color = ("#1a1a1a", "#ffffff") if is_success else "#D03030"
        lbl = ctk.CTkLabel(frame, text=result_text, font=("Consolas", 15, "bold"), text_color=color)
        lbl.pack(pady=(12, 0))
        tz_display = "Local" if self.current_timezone == "Local" else self.current_timezone
        ctk.CTkLabel(frame, text=f"({tz_display}) 按 Enter 复制", font=("Microsoft YaHei UI", 10), text_color="gray").pack()
        self.root.bind("<Return>", lambda e: self.copy_and_close(result_text))

    def show_json_ui(self, result_text, is_success):
        self._create_popup_window(500, 400, auto_close=False)
        frame = ctk.CTkFrame(self.root, fg_color=("gray95", "gray15"), corner_radius=10)
        frame.pack(fill="both", expand=True, padx=1, pady=1)

        title_frame = ctk.CTkFrame(frame, fg_color="transparent", height=30)
        title_frame.pack(fill="x", padx=10, pady=(5,0))
        title_text = "JSON 格式化成功" if is_success else "格式化失败"
        title_color = "#107C10" if is_success else "#D03030"
        ctk.CTkLabel(title_frame, text=title_text, font=("Microsoft YaHei UI", 12, "bold"), text_color=title_color).pack(side="left")
        ctk.CTkLabel(title_frame, text="按 Esc 关闭", font=("Microsoft YaHei UI", 10), text_color="gray").pack(side="right")

        textbox = ctk.CTkTextbox(frame, width=480, height=300, font=("Consolas", 11), activate_scrollbars=True)
        textbox.pack(fill="both", expand=True, padx=10, pady=5)
        textbox.insert("0.0", result_text)
        textbox.configure(state="normal") 

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        if is_success:
            ctk.CTkButton(btn_frame, text="复制全部并关闭 (Enter)", height=28, command=lambda: self.copy_and_close(result_text)).pack(fill="x")
            self.root.bind("<Return>", lambda e: self.copy_and_close(result_text))
        else:
            ctk.CTkButton(btn_frame, text="关闭", height=28, fg_color="#D03030", hover_color="#B02020", command=lambda: self.root.destroy()).pack(fill="x")

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
        d.text((22, 20), "T", fill="#0078D4")
        
        menu = pystray.Menu(
            pystray.MenuItem("修改时区 (Timezone)", self.open_timezone_safe),
            pystray.MenuItem("配置 Trace 链接 (New)", self.open_trace_config_safe), # 新增
            pystray.MenuItem("设置快捷键", self.open_settings_safe),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self.quit_app)
        )
        self.icon = pystray.Icon("DevTool", image, "开发助手", menu)
        self.icon.run()

    def open_settings_safe(self, icon=None, item=None):
        self.main_app.after(0, self.show_settings_ui)
    def open_timezone_safe(self, icon=None, item=None):
        self.main_app.after(0, self.show_timezone_ui)
    def open_trace_config_safe(self, icon=None, item=None):
        self.main_app.after(0, self.show_trace_config_ui)

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
        self.setting_window.geometry("340x300")
        
        ws = self.setting_window.winfo_screenwidth()
        hs = self.setting_window.winfo_screenheight()
        self.setting_window.geometry(f'+{int(ws/2-170)}+{int(hs/2-150)}')
        self.setting_window.attributes('-topmost', True)

        frame = ctk.CTkFrame(self.setting_window)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="快捷键配置 (pynput格式)", font=("Microsoft YaHei UI", 12, "bold")).pack(pady=5)
        
        # 时间戳
        ctk.CTkLabel(frame, text="时间戳转换:", anchor="w").pack(fill="x", pady=(5,0))
        entry_time = ctk.CTkEntry(frame)
        entry_time.insert(0, self.time_hotkey)
        entry_time.pack(fill="x", pady=2)

        # JSON
        ctk.CTkLabel(frame, text="JSON 格式化:", anchor="w").pack(fill="x", pady=(5,0))
        entry_json = ctk.CTkEntry(frame)
        entry_json.insert(0, self.json_hotkey)
        entry_json.pack(fill="x", pady=2)

        # Trace
        ctk.CTkLabel(frame, text="Trace 跳转:", anchor="w").pack(fill="x", pady=(5,0))
        entry_trace = ctk.CTkEntry(frame)
        entry_trace.insert(0, self.trace_hotkey)
        entry_trace.pack(fill="x", pady=2)

        def save_config():
            t_key = entry_time.get().strip().lower()
            j_key = entry_json.get().strip().lower()
            k_key = entry_trace.get().strip().lower()
            
            if t_key and j_key and k_key:
                try:
                    self.time_hotkey = t_key
                    self.json_hotkey = j_key
                    self.trace_hotkey = k_key
                    
                    self.config.save_config("time_hotkey", t_key)
                    self.config.save_config("json_hotkey", j_key)
                    self.config.save_config("trace_hotkey", k_key)
                    
                    self.start_listener()
                    self.setting_window.destroy()
                except: pass
            
        ctk.CTkButton(frame, text="保存生效", command=save_config).pack(pady=20)

    # --- 界面：Trace 链接配置 (新增) ---
    def show_trace_config_ui(self):
        if self.trace_config_window and self.trace_config_window.winfo_exists():
            self.trace_config_window.focus(); return

        self.trace_config_window = ctk.CTkToplevel(self.main_app)
        self.trace_config_window.title("配置 Trace 链接")
        self.trace_config_window.geometry("400x350")
        
        ws = self.trace_config_window.winfo_screenwidth()
        hs = self.trace_config_window.winfo_screenheight()
        self.trace_config_window.geometry(f'+{int(ws/2-200)}+{int(hs/2-175)}')
        self.trace_config_window.attributes('-topmost', True)

        frame = ctk.CTkFrame(self.trace_config_window)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="Trace 网页跳转配置", font=("Microsoft YaHei UI", 12, "bold")).pack(pady=5)
        
        # URL
        ctk.CTkLabel(frame, text="基础 URL (不带参数):", anchor="w").pack(fill="x")
        entry_url = ctk.CTkEntry(frame, placeholder_text="https://...")
        entry_url.insert(0, self.trace_url)
        entry_url.pack(fill="x", pady=(0, 10))

        # Trace Key
        ctk.CTkLabel(frame, text="TraceId 参数名:", anchor="w").pack(fill="x")
        entry_trace_key = ctk.CTkEntry(frame, placeholder_text="例如: traceId 或 q")
        entry_trace_key.insert(0, self.trace_key)
        entry_trace_key.pack(fill="x", pady=(0, 10))

        # Time Key
        ctk.CTkLabel(frame, text="开始时间 参数名 (默认填入-15min):", anchor="w").pack(fill="x")
        entry_time_key = ctk.CTkEntry(frame, placeholder_text="例如: startTime (留空则不传)")
        entry_time_key.insert(0, self.time_key)
        entry_time_key.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(frame, text="* 注: 时间参数将自动生成毫秒级时间戳", font=("Microsoft YaHei UI", 10), text_color="gray").pack()

        def save_trace_config():
            self.trace_url = entry_url.get().strip()
            self.trace_key = entry_trace_key.get().strip()
            self.time_key = entry_time_key.get().strip()
            
            self.config.save_config("trace_url", self.trace_url)
            self.config.save_config("trace_key", self.trace_key)
            self.config.save_config("time_key", self.time_key)
            
            self.trace_config_window.destroy()
            
        ctk.CTkButton(frame, text="保存配置", command=save_trace_config).pack(pady=20)

    # --- 界面：时区 (不变) ---
    def show_timezone_ui(self):
        # ... (和之前版本一致，省略未改动代码以节省篇幅，请保留原有时区代码) ...
        # 如果你直接复制，这里需要补全 show_timezone_ui 的代码
        if self.timezone_window and self.timezone_window.winfo_exists():
            self.timezone_window.focus(); return

        self.timezone_window = ctk.CTkToplevel(self.main_app)
        self.timezone_window.title("选择时区")
        self.timezone_window.geometry("300x200")
        
        ws = self.timezone_window.winfo_screenwidth()
        hs = self.timezone_window.winfo_screenheight()
        self.timezone_window.geometry(f'+{int(ws/2-150)}+{int(hs/2-100)}')
        self.timezone_window.attributes('-topmost', True)

        frame = ctk.CTkFrame(self.timezone_window)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="目标时区", font=("Microsoft YaHei UI", 12, "bold")).pack(pady=10)

        common_tz = ["Local", "UTC", "Asia/Shanghai", "Asia/Tokyo", "America/New_York", "America/Los_Angeles"]
        combo = ctk.CTkComboBox(frame, values=common_tz)
        combo.set(self.current_timezone)
        combo.pack(pady=10)

        def save_timezone():
            selected = combo.get()
            self.current_timezone = selected
            self.config.save_config("timezone", selected)
            self.timezone_window.destroy()
            
        ctk.CTkButton(frame, text="保存", command=save_timezone).pack(pady=20)

if __name__ == "__main__":
    TimestampTool()