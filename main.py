#!/usr/bin/env python3

import logging
import os
import re
import shutil
import subprocess

import piexif
from halo import Halo
from PIL import Image

import argparse
from dataclasses import dataclass

# Parse format: YYYYMMDD
REGEX_FILENAME_DATE = r'(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})'
REGEX_EXIF_DATE = r'((\d{4}):(\d{2}):(\d{2}))'
REGEX_EXIF_TIME = r'((\d{2}):(\d{2}):(\d{2}))'
FILES_EXT = ['jpeg', 'jpg', 'mp4']
VIDEO_EXT = ['mp4']
IMAGE_EXT = ['jpeg', 'jpg']

logger = logging.getLogger(__name__)


@dataclass
class File:
    filename: str = ''
    file_path: str = ''
    new_file_path: str = ''
    extension: str = ''
    parsed_date: str = ''
    exif_bytes: bytes = b''
    relative_dir: str = ''  # Subdirectory path relative to input_path

    def __repr__(self):
        return f'Filename: {self.filename}'


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=f'Parse and modify Whatsapp images and videos exif attributes. '
                    f'Allowed extensions are: {",".join(FILES_EXT)}')
    parser.add_argument('--input_path', help='Whatsapp Images and videos path to scan', required=True)
    parser.add_argument('--output_path', help='New Whatsapp Images and videos path to scan', required=True)
    parser.add_argument('--recursive', action='store_true', help='Run recursively in the provided folder')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files in the output path')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose debug logging')
    args = parser.parse_args()

    # Configure logging based on verbose flag
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

    return args


def get_files_from_path(path, recursive=False, output_path=''):
    files = []
    path = os.path.abspath(path)
    
    if recursive:
        file_paths = [(os.path.join(root, file), root) for root, _, files_in_dir in os.walk(path) for file in files_in_dir]
    else:
        file_paths = [(os.path.join(path, file), path) for file in os.listdir(path) if os.path.isfile(os.path.join(path, file))]
    
    for file_path, root_dir in file_paths:
        filename = os.path.basename(file_path)
        extension = os.path.splitext(filename)[1][1:].lower()
        if extension in FILES_EXT:
            # Calculate relative directory from input path
            relative_dir = os.path.relpath(root_dir, path)
            if relative_dir == '.':
                relative_dir = ''
            
            new_file_path = os.path.join(output_path, relative_dir, filename) if output_path else ''
            files.append(File(
                filename=filename,
                file_path=str(file_path),
                new_file_path=new_file_path,
                extension=extension,
                parsed_date='',
                exif_bytes=b'',
                relative_dir=relative_dir
            ))
    
    return files


def export_exif_data(file: File):
    with open(file.file_path, 'rb') as f:
        im = Image.open(f)
        exif_data = im.info.get("exif")
        data = None

        if exif_data:
            data = piexif.load(exif_data).get('Exif')

    return data


def check_exif(file: File):
    """
    Check if a file has EXIF date data (DateTimeOriginal or DateTimeDigitized).
    :param file: File object with file_path.
    :return: True if file has EXIF date data, False otherwise.
    """
    data = export_exif_data(file)

    if data:
        # EXIF date format is "YYYY:MM:DD HH:MM:SS"
        exif_date_pattern = r'\d{4}:\d{2}:\d{2} \d{2}:\d{2}:\d{2}'
        for tag_id, value in data.items():
            if isinstance(value, bytes):
                try:
                    decoded_value = value.decode('utf-8')
                    if re.search(exif_date_pattern, decoded_value):
                        logger.debug(f'Found EXIF date: {decoded_value}')
                        return True
                except UnicodeDecodeError:
                    continue
    return False


def parse_filename_to_date(file):
    """ Parse and return date and time from the filename. """
    date_match = re.search(REGEX_FILENAME_DATE, file.filename)
    time_match = re.search(r'at (\d{2})\.(\d{2})\.(\d{2})', file.filename)
    
    if date_match:
        date_dict = date_match.groupdict()
        date_str = f"{date_dict['year']}:{date_dict['month']}:{date_dict['day']}"
        
        if time_match:
            hour, minute, second = time_match.groups()
            time_str = f"{hour}:{minute}:{second}"
        else:
            time_str = "00:00:00"
        
        file.parsed_date = f"{date_str} {time_str}"
        logger.debug(f'Parsed date: {file.parsed_date}')
    
    return file

def new_image_exif_data(file):
    exif_dict = {'Exif': {}}
    date_time = file.parsed_date
    exif_dict['Exif'] = {
        piexif.ExifIFD.DateTimeOriginal: date_time.encode('utf-8'),
        piexif.ExifIFD.DateTimeDigitized: date_time.encode('utf-8')
    }
    logger.debug(f'EXIF data created: {exif_dict}')
    exif_bytes = piexif.dump(exif_dict)
    file.exif_bytes = exif_bytes
    return file, exif_bytes


def check_exiftool():
    """Check if exiftool is available on the system."""
    return shutil.which('exiftool') is not None


def save_video_exif_data(file, output_path, overwrite):
    """Save EXIF data to video files using exiftool."""
    target_dir = os.path.join(output_path, file.relative_dir) if file.relative_dir else output_path
    os.makedirs(target_dir, exist_ok=True)
    new_file_path = os.path.join(target_dir, file.filename)
    
    if os.path.exists(new_file_path):
        if not overwrite:
            logger.debug(f"Skipping '{file.filename}' - already exists")
            return None
        os.remove(new_file_path)
    
    # Copy file to output location first
    shutil.copy2(file.file_path, new_file_path)
    
    # Use exiftool to set the date metadata
    cmd = [
        'exiftool',
        '-overwrite_original',
        f'-CreateDate={file.parsed_date}',
        f'-ModifyDate={file.parsed_date}',
        f'-MediaCreateDate={file.parsed_date}',
        f'-MediaModifyDate={file.parsed_date}',
        new_file_path
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        file.new_file_path = new_file_path
        logger.debug(f"Video saved: {file.new_file_path}")
        return file
    except subprocess.CalledProcessError as e:
        logger.error(f"exiftool failed: {e.stderr}")
        os.remove(new_file_path)
        return None


def save_exif_data(file, img, output_path, overwrite):
    target_dir = os.path.join(output_path, file.relative_dir) if file.relative_dir else output_path
    os.makedirs(target_dir, exist_ok=True)
    new_file_path = os.path.join(target_dir, file.filename)
    
    if os.path.exists(new_file_path):
        if not overwrite:
            logger.debug(f"Skipping '{file.filename}' - already exists")
            img.close()
            return None
        os.remove(new_file_path)
    
    img.save(new_file_path, exif=file.exif_bytes)
    img.close()
    
    file.new_file_path = new_file_path
    logger.debug(f"Image saved: {file.new_file_path}")
    
    # Verify using the new file path
    saved_file = File(
        filename=file.filename,
        file_path=new_file_path,
        new_file_path=new_file_path,
        extension=file.extension
    )
    if not check_exif(saved_file):
        logger.warning(f"Warning: EXIF verification failed for '{new_file_path}'")

    return file

def main():
    args = parse_arguments()
    spinner = Halo(text='Retrieving list of media files...\n', spinner='dots')
    spinner.start()
    files_list = get_files_from_path(path=args.input_path, recursive=args.recursive)

    for file in files_list:
        if isinstance(file, str):
            file = File(filename=os.path.basename(file), file_path=file)
        
        spinner.text = f'Processing: {file.filename}'
        
        try:
            process_file(file, args, spinner)
        except Exception as e:
            spinner.info(f"An error occurred: {str(e)}")
    
    spinner.succeed("Run complete.")


def process_file(file, args, spinner):
    is_video = file.extension in VIDEO_EXT
    
    # For images, check existing EXIF; for videos, skip this check (exiftool handles it)
    if not is_video and check_exif(file=file):
        spinner.info(f"Skipping file: '{file.filename}' - already has EXIF date")
        return

    file = parse_filename_to_date(file=file)
    if not file.parsed_date:
        spinner.warn(f"Skipping file: '{file.filename}' - no date found in filename")
        return

    if is_video:
        if not check_exiftool():
            spinner.fail(f"Skipping video '{file.filename}' - exiftool not installed")
            return
        result = save_video_exif_data(
            file=file,
            output_path=args.output_path,
            overwrite=args.overwrite
        )
    else:
        im = Image.open(file.file_path)
        file, exif = new_image_exif_data(file=file)
        result = save_exif_data(
            file=file,
            img=im,
            output_path=args.output_path,
            overwrite=args.overwrite
        )
    
    if result:
        spinner.succeed(f"{file.filename} → {file.parsed_date}")


if __name__ == '__main__':
    main()
