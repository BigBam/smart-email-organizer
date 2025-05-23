from PIL import Image, ImageDraw
import os

def create_icon(size, output_path):
    # Create a new image with a white background
    img = Image.new('RGB', (size, size), 'white')
    draw = ImageDraw.Draw(img)
    
    # Draw a simple envelope shape
    margin = size // 4
    draw.rectangle(
        [margin, margin, size - margin, size - margin],
        outline='#4285F4',  # Google blue
        width=max(2, size // 32)
    )
    
    # Draw a label
    label_height = size // 6
    draw.rectangle(
        [margin, size - margin - label_height, size - margin, size - margin],
        fill='#EA4335',  # Google red
        outline='#EA4335'
    )
    
    # Save the image
    img.save(output_path)

def main():
    # Create icons directory if it doesn't exist
    if not os.path.exists('icons'):
        os.makedirs('icons')
    
    # Create Windows icon
    create_icon(256, 'icons/icon.ico')
    
    # Create macOS icon
    create_icon(1024, 'icons/icon.icns')

if __name__ == '__main__':
    main() 