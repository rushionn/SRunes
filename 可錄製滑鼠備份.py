import json
import time
import pyautogui
from pynput import mouse, keyboard
import ttkbootstrap as ttk
from pathlib import Path
from tkinter import filedialog
import datetime
import os

# 全域變數
actions = []
recording = False
paused = False
current_filename = ""
mouse_listener = None
keyboard_listener = None

# 儲存錄製的操作
def save_actions():
    global current_filename
    if actions:  # 確保有動作資料
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
        current_filename = f"{timestamp}.json"
        with open(current_filename, "w", encoding="utf-8") as f:
            json.dump(actions, f, ensure_ascii=False, indent=4)

# 儲存錄製的操作 (測試替代版本)
# def save_actions_alternative():
#     global current_filename
#     try:
#         if actions:
#             timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
#             current_filename = f"{timestamp}.json"
#             with open(current_filename, "w", encoding="utf-8") as f:
#                 json.dump(actions, f, ensure_ascii=False, indent=4)
#     except Exception as e:
#         print(f"儲存失敗: {e}")

# 載入已保存的操作
def load_actions(filename):
    if Path(filename).exists():
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# 更新動作代碼到窗框
def update_actions_display(action):
    actions_display.insert("end", f"{action}\n")
    actions_display.see("end")  # 滾動到最新

# 錄製滑鼠和鍵盤事件
def on_click(x, y, button, pressed):
    if recording and not paused:
        action = {"type": "click", "x": x, "y": y, "button": str(button), "pressed": pressed, "time": time.time()}
        actions.append(action)
        update_actions_display(action)

def on_move(x, y):
    if recording and not paused:
        action = {"type": "move", "x": x, "y": y, "time": time.time()}
        actions.append(action)
        update_actions_display(action)

def on_scroll(x, y, dx, dy):
    if recording and not paused:
        action = {"type": "scroll", "x": x, "y": y, "dx": dx, "dy": dy, "time": time.time()}
        actions.append(action)
        update_actions_display(action)

def on_press(key):
    if recording and not paused:
        try:
            action = {"type": "keydown", "key": str(key.char), "time": time.time()}
        except AttributeError:
            action = {"type": "keydown", "key": str(key), "time": time.time()}
        actions.append(action)
        update_actions_display(action)

def on_release(key):
    if recording and not paused:
        action = {"type": "keyup", "key": str(key), "time": time.time()}
        actions.append(action)
        update_actions_display(action)
    if key == keyboard.Key.esc:  # 結束錄製快捷鍵
        stop_recording()

# 開始錄製
def start_recording():
    global actions, recording, paused, mouse_listener, keyboard_listener
    if not recording:
        actions = []  # 清空舊的操作記錄
        recording = True
        paused = False
        record_button.config(text="停止錄製")
        actions_display.delete(1.0, "end")
        actions_display.insert("end", "錄製中...\n")
        # 開始監聽滑鼠和鍵盤事件
        mouse_listener = mouse.Listener(on_click=on_click, on_move=on_move, on_scroll=on_scroll)
        keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        mouse_listener.start()
        keyboard_listener.start()

# 停止錄製
def stop_recording():
    global recording, mouse_listener, keyboard_listener
    if recording:
        recording = False
        save_actions()  # 儲存操作
        record_button.config(text="開始錄製")
        actions_display.insert("end", f"錄製完成，已儲存為: {current_filename}\n")
        if mouse_listener:
            mouse_listener.stop()
        if keyboard_listener:
            keyboard_listener.stop()

# 增加獨立停止功能
# def stop_recording_alternative():
#     global recording
#     recording = False
#     actions_display.insert("end", "錄製已手動停止。\n")
#     save_actions()

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

# 執行選擇的操作
def execute_actions():
    if current_filename:
        filepath = os.path.join(os.getcwd(), current_filename)  # 確保完整路徑
        loaded_actions = load_actions(filepath)
        actions_display.delete(1.0, "end")
        actions_display.insert("end", "執行中...\n")
        if loaded_actions:
            prev_time = loaded_actions[0]["time"]
            for action in loaded_actions:
                time.sleep(action["time"] - prev_time)  # 使用錄製時間計算延遲
                prev_time = action["time"]
                if action["type"] == "click":
                    if action["pressed"]:
                        pyautogui.mouseDown(action["x"], action["y"], button=action["button"])
                    else:
                        pyautogui.mouseUp(action["x"], action["y"], button=action["button"])
                elif action["type"] == "move":
                    pyautogui.moveTo(action["x"], action["y"])
                elif action["type"] == "scroll":
                    pyautogui.scroll(action["dy"], action["x"], action["y"])
                elif action["type"] == "keydown":
                    pyautogui.keyDown(action["key"])
                elif action["type"] == "keyup":
                    pyautogui.keyUp(action["key"])
                actions_display.insert("end", f"{action}\n")
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

# 選擇存檔按鈕
choose_button = ttk.Button(root, text="選擇存檔", command=choose_file)
choose_button.grid(row=1, column=0, padx=5, pady=5)

# 存檔名稱顯示
file_name_label = ttk.Label(root, text="未選擇存檔")
file_name_label.grid(row=1, column=1, padx=5, pady=5)

# 執行按鈕
execute_button = ttk.Button(root, text="執行", command=execute_actions)
execute_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5)

# 顯示當前執行的動作代碼
actions_display = ttk.Text(root, height=12, width=64)
actions_display.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

root.mainloop()