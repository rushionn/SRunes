import json
import time
import pyautogui
from pynput import mouse, keyboard
import ttkbootstrap as ttk
from pathlib import Path
from tkinter import filedialog
import threading
import datetime
import os

# ===================== 常數與設定 =====================
MOUSE_MOVE_THRESHOLD = 10  # 滑鼠移動閾值（像素距離）
last_mouse_position = (0, 0)  # 記錄上次滑鼠位置
recorded_actions = []
recording = False
paused = False
current_filename = ""
mouse_listener = None
keyboard_listener = None
repeat_times = 1  # 默認執行次數
playback_delay = 0  # 默認回放延遲
replay_speed = 1  # 默認回放速度 (1為正常速度)
start_time = 0  # 錄製起始時間

# 日誌目錄
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# ===================== 儲存與載入 =====================
def save_actions():
    if recorded_actions:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
        filename = f"{log_dir}/record_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(recorded_actions, f, ensure_ascii=False, indent=4)
        actions_display.insert("end", f"已保存檔案至 {filename}\n")

def load_actions(filename):
    if Path(filename).exists():
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def get_last_saved_file():
    """獲取最近的儲存檔案"""
    files = [f for f in os.listdir(log_dir) if f.endswith(".json")]
    if files:
        files.sort(reverse=True)  # 按時間排序檔案
        return os.path.join(log_dir, files[0])
    return ""

# ===================== 事件處理 =====================
def on_click(x, y, button, pressed):
    if recording and not paused:
        elapsed_time = time.time() - start_time  # 計算相對時間
        action = {"type": "click", "x": x, "y": y, "button": button.name, "pressed": pressed, "time": elapsed_time}
        recorded_actions.append(action)
        update_actions_display(action)

def on_move(x, y):
    global last_mouse_position
    if recording and not paused:
        elapsed_time = time.time() - start_time  # 計算相對時間
        if abs(x - last_mouse_position[0]) >= MOUSE_MOVE_THRESHOLD or abs(y - last_mouse_position[1]) >= MOUSE_MOVE_THRESHOLD:
            action = {"type": "move", "x": x, "y": y, "time": elapsed_time}
            recorded_actions.append(action)
            update_actions_display(action)
            last_mouse_position = (x, y)

def on_press(key):
    if recording and not paused:
        elapsed_time = time.time() - start_time  # 計算相對時間
        try:
            key_name = key.char if key.char else str(key)
        except AttributeError:
            key_name = str(key).replace("Key.", "")
        action = {"type": "keydown", "key": key_name, "time": elapsed_time}
        recorded_actions.append(action)
        update_actions_display(action)

def on_release(key):
    if recording and not paused:
        elapsed_time = time.time() - start_time  # 計算相對時間
        try:
            key_name = key.char if key.char else str(key)
        except AttributeError:
            key_name = str(key).replace("Key.", "")
        action = {"type": "keyup", "key": key_name, "time": elapsed_time}
        recorded_actions.append(action)
        update_actions_display(action)

# ===================== 執行與回放 =====================
def execute_actions():
    global keyboard_listener
    if keyboard_listener:
        keyboard_listener.stop()  # 停止鍵盤監聽器

    if current_filename:
        actions = load_actions(current_filename)
        if actions:
            actions_display.insert("end", f"開始執行回放，共 {repeat_times} 次\n")
            root.update_idletasks()  # 強制更新 UI
            for _ in range(repeat_times):
                start_time = time.time()  # 初始化開始時間
                for action in actions:
                    # 計算每個動作的延遲時間
                    delay = max(0, action["time"] - (time.time() - start_time) + playback_delay) * replay_speed
                    time.sleep(delay)

                    # 根據動作類型執行對應的動作
                    try:
                        if action["type"] == "click":
                            pyautogui.click(action["x"], action["y"], button=action["button"])
                        elif action["type"] == "move":
                            pyautogui.moveTo(action["x"], action["y"], duration=0)
                        elif action["type"] == "keydown":
                            pyautogui.keyDown(action["key"])
                        elif action["type"] == "keyup":
                            pyautogui.keyUp(action["key"])
                    except Exception as e:
                        actions_display.insert("end", f"回放錯誤: {e}\n")

                    root.update_idletasks()  # 強制更新 UI

                actions_display.insert("end", f"回放完成一輪\n")
            actions_display.insert("end", f"所有回放操作已完成。\n")
        else:
            actions_display.insert("end", f"無法載入操作檔案或檔案損壞。\n")
    else:
        actions_display.insert("end", f"未選擇檔案，無法執行回放。\n")

    if keyboard_listener:
        keyboard_listener.start()  # 重新啟動鍵盤監聽器

# ===================== UI 事件 =====================
def start_recording():
    global recording, paused, start_time
    if not recording:
        recorded_actions.clear()
        recording = True
        paused = False
        start_time = time.time()  # 記錄錄製起始時間
        actions_display.insert("end", "開始錄製...\n")
        threading.Thread(target=record_mouse_and_keyboard, daemon=True).start()

def record_mouse_and_keyboard():
    global mouse_listener, keyboard_listener
    mouse_listener = mouse.Listener(on_click=on_click, on_move=on_move)
    keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    mouse_listener.start()
    keyboard_listener.start()
    mouse_listener.join()
    keyboard_listener.join()

def stop_recording():
    global recording
    recording = False
    save_actions()
    actions_display.insert("end", "錄製完成！\n")
    if mouse_listener:
        mouse_listener.stop()
    if keyboard_listener:
        keyboard_listener.stop()

def choose_file():
    global current_filename
    filename = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], initialdir=log_dir)  # 預設路徑為logs資料夾
    if filename:
        current_filename = filename
        file_name_label.config(text=os.path.basename(filename))

def update_actions_display(action):
    actions_display.insert("end", f"{action}\n")
    actions_display.see("end")

def clear_display():
    actions_display.delete(1.0, "end")

# ===================== UI 設定 =====================
root = ttk.Window(themename="superhero")
root.title("操作錄製器")

record_button = ttk.Button(root, text="開始錄製 (F9)", command=start_recording)
record_button.grid(row=0, column=0, padx=5, pady=5)

stop_button = ttk.Button(root, text="停止錄製 (F10)", command=stop_recording)
stop_button.grid(row=0, column=1, padx=5, pady=5)

choose_button = ttk.Button(root, text="選擇檔案", command=choose_file)
choose_button.grid(row=0, column=2, padx=5, pady=5)

repeat_times_entry = ttk.Entry(root, width=6)
repeat_times_entry.insert(0, "1")
repeat_times_entry.grid(row=1, column=0, padx=5, pady=5)

execute_button = ttk.Button(root, text="執行回放", command=execute_actions)
execute_button.grid(row=1, column=1, padx=5, pady=5)

clear_button = ttk.Button(root, text="清空顯示區", command=clear_display)
clear_button.grid(row=1, column=2, padx=5, pady=5)

file_name_label = ttk.Label(root, text="尚未選擇檔案")
file_name_label.grid(row=2, column=0, columnspan=3, pady=5)

actions_display = ttk.Text(root, height=15, width=70)
actions_display.grid(row=3, column=0, columnspan=3, padx=5, pady=5)

# ===================== 監聽快捷鍵 =====================
def on_key_press(key):
    try:
        if key == keyboard.Key.f9:
            start_recording()
        elif key == keyboard.Key.f10:
            stop_recording()
    except AttributeError:
        pass

keyboard_listener = keyboard.Listener(on_press=on_key_press)
keyboard_listener.start()

# ===================== 主程式 =====================
root.mainloop()