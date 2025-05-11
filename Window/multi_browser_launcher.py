import sys
import subprocess
import time
import os
from PyQt5 import QtWidgets, QtCore
import win32gui
import win32con
import win32process

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIRS = [
    r"C:\Temp\profile1",
    r"C:\Temp\profile2",
    r"C:\Temp\profile3",
    r"C:\Temp\profile4",
]
DEFAULT_URL = "https://openai.com/"

class ChromeLoader(QtCore.QThread):
    window_ready = QtCore.pyqtSignal(int, int)  # 傳 (idx, hwnd)

    def __init__(self, user_data_dir, parent_winid, idx, url):
        super().__init__()
        self.user_data_dir = user_data_dir
        self.parent_winid = parent_winid
        self.idx = idx
        self.url = url
        self.hwnd = None
        self.process = None

    def run(self):
        args = [
            CHROME_PATH,
            f'--user-data-dir={self.user_data_dir}',
            '--new-window',
            '--no-first-run',
            '--no-default-browser-check',
            self.url
        ]
        self.process = subprocess.Popen(args)
        time.sleep(1)

        def enum_callback(hwnd, pid):
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if found_pid == pid and win32gui.IsWindowVisible(hwnd):
                self.hwnd = hwnd
                return False
            return True

        retry = 10
        while self.hwnd is None and retry > 0:
            win32gui.EnumWindows(lambda hwnd, _: enum_callback(hwnd, self.process.pid), None)
            time.sleep(0.5)
            retry -= 1

        if self.hwnd:
            win32gui.SetParent(self.hwnd, self.parent_winid)
            style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_STYLE)
            style = style & ~win32con.WS_POPUP | win32con.WS_CHILD
            win32gui.SetWindowLong(self.hwnd, win32con.GWL_STYLE, style)

            self.window_ready.emit(self.idx, self.hwnd)

class BrowserWidget(QtWidgets.QWidget):
    def __init__(self, user_data_dir, idx, url, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.user_data_dir = user_data_dir
        self.url = url
        self.chrome_hwnd = None
        self.setAttribute(QtCore.Qt.WA_NativeWindow, True)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)

        self.loader = ChromeLoader(self.user_data_dir, int(self.winId()), self.idx, self.url)
        self.loader.window_ready.connect(self.on_window_ready)
        self.loader.start()

        # 加個定時器，每 500ms 強制調整 Chrome 視窗位置
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.force_reposition)
        self.timer.start(500)

    def on_window_ready(self, idx, hwnd):
        self.chrome_hwnd = hwnd
        self.force_reposition()

    def navigate(self, url):
        if self.loader.process:
            self.loader.process.terminate()
            self.loader.wait()
            self.loader = ChromeLoader(self.user_data_dir, int(self.winId()), self.idx, url)
            self.loader.window_ready.connect(self.on_window_ready)
            self.loader.start()

    def force_reposition(self):
        if self.chrome_hwnd:
            rect = self.rect()
            win32gui.MoveWindow(
                self.chrome_hwnd,
                0,
                0,
                rect.width(),
                rect.height(),
                True
            )

    def resizeEvent(self, event):
        self.force_reposition()

    def closeEvent(self, event):
        if self.loader.process:
            self.loader.process.terminate()
            self.loader.process.wait()

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi Google Accounts Browser")
        self.resize(1280, 800)

        self.browsers = []
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QtWidgets.QGridLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

        for idx, user_dir in enumerate(USER_DATA_DIRS):
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)
            browser = BrowserWidget(user_dir, idx, DEFAULT_URL)
            self.browsers.append(browser)
            row = idx // 2
            col = idx % 2
            self.layout.addWidget(browser, row, col)

        self.setup_menu()

    def setup_menu(self):
        menubar = self.menuBar()

        browser_menu = menubar.addMenu("瀏覽器管理")
        navigate_action = QtWidgets.QAction("切換網址", self)
        navigate_action.triggered.connect(self.change_url)
        browser_menu.addAction(navigate_action)

        add_action = QtWidgets.QAction("新增瀏覽器", self)
        add_action.triggered.connect(self.add_browser)
        browser_menu.addAction(add_action)

        remove_action = QtWidgets.QAction("關閉最後一個瀏覽器", self)
        remove_action.triggered.connect(self.remove_browser)
        browser_menu.addAction(remove_action)

    def change_url(self):
        url, ok = QtWidgets.QInputDialog.getText(self, "輸入網址", "網址：", text="https://")
        if ok and url:
            for browser in self.browsers:
                browser.navigate(url)

    def add_browser(self):
        idx = len(self.browsers)
        new_user_dir = f"C:/Temp/profile{idx+1}"
        if not os.path.exists(new_user_dir):
            os.makedirs(new_user_dir)
        browser = BrowserWidget(new_user_dir, idx, DEFAULT_URL)
        self.browsers.append(browser)
        row = idx // 2
        col = idx % 2
        self.layout.addWidget(browser, row, col)

    def remove_browser(self):
        if self.browsers:
            browser = self.browsers.pop()
            browser.close()
            browser.setParent(None)

    def closeEvent(self, event):
        for browser in self.browsers:
            browser.close()
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
