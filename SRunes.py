import json
import time
import pyautogui
from pynput import mouse, keyboard
import ttkbootstrap as ttk
from pathlib import Path
from tkinter import filedialog
from tkinter import StringVar
import datetime
import os

# 全域變數
actions = []
recording = False
paused = False
current_filename = ""
playback_accuracy = 100  # 預設播放精準度

class MouseRecorder:
    def __init__(self):
        self.actions = []
        self.recording = False
        self.mouse_listener = None
    
    def on_click(self, x, y, button, pressed):
        if self.recording:
            action = {
                "type": "click",
                "x": x,
                "y": y,
                "button": str(button),
                "pressed": pressed,
                "time": time.time()
            }
            self.actions.append(action)
            update_actions_display(action)

    def on_move(self, x, y):
        if self.recording:
            action = {
                "type": "move",
                "x": x,
                "y": y,
                "time": time.time()
            }
            self.actions.append(action)
            update_actions_display(action)

    def on_scroll(self, x, y, dx, dy):
        if self.recording:
            action = {
                "type": "scroll",
                "x": x,
                "y": y,
                "dx": dx,
                "dy": dy,
                "time": time.time()
            }
            self.actions.append(action)
            update_actions_display(action)

    def start_recording(self):
        global recording
        self.recording = True
        actions.clear()  # 清空舊的操作記錄
        self.mouse_listener = mouse.Listener(on_click=self.on_click, on_move=self.on_move, on_scroll=self.on_scroll)
        self.mouse_listener.start()

    def stop_recording(self):
        self.recording = False
        if self.mouse_listener:
            self.mouse_listener.stop()

# 儲存錄製的操作
def save_actions():
    global current_filename
    if actions:  # 確保有動作資料
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
        current_filename = f"{timestamp}.json"
        with open(current_filename, "w", encoding="utf-8") as f:
            json.dump(actions, f, ensure_ascii=False, indent=4)

# 載入已保存的操作
def load_actions(filename):
    if Path(filename).exists():
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# 更新動作代碼到窗框
def update_actions_display(action):
    action_display = ""
    if action["type"] == "click":
        action_display = f"[click] X: {action['x']} Y: {action['y']} Button: {action['button']} Pressed: {action['pressed']}"
    elif action["type"] == "move":
        action_display = f"[move] X: {action['x']} Y: {action['y']}"
    elif action["type"] == "scroll":
        action_display = f"[scroll] X: {action['x']} Y: {action['y']} DX: {action['dx']} DY: {action['dy']}"
    elif action["type"] in ["keydown", "keyup"]:
        action_display = f"[{action['type']}] Key: {action['key']}"
    
    actions_display.insert("end", f"{action_display}\n")
    actions_display.see("end")  # 滾動到最新

# 鍵盤事件錄製
def on_press(key):
    if recording and not paused:
        try:
            action = {
                "type": "keydown",
                "key": str(key.char),
                "time": time.time()
            }
        except AttributeError:
            action = {
                "type": "keydown",
                "key": str(key),
                "time": time.time()
            }
        actions.append(action)
        update_actions_display(action)

def on_release(key):
    if recording and not paused:
        action = {
            "type": "keyup",
            "key": str(key),
            "time": time.time()
        }
        actions.append(action)
        update_actions_display(action)

# 開始錄製
def start_recording():
    global recording, paused
    if not recording:
        global mouse_recorder
        mouse_recorder.start_recording()
        recording = True
        paused = False
        record_button.config(text="錄製中")
        actions_display.delete(1.0, "end")
        actions_display.insert("end", "錄製中...\n")

# 停止錄製
def stop_recording():
    global recording
    if recording:
        recording = False
        mouse_recorder.stop_recording()  # 停止滑鼠錄製
        save_actions()  # 儲存操作
        record_button.config(text="開始錄製")
        actions_display.insert("end", f"錄製完成，已儲存為: {current_filename}\n")

# 暫停與繼續錄製
def toggle_pause():
    global paused
    if recording:  # 僅在錄製中可切換
        paused = not paused
        pause_button.config(text="繼續" if paused else "暫停")

# 讀取已儲存的檔案
def choose_file():
    global current_filename
    filename = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    if filename:
        current_filename = os.path.basename(filename)  # 僅顯示檔案名稱
        file_name_label.config(text=current_filename)

# 設置播放精準度
def set_playback_accuracy(value):
    global playback_accuracy
    playback_accuracy = int(value)  # 將選擇的值轉換為整數

# 執行選擇的操作
def execute_actions():
    global current_filename
    if current_filename:
        filepath = os.path.join(os.getcwd(), current_filename)  # 確保完整路徑
        loaded_actions = load_actions(filepath)
        actions_display.delete(1.0, "end")
        actions_display.insert("end", "執行中...\n")
        if loaded_actions:
            for action in loaded_actions:
                # 調整播放速度根據 playback_accuracy 的設定
                time.sleep(0.1 * (100 / playback_accuracy))  # 根據選擇的值來設定播放精準度
                try:
                    # 執行各種行為
                    if action["type"] == "click":
                        x, y = action["x"], action["y"]
                        button = action["button"]
                        pressed = action["pressed"]
                        if pressed:
                            pyautogui.mouseDown(x, y, button=button)
                        else:
                            pyautogui.mouseUp(x, y, button=button)
                    elif action["type"] == "move":
                        x, y = action["x"], action["y"]
                        pyautogui.moveTo(x, y)
                    elif action["type"] == "scroll":
                        dy = action["dy"]
                        pyautogui.scroll(dy)
                    elif action["type"] == "keydown":
                        key = action["key"]
                        pyautogui.keyDown(key)
                    elif action["type"] == "keyup":
                        key = action["key"]
                        pyautogui.keyUp(key)

                    # 在動作視窗中顯示執行中的動作
                    action_display = f"[{action['type']}]"
                    if action["type"] == "click" or action["type"] == "move":
                        action_display += f" X: {action.get('x', 'N/A')} Y: {action.get('y', 'N/A')}"
                    elif action["type"] in ["keydown", "keyup"]:
                        action_display += f" Key: {action['key']}"
                    elif action["type"] == "scroll":
                        action_display += f" DX: {action['dx']} DY: {action['dy']}"
                    actions_display.insert("end", f"{action_display}\n")
                    actions_display.see("end")
                except Exception as e:
                    # 捕獲可能的錯誤並顯示
                    actions_display.insert("end", f"執行動作時發生錯誤: {str(e)}\n")
                    actions_display.see("end")
        else:
            actions_display.insert("end", "無效的檔案或內容為空！\n")
    else:
        actions_display.insert("end", "未選擇檔案！\n")

# UI設置
root = ttk.Window(themename="superhero")
root.title("SRunes")

# 開始錄製按鈕
record_button = ttk.Button(root, text="開始錄製", command=start_recording)
record_button.grid(row=0, column=0, padx=5, pady=5)

# 暫停與繼續按鈕
pause_button = ttk.Button(root, text="暫停", command=toggle_pause)
pause_button.grid(row=0, column=1, padx=5, pady=5)

# 停止錄製按鈕 (F9 快捷鍵)
stop_button = ttk.Button(root, text="停止錄製(F9)", command=stop_recording)
stop_button.grid(row=0, column=2, padx=5, pady=5)

# 選擇存檔按鈕
choose_button = ttk.Button(root, text="選擇存檔", command=choose_file)
choose_button.grid(row=1, column=0, padx=5, pady=5)

# 存檔名稱顯示
file_name_label = ttk.Label(root, text="未選擇存檔")
file_name_label.grid(row=1, column=1, padx=5, pady=5)

# 播放精準度下拉選單
accuracy_label = ttk.Label(root, text="播放精準度 (%)")
accuracy_label.grid(row=1, column=2, padx=5, pady=5)

accuracy_var = StringVar(value="100")  # 預設值
accuracy_dropdown = ttk.Combobox(root, textvariable=accuracy_var, state="readonly")
accuracy_dropdown['values'] = (25, 50, 75, 100)
accuracy_dropdown.grid(row=2, column=2, padx=5, pady=5)
accuracy_dropdown.bind("<<ComboboxSelected>>", lambda event: set_playback_accuracy(accuracy_var.get()))

# 執行按鈕
execute_button = ttk.Button(root, text="執行", command=execute_actions)
execute_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5)

# 顯示當前執行的動作代碼
actions_display = ttk.Text(root, height=12, width=64)
actions_display.grid(row=3, column=0, columnspan=3, padx=5, pady=5)

# 初始化滑鼠錄製器的實例
mouse_recorder = MouseRecorder()

root.mainloop()