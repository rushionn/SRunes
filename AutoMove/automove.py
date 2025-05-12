# ────────────── 參數/變數說明區塊 ──────────────
# text= 顯示在按鈕或標籤上的文字
# side= 元件對齊位置（LEFT=左, RIGHT=右, TOP=上, BOTTOM=下）
# anchor= 對齊點（'w'=左對齊, 'e'=右對齊, 'center'=置中）
# padx / pady = 元件與其他元件或邊界的水平/垂直間距
# font= 字型設定，例如 ('微軟正黑體', 11)
# insert(位置, 值)= 插入預設文字
# pack(side=..., padx=..., pady=...) = 佈局設定
# Combobox= 下拉選單，values=可選擇的值列表
# Text= 文字框，可顯示日誌
# Entry= 單行輸入框
# BooleanVar / StringVar= 綁定變數
# filedialog.askdirectory() = 彈出資料夾選取視窗
# Progressbar= 進度條小工具
# ScrollableFrame= 自訂可滾動的框架（往下看）
# ────────────────────────────────────────

import os
import shutil
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, Canvas, Frame, Scrollbar, Toplevel
import webbrowser

class ScrollableFrame(tb.Frame):  # 可滾動的外框，包覆其他UI元件
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        canvas = Canvas(self)
        scrollbar = Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tb.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))  # 自動更新滾動區域
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")  # 固定起始位置
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=LEFT, fill="both", expand=True)  # 滿版顯示內容
        scrollbar.pack(side=RIGHT, fill="y")  # 滾動條靠右

class AutoMoveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AutoMove")  # 程式視窗標題
        self.root.geometry("710x620")  # 程式初始大小（寬x高）
        self.style = tb.Style("darkly")  # 使用 darkly 主題樣式
        self.font = ('微軟正黑體', 11)  # 全域字型
        self.extension_entries = []  # 儲存副檔名欄位
        self.dest_entries = []  # 儲存目的資料夾欄位
        self.kind_var = tb.StringVar(value="1")  # 下拉選單預設值
        self.auto_move_var = tb.BooleanVar()  # 自動移動選項

        self.scrollable = ScrollableFrame(self.root)  # 加入可滾動畫面
        self.scrollable.pack(fill="both", expand=True)

        self.container = self.scrollable.scrollable_frame  # 所有UI放在這裡

        self.create_widgets()
        self.root.after(1000, self.check_auto_move)  # 每秒檢查是否自動移動

    def create_widgets(self):
        # ───────── 上方列出清單＋移動＋下拉選單＋副檔名欄位 ────────
        top_frame = tb.Frame(self.container)
        top_frame.pack(pady=5, anchor='w', padx=10)

        tb.Button(top_frame, text="列出清單", command=self.list_files).pack(side=LEFT, padx=5)
        tb.Button(top_frame, text="移動", command=self.move_files).pack(side=LEFT, padx=5)

        kind_box = tb.Combobox(top_frame, textvariable=self.kind_var, width=3, values=[str(i) for i in range(1, 11)])  # 下拉選單：1~10
        kind_box.pack(side=LEFT, padx=(5, 0))
        kind_box.bind("<<ComboboxSelected>>", self.update_dynamic_fields)  # 綁定更新副檔名與目的資料夾欄位

        tb.Label(top_frame, text="種").pack(side=LEFT, padx=(5, 10))

        self.ext_frame = tb.Frame(top_frame)  # 副檔名欄位放這裡
        self.ext_frame.pack(side=LEFT)

        self.dest_frame = tb.Frame(self.container)  # 多目的資料夾列
        self.dest_frame.pack(pady=5, anchor='w', padx=10)

        self.update_dynamic_fields()  # 初始化副檔名與目的地欄位

        tb.Button(top_frame, text="詳細", command=self.show_about).pack(side=RIGHT, padx=5)

        # ─────────來源資料夾───────
        source_row = tb.Frame(self.container)
        source_row.pack(pady=5, anchor='w', padx=10)

        self.source_entry = tb.Entry(source_row, width=40, font=self.font)  # 來源資料夾欄位
        self.source_entry.insert(0, os.path.join(os.path.expanduser("~"), "Downloads"))  # 預設為下載資料夾
        self.source_entry.pack(side=LEFT)

        tb.Button(source_row, text="取出資料夾", command=self.select_source_folder).pack(side=LEFT, padx=5)

        # ─────────延遲時間與自動移動───────
        delay_row = tb.Frame(self.container)
        delay_row.pack(pady=5, anchor='w', padx=10)

        self.delay_entry = tb.Entry(delay_row, width=3, font=self.font)
        self.delay_entry.insert(0, "3")
        self.delay_entry.pack(side=LEFT)

        tb.Label(delay_row, text="秒後").pack(side=LEFT)
        tb.Checkbutton(delay_row, text="自動移動", variable=self.auto_move_var).pack(side=LEFT, padx=10)

        # ─────────日誌視窗───────
        self.log_display = tb.Text(self.container, height=10, width=48, font=self.font, wrap='word')
        self.log_display.pack(pady=10, padx=10)

        # ─────────進度條───────
        self.progress = tb.Progressbar(self.container, orient='horizontal', mode='determinate', length=650)
        self.progress.pack(pady=(0, 10))

    def update_dynamic_fields(self, event=None):
        # 清空舊欄位
        for widget in self.ext_frame.winfo_children():
            widget.destroy()
        for widget in self.dest_frame.winfo_children():
            widget.destroy()
        self.extension_entries.clear()
        self.dest_entries.clear()

        try:
            count = int(self.kind_var.get())
        except ValueError:
            count = 1

        for i in range(count):
            row = tb.Frame(self.ext_frame)
            row.pack(anchor='w')

            entry = tb.Entry(row, width=8, font=self.font)
            entry.insert(0, ".mp4")
            entry.pack(side=LEFT, padx=(0, 5))
            tb.Label(row, text="副檔名").pack(side=LEFT)
            self.extension_entries.append(entry)

            # 對應的目的地欄位與按鈕
            row_dest = tb.Frame(self.dest_frame)
            row_dest.pack(anchor='w', pady=2)

            entry_dest = tb.Entry(row_dest, width=40, font=self.font)
            entry_dest.insert(0, "請選擇檔案要移動到的資料夾")
            entry_dest.pack(side=LEFT)

            btn = tb.Button(row_dest, text="目的資料夾", command=lambda e=entry_dest: self.select_dest_folder(e))
            btn.pack(side=LEFT, padx=5)

            self.dest_entries.append(entry_dest)

    def select_source_folder(self):
        folder = filedialog.askdirectory(initialdir=self.source_entry.get())
        if folder:
            self.source_entry.delete(0, 'end')
            self.source_entry.insert(0, folder)
            self.log(f"選擇來源資料夾：{folder}")

    def select_dest_folder(self, entry):
        folder = filedialog.askdirectory(initialdir=entry.get())
        if folder:
            entry.delete(0, 'end')
            entry.insert(0, folder)
            self.log(f"選擇目的資料夾：{folder}")

    def list_files(self):
        path = self.source_entry.get()
        extensions = [e.get().strip() for e in self.extension_entries]
        if not os.path.isdir(path):
            self.log("來源路徑無效")
            return

        all_files = []
        for ext in extensions:
            all_files += [f for f in os.listdir(path) if f.endswith(ext)]

        if not all_files:
            self.log(f"{path} 中沒有找到符合副檔名的檔案")
            return

        self.log(f"在 {path} 找到以下檔案：")
        total_size = 0
        for idx, f in enumerate(all_files, 1):
            full = os.path.join(path, f)
            size = os.path.getsize(full)
            total_size += size
            self.log(f"{idx}－{self.format_size(size)}－{f}")
        self.log(f"共找到 {len(all_files)} 個檔案，總容量 {self.format_size(total_size)}")

    def move_files(self):
        src = self.source_entry.get()
        extensions = [e.get().strip() for e in self.extension_entries]

        all_files = []
        for ext in extensions:
            all_files += [f for f in os.listdir(src) if f.endswith(ext)]

        total = len(all_files)
        self.progress['maximum'] = total
        self.progress['value'] = 0
        moved = failed = 0

        for idx, f in enumerate(all_files, 1):
            ext_index = next((i for i, e in enumerate(extensions) if f.endswith(e)), 0)
            dst = self.dest_entries[ext_index].get() if ext_index < len(self.dest_entries) else self.dest_entries[0].get()

            try:
                shutil.move(os.path.join(src, f), os.path.join(dst, f))
                self.log(f"{idx}－成功移動：{f}")
                moved += 1
            except Exception as e:
                self.log(f"{idx}－移動失敗：{f}（錯誤：{e}）")
                failed += 1

            self.progress['value'] = idx
            self.root.update_idletasks()

        self.log(f"移動完成：{moved} 成功，{failed} 失敗")

    def check_auto_move(self):
        if self.auto_move_var.get():
            try:
                delay = int(self.delay_entry.get())
            except ValueError:
                delay = 3
            self.root.after(delay * 1000, self.move_files)
        self.root.after(1000, self.check_auto_move)

    def format_size(self, size):
        if size < 1024 * 1024:
            return f"{round(size / 1024)}KB"
        elif size < 1024 * 1024 * 1024:
            return f"{round(size / (1024 * 1024), 1)}MB"
        else:
            return f"{round(size / (1024 * 1024 * 1024), 1)}GB"

    def log(self, message):
        self.log_display.insert('end', message + '\n')
        self.log_display.see('end')

    def show_about(self):
        about_window = Toplevel(self.root)
        about_window.title("About")
        about_window.geometry("500x350")
        about_window.configure(background='#172B4B')

        description_label = tb.Label(about_window, text="AutoMove將會節省經常分類檔案的時間",  font=('微軟正黑體', 12), justify='left')
        description_label.pack(pady=10)

        website_label = tb.Label(about_window, text="造訪網站",  cursor="hand2", )
        website_label.pack(pady=5)
        website_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://"))

        contact_label = tb.Label(about_window, text="聯絡",  cursor="hand2", )
        contact_label.pack(pady=5)
        contact_label.bind("<Button-1>", lambda e: webbrowser.open_new("mailto: "))

        author_label = tb.Label(about_window, text="Creat By Lucien",  font=('微軟正黑體', 12))
        author_label.pack(pady=10)

        close_button = tb.Button(about_window, text="關閉", command=about_window.destroy)
        close_button.pack(pady=10)

# ────────────── 主程式入口 ──────────────
if __name__ == "__main__":
    root = tb.Window(themename="darkly")  # 啟用 ttkbootstrap 視窗與主題
    app = AutoMoveApp(root)  # 建立主應用程式
    root.mainloop()  # 執行視窗循環