import json
import time
import pyautogui
from pynput import mouse, keyboard
import ttkbootstrap as ttk
from pathlib import Path
from tkinter import filedialog, simpledialog
import datetime
import os
import gc

# =====================常數 =====================
MOUSE_MOVE_THRESHOLD = 100  # 滑鼠移動關值 (像素距離)
last_mouse_position = (0, 0)  # 記錄上次滑鼠位置
# 數字鍵盤按鍵映射表
NUMPAD_MAPPING = {
    "<96>": "numpad0",
    "<97>": "numpad1",
    "<98>": "numpad2",
    "<99>": "numpad3",
    "<100>": "numpad4",
    "<101>": "numpad5",
    "<102>": "numpad6",
    "<103>": "numpad7",
    "<104>": "numpad8",
    "<105>": "numpad9",
    "<110>": "decimal"
}

# ===================== 全域變數 =====================
recorded_actions = []
recording = False
paused = False
current_filename = ""
mouse_listener = None
keyboard_listener = None
emergency_stop = False  # 緊急停止旗標
repeat_times_entry = None  # UI 中的執行次數輸入格

# ===================== 儲存與載入 =====================
def save_actions():
    if recorded_actions:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
        current_filename = f"{timestamp}.json"
        with open(current_filename, "w", encoding="utf-8") as f:
            json.dump(recorded_actions, f, ensure_ascii=False, indent=4)

def load_actions(filename):
    if Path(filename).exists():
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# ===================== 事件處理 =====================
def on_click(x, y, button, pressed):
    if recording and not paused:
        button_name = button.name
        print(f"Click event: ({x}, {y}), Button: {button_name}, Pressed: {pressed}")
        action = {
            "type": "click",
            "x": x, "y": y,
            "button": button_name,
            "pressed": pressed,
            "time": time.time()
        }
        recorded_actions.append(action)
        update_actions_display(action)

def on_move(x, y):
    global last_mouse_position
    if recording and not paused:
        if abs(x - last_mouse_position[0]) >= MOUSE_MOVE_THRESHOLD or abs(y - last_mouse_position[1]) >= MOUSE_MOVE_THRESHOLD:
            print(f"Move event: ({x}, {y})")
            action = {"type": "move", "x": x, "y": y, "time": time.time()}
            recorded_actions.append(action)
            update_actions_display(action)
            last_mouse_position = (x, y)

def on_scroll(x, y, dx, dy):
    if recording and not paused:
        print(f"Scroll event: ({x}, {y}), DX: {dx}, DY: {dy}")
        action = {"type": "scroll", "x": x, "y": y, "dx": dx, "dy": dy, "time": time.time()}
        recorded_actions.append(action)
        update_actions_display(action)

def on_press(key):
    if recording and not paused:
        try:
            key_name = key.char
        except AttributeError:
            key_name = str(key).replace("Key.", "")
            # 添加數字鍵盤相關處理
            if key_name in NUMPAD_MAPPING:
                key_name = NUMPAD_MAPPING[key_name]  # 確保映射正確
        action = {"type": "keydown", "key": key_name, "time": time.time()}
        recorded_actions.append(action)
        update_actions_display(action)

def on_release(key):
    if recording and not paused:
        try:
            key_name = key.char
        except AttributeError:
            key_name = str(key).replace("Key.", "")
            # 添加數字鍵盤相關處理
            if key_name in NUMPAD_MAPPING:
                key_name = NUMPAD_MAPPING[key_name]  # 確保映射正確
        action = {"type": "keyup", "key": key_name, "time": time.time()}
        recorded_actions.append(action)
        update_actions_display(action)

    if key == keyboard.Key.f9:
        stop_recording()

# ===================== UI 事件 =====================
def start_recording():
    global recording, paused, mouse_listener, keyboard_listener
    if not recording:
        recorded_actions.clear()
        recording, paused = True, False
        record_button.config(text="錄製中")
        actions_display.delete(1.0, "end")
        actions_display.insert("end", "錄製中...\n")
        # 啟動監聽器
        if not mouse_listener:
            mouse_listener = mouse.Listener(on_click=on_click, on_move=on_move, on_scroll=on_scroll)
            mouse_listener.start()
        if not keyboard_listener:
            keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            keyboard_listener.start()

def stop_recording():
    global recording, mouse_listener, keyboard_listener
    if recording:
        recording = False
        save_actions()
        record_button.config(text="開始錄製")
        actions_display.insert("end", "錄製完成！\n")
        if mouse_listener:
            mouse_listener.stop()
        if keyboard_listener:
            keyboard_listener.stop()
        mouse_listener, keyboard_listener = None, None
        gc.collect()

def execute_actions():
    if current_filename:
        loaded_actions = load_actions(current_filename)
        if loaded_actions:
            repeat_times = int(repeat_times_entry.get())  # 從 UI 中獲取次數
            for _ in range(repeat_times):
                start_time = loaded_actions[0]["time"]
                for action in loaded_actions:
                    delay = max(0, action["time"] - start_time)
                    time.sleep(delay)
                    # 延遲時間修正
                    start_time = action["time"]
                    for action in loaded_actions:
                        current_time = time.time()
                        delay = max(0, action["time"] - start_time)
                        time.sleep(delay)
                        start_time = current_time
                    # 動作執行部分
                    try:
                        if action["type"] == "click":
                            pyautogui.click(action["x"], action["y"], button=action["button"])
                        elif action["type"] == "move":
                            pyautogui.moveTo(action["x"], action["y"], duration=0)
                        elif action["type"] == "scroll":
                            pyautogui.scroll(action["dy"], action["x"], action["y"])
                        elif action["type"] == "keydown":
                            pyautogui.keyDown(action["key"])
                        elif action["type"] == "keyup":
                            pyautogui.keyUp(action["key"])
                    except Exception as e:
                        actions_display.insert("end", f"執行錯誤: {e}\n")
            actions_display.insert("end", "操作執行完成！\n")

def choose_file():
    global current_filename
    filename = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    if filename:
        current_filename = filename
        file_name_label.config(text=os.path.basename(filename))

def update_actions_display(action):
    actions_display.insert("end", f"{action}\n")
    actions_display.see("end")

# ===================== UI 設定 =====================
root = ttk.Window(themename="superhero")
root.title("SRunes - 操作錄製器")

record_button = ttk.Button(root, text="開始錄製", command=start_recording)
record_button.grid(row=0, column=0, padx=5, pady=5)

pause_button = ttk.Button(root, text="暫停", command=lambda: None)
pause_button.grid(row=0, column=1, padx=5, pady=5)

stop_button = ttk.Button(root, text="停止錄製(F9)", command=stop_recording)
stop_button.grid(row=0, column=2, padx=5, pady=5)

choose_button = ttk.Button(root, text="選擇存檔", command=choose_file)
choose_button.grid(row=1, column=0, padx=5, pady=5)

repeat_times_entry = ttk.Entry(root, width=6)
repeat_times_entry.insert(0, "1")  # 預設執行次數為 1
repeat_times_entry.grid(row=1, column=1, padx=5, pady=5)

execute_button = ttk.Button(root, text="執行操作", command=execute_actions)
execute_button.grid(row=1, column=2, padx=5, pady=5)

file_name_label = ttk.Label(root, text="尚未選擇檔案")
file_name_label.grid(row=2, column=0, columnspan=3, pady=5)

actions_display = ttk.Text(root, height=15, width=70)
actions_display.grid(row=3, column=0, columnspan=3, padx=5, pady=5)

# ===================== 主程式啟動 =====================
root.mainloop()
