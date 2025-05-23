import os
import sys
import subprocess
import shutil

def build_windows():
    # Install required packages
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Create the spec file content
    spec_content = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['gmail_labeler_gui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Gmail Labeler',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'  # You'll need to add an icon file
)
"""
    
    # Write the spec file
    with open("gmail_labeler.spec", "w") as f:
        f.write(spec_content)
    
    # Run PyInstaller with just the spec file
    subprocess.check_call([
        "pyinstaller",
        "--clean",
        "gmail_labeler.spec"
    ])
    
    # Create a README file in the dist directory
    readme_content = """Gmail Labeler
============

A tool to automatically organize your Gmail inbox by labeling old unread emails.

First Run Instructions:
1. Run 'Gmail Labeler.exe'
2. Click 'Authenticate with Gmail'
3. Follow the authentication process in your web browser
4. Once authenticated, you can start using the application

Note: Keep your credentials.json file in the same directory as the executable.
"""
    
    with open(os.path.join("dist", "README.txt"), "w") as f:
        f.write(readme_content)
    
    print("Build completed! The executable can be found in the 'dist' directory.")

if __name__ == "__main__":
    build_windows() 