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
MOUSE_MOVE_THRESHOLD = 50  # 滑鼠移動閾值（像素距離）
last_mouse_position = (0, 0)
recorded_actions = []
recording = False
paused = False
paused_playback = False
current_filename = ""
mouse_listener = None
keyboard_listener = None
repeat_times = 1
playback_delay = 0
replay_speed = 1
start_time = 0

# 特殊按鍵映射表 (解決右側數字鍵問題)
KEY_MAP = {
    "<65437>": "enter",  # 小鍵盤 Enter
    "<65429>": "0",
    "<65434>": "1",
    "<65435>": "2",
    "<65436>": "3",
    "<65430>": "4",
    "<65431>": "5",
    "<65432>": "6",
    "<65426>": "7",
    "<65427>": "8",
    "<65428>": "9",
    "<65439>": "numlock",
    "<65453>": ".",
    "<65450>": "*",  # 小鍵盤 *
    "<65451>": "+",  # 小鍵盤 +
    "<65452>": "-",  # 小鍵盤 -
    "<65453>": "/"   # 小鍵盤 /
}

log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# ===================== 儲存與載入 =====================
def save_actions():
    try:
        if recorded_actions:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
            filename = f"{log_dir}/record_{timestamp}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(recorded_actions, f, ensure_ascii=False, indent=4)
            actions_display.insert("end", f"已保存檔案至 {filename}\n")
            return filename
    except Exception as e:
        actions_display.insert("end", f"保存檔案時發生錯誤: {e}\n")
    return ""

def load_actions(filename):
    try:
        if Path(filename).exists():
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        actions_display.insert("end", f"載入檔案時發生錯誤: {e}\n")
    return []

def get_last_saved_file():
    try:
        files = [f for f in os.listdir(log_dir) if f.endswith(".json")]
        if files:
            files.sort(reverse=True)
            return os.path.join(log_dir, files[0])
    except Exception as e:
        actions_display.insert("end", f"獲取最新檔案時發生錯誤: {e}\n")
    return ""

# ===================== 事件處理 =====================
def on_click(x, y, button, pressed):
    if recording and not paused:
        try:
            elapsed_time = round(time.time() - start_time, 3)
            action = {"type": "click", "x": x, "y": y, "button": button.name, "pressed": pressed, "time": elapsed_time}
            recorded_actions.append(action)
            update_actions_display(action)
        except Exception as e:
            actions_display.insert("end", f"錄製點擊事件時發生錯誤: {e}\n")

def on_move(x, y):
    global last_mouse_position
    if recording and not paused:
        try:
            elapsed_time = round(time.time() - start_time, 3)
            distance = ((x - last_mouse_position[0])**2 + (y - last_mouse_position[1])**2)**0.5
            if distance >= MOUSE_MOVE_THRESHOLD:
                action = {"type": "move", "x": x, "y": y, "time": elapsed_time}
                recorded_actions.append(action)
                update_actions_display(action)
                last_mouse_position = (x, y)
        except Exception as e:
            actions_display.insert("end", f"錄製移動事件時發生錯誤: {e}\n")

def on_press(key):
    if recording and not paused:
        try:
            elapsed_time = round(time.time() - start_time, 3)
            try:
                key_name = key.char
            except AttributeError:
                key_str = str(key)
                key_name = KEY_MAP.get(key_str, key_str.replace("Key.", ""))
            action = {"type": "keydown", "key": key_name, "time": elapsed_time}
            recorded_actions.append(action)
            update_actions_display(action)
        except Exception as e:
            actions_display.insert("end", f"錄製按鍵按下事件時發生錯誤: {e}\n")

def on_release(key):
    if recording and not paused:
        try:
            elapsed_time = round(time.time() - start_time, 3)
            try:
                key_name = key.char
            except AttributeError:
                key_str = str(key)
                key_name = KEY_MAP.get(key_str, key_str.replace("Key.", ""))
            action = {"type": "keyup", "key": key_name, "time": elapsed_time}
            recorded_actions.append(action)
            update_actions_display(action)
        except Exception as e:
            actions_display.insert("end", f"錄製按鍵釋放事件時發生錯誤: {e}\n")

# ===================== 執行與回放 =====================
def execute_actions():
    global keyboard_listener, paused_playback
    if keyboard_listener:
        keyboard_listener.stop()

    if current_filename:
        actions = load_actions(current_filename)
        if actions:
            actions_display.delete(1.0, "end")  # 清空視窗
            actions_display.insert("end", f"開始執行回放，共 {repeat_times} 次\n")
            root.update_idletasks()
            for _ in range(repeat_times):
                start_time = time.time()
                for action in actions:
                    while paused_playback:
                        time.sleep(0.1)
                        root.update_idletasks()

                    # 計算每個動作的延遲時間
                    delay = max(0, action["time"] - (time.time() - start_time) + playback_delay) * replay_speed
                    time.sleep(delay)

                    try:
                        if action["type"] == "click":
                            # 先移動到點擊位置
                            pyautogui.moveTo(action["x"], action["y"], duration=0.01, _pause=False)
                            # 執行點擊
                            pyautogui.mouseDown(button=action["button"], _pause=False) if action["pressed"] else pyautogui.mouseUp(button=action["button"], _pause=False)
                        elif action["type"] == "move":
                            pyautogui.moveTo(action["x"], action["y"], duration=0.01, _pause=False)
                        elif action["type"] == "keydown":
                            if action["key"]:  # 確保鍵名有效
                                pyautogui.keyDown(action["key"], _pause=False)
                        elif action["type"] == "keyup":
                            if action["key"]:  # 確保鍵名有效
                                pyautogui.keyUp(action["key"], _pause=False)
                    except Exception as e:
                        actions_display.insert("end", f"回放錯誤: {e}\n")

                    root.update_idletasks()

                actions_display.insert("end", f"回放完成一輪\n")
            actions_display.insert("end", f"所有回放操作已完成。\n")
        else:
            actions_display.insert("end", f"無法載入操作檔案或檔案損壞。\n")
    else:
        actions_display.insert("end", f"未選擇檔案，無法執行回放。\n")

    if keyboard_listener:
        keyboard_listener.start()

# ===================== UI 事件 =====================
def start_recording():
    global recording, paused, start_time
    if not recording:
        recorded_actions.clear()
        recording = True
        paused = False
        start_time = time.time()
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
    global recording, current_filename
    recording = False
    latest_file = save_actions()
    if latest_file:
        current_filename = latest_file
        file_name_label.config(text=os.path.basename(latest_file))
    actions_display.insert("end", "錄製完成！\n")
    if mouse_listener:
        mouse_listener.stop()
    if keyboard_listener:
        keyboard_listener.stop()

def choose_file():
    global current_filename
    filename = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], initialdir=log_dir)
    if filename:
        current_filename = filename
        file_name_label.config(text=os.path.basename(filename))
        actions_display.delete(1.0, "end")  # 清空視窗

def toggle_pause_playback():
    global paused_playback
    paused_playback = not paused_playback
    if paused_playback:
        pause_button.config(text="繼續回放 (F11)")
    else:
        pause_button.config(text="暫停回放 (F11)")

def update_actions_display(action):
    actions_display.insert("end", f"{action}\n")
    actions_display.see("end")  # 確保視窗滾動到最新內容
    actions_display.update()  # 強制更新 UI

# ===================== UI 設定 =====================
root = ttk.Window(themename="superhero")
root.title("操作錄製器")

# 統一按鈕大小
button_width = 15

record_button = ttk.Button(root, text="開始錄製 (F9)", command=start_recording, width=button_width)
record_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

stop_button = ttk.Button(root, text="停止錄製 (F10)", command=stop_recording, width=button_width)
stop_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

choose_button = ttk.Button(root, text="選擇檔案", command=choose_file, width=button_width)
choose_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

repeat_times_entry = ttk.Entry(root, width=6)
repeat_times_entry.insert(0, "1")
repeat_times_entry.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

execute_button = ttk.Button(root, text="執行回放 (F12)", command=execute_actions, width=button_width)
execute_button.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

pause_button = ttk.Button(root, text="暫停回放 (F11)", command=toggle_pause_playback, width=button_width)
pause_button.grid(row=1, column=2, padx=5, pady=5, sticky="ew")

file_name_label = ttk.Label(root, text="尚未選擇檔案")
file_name_label.grid(row=2, column=0, columnspan=3, pady=5)

actions_display = ttk.Text(root, height=15, width=70)
actions_display.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")

# 讓按鈕和顯示區隨窗口大小調整
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)
root.grid_rowconfigure(3, weight=1)

# ===================== 監聽快捷鍵 =====================
def on_key_press(key):
    try:
        if key == keyboard.Key.f9:
            start_recording()
        elif key == keyboard.Key.f10:
            stop_recording()
        elif key == keyboard.Key.f11:
            toggle_pause_playback()
        elif key == keyboard.Key.f12:
            execute_actions()
    except AttributeError:
        pass

keyboard_listener = keyboard.Listener(on_press=on_key_press)
keyboard_listener.start()

# ===================== 主程式 =====================
root.mainloop()