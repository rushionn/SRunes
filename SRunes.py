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
emergency_stop = False  # 緊急停止旗標

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

# 更新動作代碼到窗框 (簡化顯示)
# 新增：錄製提示
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

# 新增：滑鼠移動空閒提示
def idle_mouse_check():
    if not recording or paused:
        return
    if len(actions) == 0:  # 未有事件時提示
        actions_display.insert("end", "滑鼠未移動或無按鍵事件...\n")
        actions_display.see("end")
    root.after(5000, idle_mouse_check)

# 錄製滑鼠和鍵盤事件
# 修正滑鼠事件
def on_click(x, y, button, pressed):
    if recording and not paused:
        action = {
            "type": "click",
            "x": x,
            "y": y,
            "button": str(button),
            "pressed": pressed,
            "time": time.time()
        }
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
    if key == keyboard.Key.f9:  # 停止錄製快捷鍵
        stop_recording()

# 開始錄製
# 修正：滑鼠和鍵盤監聽初始化
def start_recording():
    global actions, recording, paused, mouse_listener, keyboard_listener
    try:
        if not recording:
            actions.clear()  # 清空舊的操作記錄
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
# 修正：在停止錄製時檢查監聽器是否存在
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
        filepath = os.path.join(os.getcwd(), current_filename)  # 確保完整路徑
        loaded_actions = load_actions(filepath)
        actions_display.delete(1.0, "end")
        actions_display.insert("end", "執行中...\n")
        if loaded_actions:
            prev_time = loaded_actions[0]["time"]
            for action in loaded_actions:
                # 計算行為之間的延遲
                delay = action["time"] - prev_time
                if delay > 0:  # 確保延遲為正值
                    time.sleep(delay)
                prev_time = action["time"]

                try:
                    # 執行各種行為
                    if action["type"] == "click":
                        x, y, button, pressed = action["x"], action["y"], action["button"], action["pressed"]
                        if pressed:
                            pyautogui.mouseDown(x, y, button=button)
                        else:
                            pyautogui.mouseUp(x, y, button=button)
                    elif action["type"] == "move":
                        x, y = action["x"], action["y"]
                        pyautogui.moveTo(x, y)
                    elif action["type"] == "scroll":
                        dx, dy, x, y = action["dx"], action["dy"], action.get("x", None), action.get("y", None)
                        if x is not None and y is not None:
                            pyautogui.scroll(dy, x, y)
                        else:
                            pyautogui.scroll(dy)
                    elif action["type"] == "keydown":
                        key = action["key"]
                        pyautogui.keyDown(key)
                    elif action["type"] == "keyup":
                        key = action["key"]
                        pyautogui.keyUp(key)

                    # 在動作視窗中顯示執行中的動作
                    simplified_action = f"[{action['type']}]"
                    if action["type"] in ["click", "move"]:
                        simplified_action += f" X: {action.get('x', 'N/A')} Y: {action.get('y', 'N/A')}"
                    elif action["type"] in ["keydown", "keyup"]:
                        simplified_action += f" Key: {action['key']}"
                    elif action["type"] == "scroll":
                        simplified_action += f" DX: {action['dx']} DY: {action['dy']}"
                    actions_display.insert("end", f"{simplified_action}\n")
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

# 執行按鈕
execute_button = ttk.Button(root, text="執行", command=execute_actions)
execute_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5)

# 顯示當前執行的動作代碼
actions_display = ttk.Text(root, height=12, width=64)
actions_display.grid(row=3, column=0, columnspan=3, padx=5, pady=5)

# 啟動全域快捷鍵監聽
listen_for_emergency_stop()

idle_mouse_check()
root.mainloop()