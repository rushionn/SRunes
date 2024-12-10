from pynput import mouse

def on_move(x, y):
    try:
        print(f'Mouse moved to ({x}, {y})')
    except Exception as e:
        print(f'Error on move: {e}')

# 監聽器
with mouse.Listener(on_move=on_move) as listener:
    listener.join()