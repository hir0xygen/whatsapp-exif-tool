# WhatsApp EXIF Tool

[![Forked from](https://img.shields.io/badge/forked%20from-icecore2%2Fwhatsapp--media--date--to--exif-blue)](https://github.com/icecore2/whatsapp-media-date-to-exif)

Extract dates from WhatsApp media filenames and write them as EXIF metadata for proper date sorting in photo apps.

## Features
- Parses date from WhatsApp filenames (e.g., `IMG-20231225-WA0001.jpg`)
- Writes `DateTimeOriginal` EXIF data to images (JPEG) and videos (MP4)
- Recursive folder scanning with preserved directory structure
- Verbose mode for debugging

## Installation

### Dependencies
```bash
pip install -r requirements.txt
```

### Video Support (optional)
| OS | Command |
|----|---------|
| Ubuntu/Debian | `sudo apt install libimage-exiftool-perl` |
| macOS | `brew install exiftool` |
| Windows | Download from [exiftool.org](https://exiftool.org/) |

## Usage

```bash
python main.py --input_path <INPUT> --output_path <OUTPUT> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--input_path` | Source folder with WhatsApp media (required) |
| `--output_path` | Destination folder for processed files (required) |
| `--recursive` | Scan subfolders, preserving structure |
| `--overwrite` | Overwrite existing files in output |
| `--verbose, -v` | Enable debug logging |

### Examples

**Basic:**
```bash
python main.py --input_path ~/WhatsApp/Media --output_path ~/Photos/WhatsApp
```

**Recursive with overwrite:**
```bash
python main.py --input_path ~/WhatsApp --output_path ~/Photos --recursive --overwrite
```

**Debug mode:**
```bash
python main.py --input_path ./images --output_path ./out --verbose
```

## Supported Formats
- Images: `.jpg`, `.jpeg`
- Videos: `.mp4` (requires exiftool)

## License
[MIT](LICENSE)

---
*Forked from [icecore2/whatsapp-media-date-to-exif](https://github.com/icecore2/whatsapp-media-date-to-exif)*
