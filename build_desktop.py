"""Produce a self-contained Windows EXE with the English speech model."""
import subprocess
import sys
from pathlib import Path
from make_icon import make_icons

root = Path(__file__).resolve().parent
models = list((root / '.models' / 'models--Systran--faster-whisper-base.en' / 'snapshots').glob('*/model.bin'))
if not models:
    raise SystemExit('Run automatic recognition once to download the base.en model before building.')

make_icons()
icon = root / 'app.ico'
command = [sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed',
           '--distpath',str(root / 'dist' / 'Flow'),
           '--name','Flow','--icon',str(icon),
           '--add-data',f'{root / "web"};web',
           '--add-data',f'{icon};.',
           '--add-data',f'{models[0].parent};model',
           '--add-data',f'{root / "sample.mp4"};.', '--hidden-import','clr']
for module in ['webview','faster_whisper','ctranslate2','av','onnxruntime','tokenizers','pythonnet','clr_loader']:
    command.extend(['--collect-all',module])
command.append(str(root / 'desktop.py'))
subprocess.run(command,cwd=root,check=True)
