import pyautogui
import keyboard
import json
import time
import threading
from pynput.mouse import Listener as MouseListener
from pynput.mouse import Controller as MouseController
from pynput.keyboard import Listener as KeyboardListener
from pynput.keyboard import Controller as KeyboardController
from tkinter import Tk, Button, Label, Checkbutton, IntVar, Frame, Text, Scrollbar, Scale, HORIZONTAL, Entry, filedialog
from datetime import datetime
import os
import sys
import random

# 儲存錄製的操作
operations = []

# Yuna特色：隨機亂飛或錯誤操作
yuna_feature_enabled = False

# 控制回放延遲
playback_delay = 0.1  # 默認延遲

# 當前操作顯示區
current_action = ""

# 回放次數
replay_count = 0

# 更新動作顯示區的內容
def update_action(action_text):
    global current_action
    current_action = action_text
    action_text_widget.delete(1.0, "end")
    action_text_widget.insert("insert", current_action + "\n")

# 捕捉滑鼠移動的回調函數
def on_move(x, y):
    timestamp = time.time() - start_time
    operations.append({
        "type": "move", "x": x, "y": y, "time": timestamp
    })
    update_action(f"滑鼠移動到: ({x}, {y}) 時間戳記: {timestamp:.4f}")

# 捕捉滑鼠點擊的回調函數
def on_click(x, y, button, pressed):
    if pressed:
        timestamp = time.time() - start_time
        operations.append({
            "type": "click", "x": x, "y": y, "button": button.name, "time": timestamp
        })
        update_action(f"滑鼠點擊: ({x}, {y}) 按鈕: {button.name} 時間戳記: {timestamp:.4f}")

# 捕捉滑鼠滾輪的回調函數
def on_scroll(x, y, dx, dy):
    timestamp = time.time() - start_time
    operations.append({
        "type": "scroll", "x": x, "y": y, "dx": dx, "dy": dy, "time": timestamp
    })
    update_action(f"滑鼠滾輪: ({dx}, {dy}) 時間戳記: {timestamp:.4f}")

# 捕捉鍵盤按鍵事件
def on_press(key):
    try:
        timestamp = time.time() - start_time
        operations.append({"type": "keyboard", "key": key.char, "time": timestamp})
        update_action(f"按下鍵: {key.char} 時間戳記: {timestamp:.4f}")
    except AttributeError:
        timestamp = time.time() - start_time
        operations.append({"type": "keyboard", "key": str(key), "time": timestamp})
        update_action(f"按下鍵: {key} 時間戳記: {timestamp:.4f}")

# 錄製操作的函數
def record_operations():
    global operations
    update_action("錄製開始！按下 F10 來停止錄製")
    start_time = time.time()  # 記錄開始時間

    # 設定滑鼠監聽器
    mouse_listener = MouseListener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
    mouse_listener.start()

    # 設定鍵盤監聽器
    keyboard_listener = KeyboardListener(on_press=on_press)
    keyboard_listener.start()

    while True:
        if keyboard.is_pressed('F10'):  # F10 停止錄製
            update_action("停止錄製。")
            save_operations()  # 自動保存
            break

        time.sleep(0.1)

# 儲存操作至 JSON 檔案
def save_operations():
    timestamp = datetime.now().strftime("%d-%m-%S")  # 使用當前時間作為檔案名稱
    file_name = f"operations_{timestamp}.json"
    with open(file_name, 'w') as f:
        json.dump(operations, f)
    update_action(f"操作已儲存至 {file_name}！")

# 回放操作的函數
def replay_operations():
    global replay_count
    update_action("回放開始！")
    start_time = time.time()  # 回放開始時間
    replay_count += 1

    for op in operations:
        elapsed_time = op["time"]  # 距離回放開始的時間
        time.sleep(elapsed_time)  # 根據時間戳延遲播放

        if op['type'] == 'move':
            if yuna_feature_enabled and random.random() < 0.1:  # 開啟 Yuna 特色功能，隨機亂飛
                random_offset = random.randint(-100, 100)
                pyautogui.moveTo(op['x'] + random_offset, op['y'] + random_offset, duration=playback_delay)
                update_action(f"Yuna 隨機亂飛！")
            else:
                pyautogui.moveTo(op['x'], op['y'], duration=playback_delay)
        
        elif op['type'] == 'click':
            pyautogui.click(op['x'], op['y'], button=op['button'])
            update_action(f"回放點擊: {op['button']} at ({op['x']}, {op['y']})")
        
        elif op['type'] == 'keyboard':
            keyboard.press(op['key'])
            keyboard.release(op['key'])
            update_action(f"回放按下鍵: {op['key']}")
        
        elif op['type'] == 'scroll':
            pyautogui.scroll(op['dy'])
            update_action(f"回放滾輪: {op['dy']}")

    update_action(f"回放結束！回放次數: {replay_count}")

# 回放速度的調整
def update_playback_delay(val):
    global playback_delay
    playback_delay = float(val) / 100  # 回放速度設為 100 時為正常速度
    update_action(f"回放延遲設定為: {playback_delay}秒")

# 讀取操作檔案
def load_operations():
    global operations
    file_path = filedialog.askopenfilename(title="選擇操作檔案", filetypes=[("JSON Files", "*.json")])
    if file_path:
        with open(file_path, 'r') as f:
            operations = json.load(f)
        update_action(f"已讀取檔案: {file_path.split('/')[-1]}")

# UI 控制
def start_recording():
    global operations
    operations = []  # 清空以前的錄製
    recording_thread = threading.Thread(target=record_operations)
    recording_thread.start()
    start_button.config(state="disabled")  # 禁用開始錄製按鈕
    stop_button.config(state="normal")  # 啟用停止錄製按鈕

def stop_recording():
    update_action("停止錄製中...")
    save_operations()  # 儲存錄製結果
    start_button.config(state="normal")  # 啟用開始錄製按鈕
    stop_button.config(state="disabled")  # 禁用停止錄製按鈕

def start_replaying():
    replay_thread = threading.Thread(target=replay_operations)
    replay_thread.start()

def toggle_yuna_feature():
    global yuna_feature_enabled
    yuna_feature_enabled = not yuna_feature_enabled
    update_action(f"Yuna 特色 {'開啟' if yuna_feature_enabled else '關閉'}")

def on_close():
    sys.exit()

# UI 配置
def setup_ui():
    global action_text_widget, start_button, stop_button, playback_speed_entry, replay_count_entry, current_file_label
    root = Tk()
    root.title("Yuna 滑鼠鍵盤錄製工具")
    root.geometry("700x500")
    
    # UI 配色 (參考 SRunes 及 Yuna 風格)
    root.configure(bg="#3E4A89")
    
    # 設定關閉事件
    root.protocol("WM_DELETE_WINDOW", on_close)

    # 標題區
    title_frame = Frame(root, bg="#3E4A89")
    title_frame.pack(pady=10)
    Label(title_frame, text="Yuna 滑鼠鍵盤錄製工具", font=("Arial", 16), fg="white", bg="#3E4A89").pack()

    # 控制區
    control_frame = Frame(root, bg="#3E4A89")
    control_frame.pack(pady=10)

    start_button = Button(control_frame, text="開始錄製 (F9)", command=start_recording, bg="#FF6F61", fg="white")
    start_button.pack(side="left", padx=5)

    stop_button = Button(control_frame, text="停止錄製 (F10)", command=stop_recording, bg="#FF6F61", fg="white", state="disabled")
    stop_button.pack(side="left", padx=5)

    replay_button = Button(control_frame, text="回放 (F8)", command=start_replaying, bg="#55B6A2", fg="white")
    replay_button.pack(side="left", padx=5)

    replay_count_label = Label(control_frame, text="回放次數:", bg="#3E4A89", fg="white")
    replay_count_label.pack(side="left", padx=5)
    
    replay_count_entry = Entry(control_frame, width=6, font=("Arial", 12), justify="center")
    replay_count_entry.insert(0, "0")
    replay_count_entry.config(state="readonly")
    replay_count_entry.pack(side="left", padx=5)

    load_button = Button(control_frame, text="讀取檔案", command=load_operations, bg="#9B59B6", fg="white")
    load_button.pack(side="left", padx=5)

    current_file_label = Label(control_frame, text="當前檔案: 無", bg="#3E4A89", fg="white")
    current_file_label.pack(side="left", padx=5)

    speed_label = Label(root, text="回放速度 (0-500):", bg="#3E4A89", fg="white")
    speed_label.pack(pady=5)

    playback_speed_entry = Entry(root, width=6, font=("Arial", 12), justify="center")
    playback_speed_entry.insert(0, "100")
    playback_speed_entry.pack(pady=5)
    playback_speed_entry.bind("<Return>", lambda event: update_playback_delay(playback_speed_entry.get()))

    # 動作顯示區
    action_frame = Frame(root, bg="#3E4A89")
    action_frame.pack(pady=10, fill="both", expand=True)
    action_text_widget = Text(action_frame, height=6, wrap="word", font=("Arial", 12), bg="#2E3B5E", fg="white", bd=0, padx=10, pady=10)
    action_text_widget.pack(fill="both", expand=True)
    scrollbar = Scrollbar(action_text_widget)
    scrollbar.pack(side="right", fill="y")
    action_text_widget.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=action_text_widget.yview)

    root.mainloop()

if __name__ == "__main__":
    setup_ui()