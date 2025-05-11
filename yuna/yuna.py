import json
import time
import pyautogui
import threading
import datetime
import os
import keyboard as kb  # 新的鍵盤模組
from pynput import mouse
from pathlib import Path
import ttkbootstrap as ttk
from tkinter import filedialog
from typing import List, Dict, Any, Optional

class AutomationScriptTool:
    def __init__(self):
        self.root = ttk.Window(themename="superhero")
        self.root.title("自動化腳本工具")
        self.MOUSE_MOVE_THRESHOLD = 50
        self.last_mouse_position = (0, 0)
        self.actions: List[Dict] = []
        self.recording = False
        self.paused = False
        self.paused_playback = False
        self.current_file = ""
        self.mouse_listener = None
        self.repeat_times = 1
        self.playback_delay = 0.0
        self.replay_speed = 1.0
        self.start_time = 0.0
        self.log_dir = "logs"
        self.KEY_MAP = {
            "shift": "shift", "shift_r": "shift",
            "ctrl": "ctrl", "ctrl_r": "ctrl",
            "alt": "alt", "alt_r": "alt",
            "enter": "enter", "space": "space", "tab": "tab",
            "f9": "f9", "f10": "f10", "f11": "f11", "f12": "f12",
        }
        self.active_modifiers = []
        os.makedirs(self.log_dir, exist_ok=True)
        self._setup_ui()
        self._setup_global_keys()

    def _setup_ui(self):
        button_width = 15
        ttk.Button(self.root, text="開始錄製 (F9)", command=self.start_recording, width=button_width).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(self.root, text="停止錄製 (F10)", command=self.stop_recording, width=button_width).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(self.root, text="選擇檔案", command=self.choose_file, width=button_width).grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        self.repeat_entry = ttk.Entry(self.root, width=6)
        self.repeat_entry.insert(0, "1")
        self.repeat_entry.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(self.root, text="執行回放 (F12)", command=self.execute_actions, width=button_width).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.pause_btn = ttk.Button(self.root, text="暫停回放 (F11)", command=self.toggle_pause_playback, width=button_width)
        self.pause_btn.grid(row=1, column=2, padx=5, pady=5, sticky="ew")
        self.file_label = ttk.Label(self.root, text="尚未選擇檔案")
        self.file_label.grid(row=2, column=0, columnspan=3, pady=5)
        self.display = ttk.Text(self.root, height=15, width=70)
        self.display.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        self.root.grid_columnconfigure((0, 1, 2), weight=1)
        self.root.grid_rowconfigure(3, weight=1)
        self.root.protocol("WM_DELETE_WINDOW", self.cleanup)

    def _setup_global_keys(self):
        kb.on_press_key("f9", lambda _: self.start_recording(), suppress=False)
        kb.on_press_key("f10", lambda _: self.stop_recording(), suppress=False)
        kb.on_press_key("f11", lambda _: self.toggle_pause_playback(), suppress=False)
        kb.on_press_key("f12", lambda _: self.execute_actions(), suppress=False)

    def save_actions(self) -> str:
        if not self.actions: return ""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
        fn = f"{self.log_dir}/script_{timestamp}.json"
        with open(fn, "w", encoding="utf-8") as f:
            json.dump(self.actions, f, ensure_ascii=False, indent=4)
        self._msg(f"已儲存至 {fn}")
        return fn

    def load_actions(self, fn: str) -> List[Dict]:
        if Path(fn).exists():
            with open(fn, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def on_click(self, x: int, y: int, button: mouse.Button, pressed: bool):
        if self.recording and not self.paused:
            elapsed_time = round(time.time() - self.start_time, 3)
            action = {"type": "click", "x": x, "y": y, "button": button.name, "pressed": pressed, "time": elapsed_time}
            self.actions.append(action)
            self._update_display(action)

    def on_move(self, x: int, y: int):
        if self.recording and not self.paused:
            elapsed_time = round(time.time() - self.start_time, 3)
            distance = ((x - self.last_mouse_position[0])**2 + (y - self.last_mouse_position[1])**2)**0.5
            if distance >= self.MOUSE_MOVE_THRESHOLD:
                action = {"type": "move", "x": x, "y": y, "time": elapsed_time}
                self.actions.append(action)
                self._update_display(action)
                self.last_mouse_position = (x, y)

    def on_key_press(self, event):
        if self.recording and not self.paused:
            key = event.name.lower()
            if key in {"f9", "f10", "f11", "f12"}:  # 避免記錄控制鍵
                return
            t = round(time.time() - self.start_time, 3)
            k = self.KEY_MAP.get(key, key)
            if k in {"shift", "ctrl", "alt"}:
                self.active_modifiers.append(k)
                action = {"type": "keydown", "key": k, "time": t}
            elif self.active_modifiers:
                action = {"type": "hotkey", "keys": self.active_modifiers + [k], "time": t}
                self.active_modifiers.clear()
            else:
                action = {"type": "keydown", "key": k, "time": t}
            self.actions.append(action)
            self._msg(action)

    def on_key_release(self, event):
        if self.recording and not self.paused:
            key = event.name.lower()
            if key in {"f9", "f10", "f11", "f12"}:
                return
            t = round(time.time() - self.start_time, 3)
            k = self.KEY_MAP.get(key, key)
            if k not in {"shift", "ctrl", "alt"} or not self.active_modifiers:
                action = {"type": "keyup", "key": k, "time": t}
                self.actions.append(action)
                self._msg(action)

    def execute_actions(self):
        if not self.current_file:
            self._msg("未選擇檔案")
            return
        acts = self.load_actions(self.current_file)
        if acts:
            self.display.delete(1.0, "end")
            try:
                self.repeat_times = int(self.repeat_entry.get() or 1)
            except ValueError:
                self.repeat_times = 1
            self._msg(f"開始回放 {self.repeat_times} 次")
            threading.Thread(target=self._replay_actions, args=(acts,), daemon=True).start()

    def _replay_actions(self, actions: List[Dict]):
        held = set()
        for _ in range(self.repeat_times):
            start = time.time()
            for a in actions:
                while self.paused_playback:
                    time.sleep(0.1)
                delay = max(0, a["time"] - (time.time() - start) + self.playback_delay) / self.replay_speed
                time.sleep(delay)
                try:
                    if a["type"] == "click":
                        pyautogui.moveTo(a["x"], a["y"], duration=0.01)
                        if a["pressed"]:
                            pyautogui.mouseDown(button=a["button"])
                        else:
                            pyautogui.mouseUp(button=a["button"])
                    elif a["type"] == "move":
                        pyautogui.moveTo(a["x"], a["y"], duration=0.01)
                    elif a["type"] == "hotkey":
                        for key in a["keys"]:
                            kb.press(key)
                        time.sleep(0.05)  # 確保組合鍵被識別
                        for key in reversed(a["keys"]):
                            kb.release(key)
                    elif a["type"] == "keydown":
                        kb.press(a["key"])
                        held.add(a["key"])
                        time.sleep(0.01)  # 模擬物理按鍵間隔
                    elif a["type"] == "keyup":
                        kb.release(a["key"])
                        held.discard(a["key"])
                except Exception as e:
                    self._msg(f"回放錯誤: {e}")
            self._msg("回放完成一輪")
            for k in list(held):
                kb.release(k)
            held.clear()
        self._msg("回放結束")

    def start_recording(self):
        if not self.recording:
            self.actions.clear()
            self.recording = True
            self.paused = False
            self.start_time = time.time()
            self.last_mouse_position = pyautogui.position()
            self._msg("開始錄製...")
            self.mouse_listener = mouse.Listener(on_click=self.on_click, on_move=self.on_move)
            kb.hook(self.on_key_press)  # 使用 keyboard 模組監聽鍵盤
            kb.on_release(self.on_key_release)
            self.mouse_listener.start()

    def stop_recording(self):
        if self.recording:
            self.recording = False
            if self.mouse_listener:
                self.mouse_listener.stop()
            kb.unhook_all()  # 停止所有鍵盤鉤子
            fn = self.save_actions()
            if fn and Path(fn).exists():
                self.current_file = fn
                self.file_label.config(text=os.path.basename(fn))
            self._msg("錄製完成")

    def choose_file(self):
        fn = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], initialdir=self.log_dir)
        if fn:
            self.current_file = fn
            self.file_label.config(text=os.path.basename(fn))
            self.display.delete(1.0, "end")

    def toggle_pause_playback(self):
        self.paused_playback = not self.paused_playback
        self.pause_btn.config(text="繼續回放 (F11)" if self.paused_playback else "暫停回放 (F11)")

    def _update_display(self, action: Dict):
        try:
            self.display.insert("end", f"{action}\n")
            self.display.see("end")
        except:
            pass

    def _msg(self, msg: str):
        try:
            self.display.insert("end", f"{msg}\n")
            self.display.see("end")
        except:
            pass

    def run(self):
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"運行錯誤: {e}")
            self.cleanup()

    def cleanup(self):
        try:
            if self.mouse_listener and self.mouse_listener.running:
                self.mouse_listener.stop()
            kb.unhook_all()
            for k in ["ctrl", "shift", "alt"]:
                kb.release(k)
            self.root.destroy()
        except:
            pass

if __name__ == "__main__":
    try:
        tool = AutomationScriptTool()
        tool.run()
    except Exception as e:
        print(f"程式錯誤: {e}")
        input("按 Enter 退出...")
    finally:
        try:
            tool.cleanup()
        except:
            pass