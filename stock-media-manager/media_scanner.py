import os
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
    from PIL.ExifTags import TAGS

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp", ".heic", ".raw", ".cr2", ".nef", ".arw", ".dng"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg", ".mxf", ".prores"}


def classify_file(file_path):
    """Determine if a file is a photo, video, or other."""
    ext = Path(file_path).suffix.lower()
    if ext in PHOTO_EXTENSIONS:
        return "photo"
    elif ext in VIDEO_EXTENSIONS:
        return "video"
    return None


def extract_image_metadata(file_path):
    """Extract EXIF and file metadata from an image."""
    metadata = {
        "file_name": os.path.basename(file_path),
        "file_path": os.path.abspath(file_path),
        "file_size": os.path.getsize(file_path),
        "file_type": "photo",
        "width": 0,
        "height": 0,
        "date_taken": "",
        "camera_model": "",
    }

    if HAS_PIL:
        try:
            with Image.open(file_path) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height

                exif_data = img.getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        if tag_name == "DateTimeOriginal":
                            metadata["date_taken"] = str(value)
                        elif tag_name == "Model":
                            metadata["camera_model"] = str(value)
        except Exception:
            pass

    return metadata


def extract_video_metadata(file_path):
    """Extract basic metadata from a video file."""
    return {
        "file_name": os.path.basename(file_path),
        "file_path": os.path.abspath(file_path),
        "file_size": os.path.getsize(file_path),
        "file_type": "video",
        "width": 0,
        "height": 0,
        "date_taken": "",
        "camera_model": "",
    }


def scan_directory(directory, recursive=True):
    """Scan a directory for media files and extract metadata."""
    results = []
    directory = os.path.expanduser(directory)

    if not os.path.isdir(directory):
        return results

    if recursive:
        walker = os.walk(directory)
    else:
        walker = [(directory, [], os.listdir(directory))]

    for root, dirs, files in walker:
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for file_name in files:
            if file_name.startswith("."):
                continue

            file_path = os.path.join(root, file_name)
            file_type = classify_file(file_path)

            if file_type == "photo":
                metadata = extract_image_metadata(file_path)
                results.append(metadata)
            elif file_type == "video":
                metadata = extract_video_metadata(file_path)
                results.append(metadata)

    return results


def generate_stock_keywords(file_name, category=""):
    """Generate suggested keywords based on file name and category."""
    # Clean up file name for keyword suggestions
    name = Path(file_name).stem
    # Split on common separators
    words = []
    for sep in ["-", "_", " ", "."]:
        if sep in name:
            words.extend(name.split(sep))
            break
    if not words:
        words = [name]

    # Filter out numbers and very short words
    words = [w.lower().strip() for w in words if len(w) > 2 and not w.isdigit()]

    # Add category-based keywords
    category_keywords = {
        "Landscape": ["landscape", "nature", "scenic", "outdoor", "travel"],
        "Portrait": ["portrait", "person", "people", "face", "model"],
        "Architecture": ["architecture", "building", "structure", "urban", "city"],
        "Food": ["food", "cuisine", "dish", "restaurant", "cooking"],
        "Business": ["business", "office", "corporate", "professional", "work"],
        "Technology": ["technology", "digital", "computer", "tech", "modern"],
        "Lifestyle": ["lifestyle", "living", "home", "casual", "everyday"],
        "Events": ["event", "celebration", "gathering", "ceremony", "party"],
        "Sports": ["sports", "fitness", "athletic", "exercise", "active"],
        "Abstract": ["abstract", "artistic", "creative", "design", "pattern"],
    }

    if category in category_keywords:
        words.extend(category_keywords[category])

    return list(set(words))


def format_file_size(size_bytes):
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
