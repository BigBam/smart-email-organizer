import os
import platform
import subprocess
import shutil

def build():
    # Create icons first
    print("Creating icons...")
    subprocess.run(['python', 'create_icons.py'])
    
    # Copy icons to the right location
    if platform.system() == 'Windows':
        shutil.copy('icons/icon.ico', 'icon.ico')
    else:
        shutil.copy('icons/icon.icns', 'icon.icns')
    
    # Build with PyInstaller
    print("Building application...")
    subprocess.run(['pyinstaller', 'gmail_labeler.spec'])
    
    # Clean up temporary files
    if os.path.exists('icon.ico'):
        os.remove('icon.ico')
    if os.path.exists('icon.icns'):
        os.remove('icon.icns')
    
    print("\nBuild completed!")
    if platform.system() == 'Windows':
        print("Windows executable created in: dist/Gmail Labeler.exe")
    else:
        print("macOS app created in: dist/Gmail Labeler.app")
        print("You can create a DMG using: create-dmg dist/Gmail\\ Labeler.app")

if __name__ == '__main__':
    build() 