import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

cmd = [PY, '-m', 'PyInstaller', '--clean', '--onefile', '--noconsole', '--name', 'LiveTranslator', '--distpath', os.path.join(ROOT, 'dist'), '--workpath', os.path.join(ROOT, 'build'), '--specpath', ROOT, '--collect-all', 'faster_whisper', '--collect-all', 'translatepy', '--hidden-import', 'sounddevice', '--hidden-import', 'ctranslate2', 'main.py']
print('Building EXE...')
subprocess.check_call(cmd, cwd=ROOT)
print('Done. EXE is in:', os.path.join(ROOT, 'dist', 'LiveTranslator.exe'))
