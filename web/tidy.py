import os
import time

from pathlib import Path

TOO_LONG = 600

if __name__ == '__main__':
    while True:
        for file in os.listdir(Path('upload')):
            if file != 'image' and os.stat(Path('upload', file)).st_mtime > TOO_LONG:
                os.remove(Path('upload', file))

        for file in os.listdir(Path('upload/image')):
            if os.stat(Path('upload/image', file)).st_mtime > TOO_LONG:
                os.remove(Path('upload/image', file))
        
        time.sleep(TOO_LONG)
