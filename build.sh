#!/bin/bash

export PYTHONPATH="$PWD:$PYTHONPATH"

rm -rf build/ dist/ __pycache__/
rm -f *.spec

pyinstaller \
  --onefile \
  --windowed \
  --name "bili-cookies-extractor" \
  --hidden-import=DrissionPage \
  --hidden-import=DrissionPage._base \
  --hidden-import=DrissionPage._pages \
  --hidden-import=DrissionPage._elements \
  --hidden-import=DrissionPage._units \
  --hidden-import=requests \
  --hidden-import=lxml \
  --hidden-import=lxml.etree \
  --hidden-import=lxml.html \
  --hidden-import=websocket \
  --hidden-import=websocket_client \
  --hidden-import=tkinter \
  --hidden-import=tkinter.ttk \
  --hidden-import=tkinter.scrolledtext \
  --hidden-import=tkinter.messagebox \
  --hidden-import=tkinter.filedialog \
  --hidden-import=json \
  --hidden-import=base64 \
  --hidden-import=shutil \
  --hidden-import=platform \
  --hidden-import=tempfile \
  --hidden-import=threading \
  --hidden-import=subprocess \
  --hidden-import=pathlib \
  --hidden-import=datetime \
  --hidden-import=os \
  --hidden-import=sys \
  --hidden-import=time \
  --optimize=2 \
  bce.py

chmod +x dist/bili-cookies-extractor

echo "succeed"
ls -lh dist/bili-cookies-extractor