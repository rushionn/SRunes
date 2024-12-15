現在滑鼠的部分算是正常，鍵盤則沒有反應。12/16

import json
import time
import pyautogui
from pynput import mouse, keyboard
import ttkbootstrap as ttk
from pathlib import Path
from tkinter import filedialog
import datetime
import os
import gc
# ===================== 新增部分 =====================
# 滑鼠捕捉頻率閾值 (像素距離)
MOUSE_MOVE_THRESHOLD = 100  # 預設為10像素，可以自行調整
last_mouse_position = (0, 0)  # 記錄上次滑鼠位置
# ===================================================

# 全域變數
recorded_actions = []
recording = False
paused = False
current_filename = ""
mouse_listener = None
keyboard_listener = None
emergency_stop = False  # 緊急停止旗標

# 儲存錄製的操作
def save_actions():
    global current_filename
    if recorded_actions:  # 確保有動作資料
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
        current_filename = f"{timestamp}.json"
        with open(current_filename, "w", encoding="utf-8") as f:
            json.dump(recorded_actions, f, ensure_ascii=False, indent=4)

# 載入已保存的操作
def load_actions(filename):
    if Path(filename).exists():
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# 更新動作代碼到窗框 (簡化顯示)
def update_actions_display(action):
    simplified_action = ""
    if action["type"] == "click":
        simplified_action = f"[click] X: {action['x']} Y: {action['y']} Button: {action['button']} Pressed: {action['pressed']}"
    elif action["type"] == "move":
        simplified_action = f"[move] X: {action['x']} Y: {action['y']}"
    elif action["type"] == "scroll":
        simplified_action = f"[scroll] DX: {action['dx']} DY: {action['dy']}"
    elif action["type"] in ["keydown", "keyup"]:
        simplified_action = f"[{action['type']}] Key: {action['key']}"
    else:
        simplified_action = "[unknown event]"
    actions_display.insert("end", f"{simplified_action}\n")
    actions_display.see("end")

# 滑鼠與鍵盤事件處理器
def on_click(x, y, button, pressed):
    if recording and not paused:
        button_name = "left" if button == mouse.Button.left else "right" if button == mouse.Button.right else "middle"
        print(f"Click event: ({x}, {y}), Button: {button_name}, Pressed: {pressed}")
        action = {
            "type": "click",
            "x": x,
            "y": y,
            "button": button_name,  # 改為標準名稱
            "pressed": pressed,
            "time": time.time()
        }
        recorded_actions.append(action)
        update_actions_display(action)


# ===================== 修改部分 =====================
def on_move(x, y):
    global last_mouse_position
    if recording and not paused:
        # 判斷滑鼠移動距離是否超過閾值
        if abs(x - last_mouse_position[0]) >= MOUSE_MOVE_THRESHOLD or abs(y - last_mouse_position[1]) >= MOUSE_MOVE_THRESHOLD:
            print(f"Move event: ({x}, {y})")
            action = {"type": "move", "x": x, "y": y, "time": time.time()}
            recorded_actions.append(action)
            update_actions_display(action)
            last_mouse_position = (x, y)  # 更新滑鼠位置
# ===================================================


def on_scroll(x, y, dx, dy):
    if recording and not paused:
        print(f"Scroll event: ({x}, {y}), DX: {dx}, DY: {dy}")
        action = {"type": "scroll", "x": x, "y": y, "dx": dx, "dy": dy, "time": time.time()}
        recorded_actions.append(action)
        update_actions_display(action)

def on_press(key):
    if recording and not paused:
        try:
            print(f"Key down event: {key}")
            action = {"type": "keydown", "key": str(key.char), "time": time.time()}
        except AttributeError:
            action = {"type": "keydown", "key": str(key), "time": time.time()}
        recorded_actions.append(action)
        update_actions_display(action)

def on_release(key):
    if recording and not paused:
        print(f"Key up event: {key}")
        action = {"type": "keyup", "key": str(key), "time": time.time()}
        recorded_actions.append(action)
        update_actions_display(action)
    if key == keyboard.Key.f9:  # 停止錄製快捷鍵
        stop_recording()

# 開始錄製
def start_recording():
    global recorded_actions, recording, paused, mouse_listener, keyboard_listener
    try:
        if not recording:
            recorded_actions.clear()  # 清空舊的操作記錄
            recording = True
            paused = False
            record_button.config(text="錄製中")
            actions_display.delete(1.0, "end")
            actions_display.insert("end", "錄製中...\n")
            # 初始化監聽器
            mouse_listener = mouse.Listener(on_click=on_click, on_move=on_move, on_scroll=on_scroll)
            keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            mouse_listener.start()
            keyboard_listener.start()
    except Exception as e:
        actions_display.insert("end", f"錄製啟動失敗：{e}\n")

# 停止錄製
def stop_recording():
    global recording, mouse_listener, keyboard_listener
    if recording:
        recording = False
        save_actions()  # 儲存操作
        record_button.config(text="開始錄製")
        actions_display.insert("end", f"錄製完成，儲存為：{current_filename}\n")
        # 停止監聽器
        try:
            if mouse_listener:
                mouse_listener.stop()
                mouse_listener = None
            if keyboard_listener:
                keyboard_listener.stop()
                keyboard_listener = None
        except Exception as e:
            actions_display.insert("end", f"停止監聽時發生錯誤：{e}\n")
        gc.collect()  # 垃圾回收

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
    global emergency_stop
    if current_filename:
        loaded_actions = load_actions(current_filename)
        if not loaded_actions:
            actions_display.insert("end", "檔案內容為空或無效！\n")
            return

        actions_display.insert("end", "\n正在執行錄製操作...\n")
        start_time = loaded_actions[0]["time"]
        for action in loaded_actions:
            try:
                # 計算延遲
                time.sleep(max(0, action["time"] - start_time))
                start_time = action["time"]
                
                if action["type"] == "click":
                    if action["pressed"]:
                        pyautogui.mouseDown(action["x"], action["y"], button=action["button"])
                    else:
                        pyautogui.mouseUp(action["x"], action["y"], button=action["button"])
                elif action["type"] == "move":
                    pyautogui.moveTo(action["x"], action["y"], duration=0.05)
                elif action["type"] == "scroll":
                    pyautogui.scroll(action["dy"], action["x"], action["y"])
                elif action["type"] == "keydown":
                    pyautogui.keyDown(action["key"])
                elif action["type"] == "keyup":
                    pyautogui.keyUp(action["key"])
            except Exception as e:
                actions_display.insert("end", f"執行錯誤: {e}\n")
        actions_display.insert("end", "操作執行完成！\n")
    else:
        actions_display.insert("end", "未選擇執行檔案！\n")

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

# 執行按鈕
execute_button = ttk.Button(root, text="執行", command=execute_actions)
execute_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5)

# 顯示當前執行的動作代碼
actions_display = ttk.Text(root, height=12, width=64)
actions_display.grid(row=3, column=0, columnspan=3, padx=5, pady=5)

# 啟動全域快捷鍵監聽
# function listen_for_emergency_stop 定義需完善，這裡假設為一個內建功能
# listen_for_emergency_stop()

#idle_mouse_check()
root.mainloop()

