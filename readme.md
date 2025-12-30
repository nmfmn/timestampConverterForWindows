这是我用gemini 3 pro preview生成的时间戳转换小工具。[去下载exe](https://github.com/nmfmn/timestampConverterForWindows/releases/tag/release)

<img src="demoGif.gif" style="zoom:50%;" />

# 🕒 TimeConverter Pro - 专业时间戳转换助手

**TimeConverter** 是一款专为开发者、运维和数据分析师打造的 Windows 高效工具。它在后台静默运行，通过快捷键唤醒，能将任意选中的时间戳瞬间转换为可读日期。

**v2.0 核心升级**：采用 `pynput` 专业内核，完美解决系统休眠导致的功能失效问题，并新增全球时区转换支持。

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg) ![Platform](https://img.shields.io/badge/Platform-Windows_10%2F11-0078D4.svg) ![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ 核心特性

*   **⚡ 极速唤醒**：双击选中数字 -> 按下快捷键（默认 `<ctrl>+<alt>+h`）-> 立即展示结果。
*   **🌍 时区支持 (New!)**：支持切换 **UTC**、**美东**、**东京**等全球时区，服务器日志排查神技。
*   **🛡️ 磐石稳定**：基于 `pynput` 钩子技术，休眠唤醒后 **100% 不掉线**，无需重启。
*   **🧠 智能容错**：自动清洗剪切板脏数据（如 `time: 1712345678,`），精准提取 10 位/13 位时间戳。
*   **🎨 现代 UI**：Win11 风格圆角界面，自动跟随鼠标位置，支持深色模式。
*   **⚙️ 灵活配置**：通过托盘菜单即可修改快捷键和目标时区，配置自动保存。
*   **🚀 开机自启**：智能注册表集成，一次运行，永久守护。

---

## 📖 使用手册

### 1. 启动与运行
下载并双击 `TimeConverter.exe`。程序启动后会最小化至**系统托盘**（右下角小图标），不占用任务栏。

### 2. 基础转换
1.  在任意软件中选中一串时间戳（例如 `1735639680`）。
2.  按下快捷键 **`Ctrl + Alt + H`**。
3.  屏幕将弹出转换结果：`2024-12-31 18:08:00`。
4.  **按 Enter 键**：复制日期并关闭窗口。

### 3. 进阶功能
在系统托盘图标上 **点击右键**，可访问高级菜单：

*   **🌐 修改时区 (Timezone)**：
    *   弹窗选择目标时区（如 `UTC` 或 `Asia/Shanghai`）。
    *   设置后，所有转换结果将自动计算时差。
*   **⌨️ 设置快捷键 (Hotkey)**：
    *   自定义你的专属热键（支持 `pynput` 格式，如 `<ctrl>+<shift>+z`）。

---

## 🛠️ 开发者指南 (源码构建)

如果你希望自行修改代码或打包，请遵循以下步骤。

### 1. 环境依赖
本项目依赖以下 Python 库（请务必安装 `pytz` 和 `pynput`）：

```bash
pip install customtkinter pynput pyperclip pystray Pillow pytz pyinstaller
```

### 2. 源码运行
```bash
python main.py
```

### 3. 打包发布 (Build)
由于引入了 UI 库和时区数据库，**必须**使用以下命令打包，否则会因缺少资源文件导致闪退：

```powershell
# --noconsole: 隐藏黑窗口
# --collect-all: 收集库的资源文件 (关键步骤)

python -m PyInstaller --noconsole --onefile --name "TimeConverter" --collect-all customtkinter --collect-all pytz main.py
```

打包完成后，`dist` 文件夹内的 `.exe` 文件即为最终成品。

---

## ❓ 常见问题 (FAQ)

**Q: 为什么在任务管理器或某些系统界面里按快捷键没反应？**
*   **A**: 这是 Windows 的安全机制（权限隔离）。如果目标窗口是“管理员权限”运行的，普通软件无法向其发送复制指令。
    *   **解决方法**：右键点击本软件 -> 选择 **“以管理员身份运行”**。

**Q: 休眠后需要重启软件吗？**
*   **A**: **不需要**。v2.0 版本已升级内核，能够自动处理系统休眠和唤醒事件，全天候待命。

**Q: 为什么提示“非时间戳”？**
*   **A**: 请检查选中的内容是否包含有效的数字。虽然软件有智能清洗功能，但如果选中的全是中文或字母，将无法转换。

**Q: 快捷键设置格式是什么？**
*   **A**: 采用标准格式，修饰键需用尖括号包裹。例如：
    *   `<ctrl>+<alt>+h` (默认)
    *   `<alt>+q`
    *   `<ctrl>+<shift>+c`

---

## 📝 版本历史

*   **v2.1.0 (Current)**
    *   ✨ 新增：全球时区切换功能 (UTC, Local, etc.)。
    *   🔧 优化：重构为 `pynput` 内核，彻底解决按键冲突和休眠失效问题。
    *   🔧 优化：增加主动释放修饰键逻辑，防止 `Alt` 卡键。
*   **v1.0.0**
    *   🎉 首发：基于 `keyboard` 库，支持基础转换与鼠标跟随弹窗。

---

**Made with ❤️ by Python**