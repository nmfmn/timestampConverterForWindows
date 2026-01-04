这是我用gemini 3 pro preview生成的开发查日志小工具。[去下载exe](https://github.com/nmfmn/timestampConverterForWindows/releases)

<img src="demoGif.gif" style="zoom:50%;" />

# 🧰 DevTools Pro - Windows 开发者效率工具箱

**DevTools Pro** 是一款专为开发者设计的 Windows 桌面效率工具。它在后台静默运行，通过全局快捷键快速唤醒，提供**时间戳转换**和**JSON 格式化**两大核心功能。

**v3.0 核心升级**：新增 JSON 格式化功能，支持双快捷键独立配置，优化窗口交互体验。

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg) ![Platform](https://img.shields.io/badge/Platform-Windows_10%2F11-0078D4.svg) ![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ 核心功能

### 1. 🕒 智能时间戳转换
*   **快捷键**：默认 `<ctrl>+<alt>+h`
*   **功能**：
    *   智能识别 10 位（秒）和 13 位（毫秒）时间戳。
    *   支持全球时区转换（UTC, 美东, 东京等）。
    *   **阅后即焚**：弹窗失去焦点自动关闭，操作行云流水。

### 2. 📝 JSON 格式化与预览 (New!)
*   **快捷键**：默认 `<ctrl>+<alt>+j`
*   **功能**：
    *   将选中的混乱 JSON 字符串瞬间格式化（Pretty Print）。
    *   **交互优化**：弹窗**不会自动关闭**，支持在文本框内自由拖拽选择、复制部分内容。
    *   支持语法错误提示，快速定位 JSON 格式问题。

### 3. ⚙️ 系统级特性
*   **防休眠内核**：基于 `pynput`，完美解决电脑休眠后快捷键失效的问题。
*   **配置管理**：通过托盘菜单可独立设置两个功能的快捷键及目标时区。
*   **开机自启**：智能注册表集成，一次运行，永久守护。

---

## 📖 使用指南

### 启动软件
双击 `DevTools.exe`（打包后的名称）。程序启动后会隐藏至**系统托盘**（右下角），不占用任务栏。

### 场景 A：查看时间戳
1.  选中一串数字（如 `1735639680`）。
2.  按下 **`Ctrl + Alt + H`**。
3.  **结果**：鼠标旁弹出日期 `2024-12-31 18:08:00`。
4.  **操作**：按 `Enter` 复制并关闭，或点击窗口外部直接关闭。

### 场景 B：格式化 JSON
1.  选中一段未格式化的 JSON 文本（如 `{"code":200,"msg":"success"}`）。
2.  按下 **`Ctrl + Alt + J`**。
3.  **结果**：屏幕弹出大窗口，展示高亮缩进后的 JSON。
4.  **操作**：
    *   **复制全部**：点击底部按钮或按 `Enter`。
    *   **部分复制**：用鼠标选中需要的字段 -> `Ctrl+C`。
    *   **关闭**：按 `Esc` 键或点击关闭按钮。

---

## ⚙️ 设置与配置

在系统托盘图标上 **点击右键**，可访问高级设置：

*   **修改时区 (Timezone)**：设置时间戳转换的目标时区（如切换到 UTC 查看服务器日志）。
*   **设置快捷键 (Settings)**：
    *   分别配置时间戳和 JSON 的触发热键。
    *   支持标准格式，如 `<alt>+q` 或 `<ctrl>+<shift>+z`。

---

## 🛠️ 源码构建指南

如果你想自行打包修改版本，请严格按照以下步骤操作。

### 1. 安装依赖
```bash
pip install customtkinter pynput pyperclip pystray Pillow pytz pyinstaller
```

### 2. 打包命令 (Build)
由于引入了多窗口 UI 和时区库，**必须**使用以下完整命令进行打包：

```powershell
# --noconsole: 隐藏黑窗口
# --collect-all: 确保 UI 库和时区数据被正确打包

python -m PyInstaller --noconsole --onefile --name "DevTools" --collect-all customtkinter --collect-all pytz main.py
```

---

## ❓ 常见问题 (FAQ)

**Q: JSON 弹窗为什么点击外部不会自动关闭？**
*   **A**: 设计如此。为了方便用户在弹窗内**选中并复制部分内容**，我们取消了 JSON 窗口的自动关闭功能。请按 `Esc` 键或点击按钮关闭。

**Q: 为什么按快捷键没反应？**
*   **A**:
    1.  检查托盘区是否有图标。
    2.  如果在**管理员权限**窗口（如任务管理器）操作，请右键软件 -> **“以管理员身份运行”**。

**Q: 提示“JSON 解析失败”？**
*   **A**: 说明选中的文本不符合 JSON 标准格式（例如缺少引号、逗号错误）。弹窗会显示具体的错误位置帮助排查。

---

## 📝 版本历史

*   **v3.0.0**
    *   ✨ 新增：JSON 格式化功能。
    *   ✨ 新增：双快捷键独立配置支持。
    *   🔧 优化：区分窗口交互模式（时间戳自动关闭 vs JSON 手动关闭）。
*   **v2.1.0**
    *   ✨ 新增：全球时区切换。
    *   🔧 核心：升级 `pynput` 内核，修复休眠失效问题。
*   **v1.0.0**
    *   🎉 首发：基础时间戳转换功能。

---

**Made with ❤️ for Developers**