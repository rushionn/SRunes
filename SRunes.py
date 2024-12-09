import os
import time
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, StringVar
from pynput import mouse, keyboard

# 全域變數
recorded_actions = []
is_recording = False
is_paused = False
recording_start_time = None
recordings_folder = "recordings"

# 確保音檔資料夾存在
if not os.path.exists(recordings_folder):
    os.makedirs(recordings_folder)

# 錄製邏輯
def start_recording():
    global is_recording, recorded_actions, recording_start_time, is_paused
    is_recording = True
    is_paused = False
    recorded_actions = []
    recording_start_time = time.time()
    log_code("開始錄製。\n")

def pause_recording():
    global is_paused
    if is_recording:
        is_paused = not is_paused
        status = "暫停" if is_paused else "繼續"
        log_code(f"錄製 {status}。\n")

def stop_recording():
    global is_recording, is_paused
    is_recording = False
    is_paused = False
    log_code("錄製停止。\n")

def save_recording():
    if not recorded_actions:
        log_code("沒有錄製可供保存。\n")
        return
    file_path = os.path.join(recordings_folder, f"recording_{int(time.time())}.txt")
    with open(file_path, "w") as f:
        for action in recorded_actions:
            f.write(f"{action}\n")
    log_code(f"錄製已保存到 {file_path}\n")
    update_script_list()

def log_code(message):
    code_display.insert(tk.END, message)
    code_display.see(tk.END)

def update_script_list():
    # 更新當前腳本的下拉選單
    files = os.listdir(recordings_folder)
    script_list.set('')
    script_menu['values'] = [f for f in files if f.endswith('.txt')]
    if script_menu['values']:
        script_list.set(script_menu['values'][-1])  # 設置為最後一個檔案

def execute_recording():
    file_path = script_list.get()  # 使用選擇的文件
    if not file_path:
        log_code("請選擇一個檔案來執行。\n")
        return
    full_path = os.path.join(recordings_folder, file_path)
    with open(full_path, "r") as f:
        for line in f:
            action = eval(line.strip())
            action_type, action_detail, *args = action
            
            if action_type == '鍵盤':
                if action_detail == '按下':
                    keyboard.Controller().press(args[0])
                elif action_detail == '放開':
                    keyboard.Controller().release(args[0])
            elif action_type == '滑鼠':
                if action_detail == '點擊':
                    x, y, button_name, pressed = args[0]
                    button = mouse.Button.left if button_name == 'left' else mouse.Button.right
                    if pressed:
                        mouse.Controller().click(button, 1)
                elif action_detail == '移動':
                    x, y = args[0]
                    mouse.Controller().position = (x, y)
                elif action_detail == '滾動':
                    x, y, dx, dy = args[0]
                    mouse.Controller().scroll(dx, dy)

# 事件監控
def on_press(key):
    global recorded_actions, is_recording, is_paused
    if is_recording and not is_paused:
        try:
            recorded_actions.append(('鍵盤', '按下', key.char, time.time() - recording_start_time))
        except AttributeError:
            recorded_actions.append(('鍵盤', '按下', str(key), time.time() - recording_start_time))

def on_release(key):
    global recorded_actions, is_recording, is_paused
    if is_recording and not is_paused:
        try:
            recorded_actions.append(('鍵盤', '放開', key.char, time.time() - recording_start_time))
        except AttributeError:
            recorded_actions.append(('鍵盤', '放開', str(key), time.time() - recording_start_time))

def on_move(x, y):
    global recorded_actions, is_recording, is_paused
    if is_recording and not is_paused:
        recorded_actions.append(('滑鼠', '移動', (x, y), time.time() - recording_start_time))

def on_click(x, y, button, pressed):
    global recorded_actions, is_recording, is_paused
    if is_recording and not is_paused:
        recorded_actions.append(('滑鼠', '點擊', (x, y, button.name, pressed), time.time() - recording_start_time))

def on_scroll(x, y, dx, dy):
    global recorded_actions, is_recording, is_paused
    if is_recording and not is_paused:
        recorded_actions.append(('滑鼠', '滾動', (x, y, dx, dy), time.time() - recording_start_time))

# 啟動監控
def start_listeners():
    mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
    keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)

    mouse_listener.start()
    keyboard_listener.start()

    mouse_listener.join()
    keyboard_listener.join()

# 啟動監聽執行緒
listener_thread = threading.Thread(target=start_listeners, daemon=True)
listener_thread.start()

# 設定 GUI
app = tk.Tk()
app.title("鍵盤與滑鼠操作錄製器")
app.geometry("800x600")

# 當前腳本選擇框
script_list = StringVar()
script_menu = tk.OptionMenu(app, script_list, '')
script_menu.pack(pady=10)

# 按鈕區域
frame = tk.Frame(app)
frame.pack(pady=10)

start_button = tk.Button(frame, text="錄製", command=start_recording, width=10)
start_button.grid(row=0, column=0, padx=10)

pause_button = tk.Button(frame, text="暫停/繼續", command=pause_recording, width=10)
pause_button.grid(row=0, column=1, padx=10)

stop_button = tk.Button(frame, text="停止", command=stop_recording, width=10)
stop_button.grid(row=0, column=2, padx=10)

save_button = tk.Button(frame, text="存檔", command=save_recording, width=10)
save_button.grid(row=0, column=3, padx=10)

execute_button = tk.Button(frame, text="執行", command=execute_recording, width=10)
execute_button.grid(row=0, column=4, padx=10)

# 代碼顯示區域
code_display = scrolledtext.ScrolledText(app, height=25, width=95, state='normal')
code_display.pack(pady=10)
code_display.insert(tk.END, "代碼執行結果會顯示於此。\n")

# 更新腳本列表
# update_script_list()

# 啟動主循環
app.mainloop()