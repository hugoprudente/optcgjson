import os
import shutil

def is_image_file(filename):
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'}
    _, ext = os.path.splitext(filename)
    return ext.lower() in image_extensions

def copy_all_images(src_folder, dest_folder):
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    
    for root, _, files in os.walk(src_folder):
        for file in files:
            if is_image_file(file):
                src_file = os.path.join(root, file)
                dest_file = os.path.join(dest_folder, file)
                shutil.copy2(src_file, dest_file)
                print(f'Copied {src_file} to {dest_file}')

source_folder = 'images'  # Replace with your source folder path
destination_folder = 'all'  # Replace with your destination folder path

copy_all_images(source_folder, destination_folder)
