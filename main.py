from flask import Flask, request, jsonify, send_file
import subprocess
import os
import psutil
import csv
import base64
from datetime import datetime

# Import the mega upload function from the modules folder.
from modules.megaUpload import upload_uncompressed_file

app = Flask(__name__)

# Directories for temporary storage
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
SSD_DIR = os.path.join(BASE_DIR, "Videos")  # Example folder on SSD
RAM_DISK_DIR = "R:/temp"  # Adjust for your RAM disk path
LOG_CSV = os.path.join(BASE_DIR, "file_log.csv")

def get_temp_directory(total_size):
    avail_ram = psutil.virtual_memory().available
    if total_size < 0.5 * avail_ram:
        if not os.path.exists(RAM_DISK_DIR):
            os.makedirs(RAM_DISK_DIR, exist_ok=True)
        return RAM_DISK_DIR
    else:
        os.makedirs(SSD_DIR, exist_ok=True)
        return SSD_DIR

def extract_thumbnail(video_path, thumbnail_path):
    """
    Uses ffmpeg to extract a thumbnail at 1 second into the video,
    resized to 320x240. The -update 1 flag ensures a single image file is written.
    """
    command = f'ffmpeg -y -i "{video_path}" -ss 00:00:01.000 -vframes 1 -s 320x240 -update 1 "{thumbnail_path}"'
    subprocess.run(command, shell=True, check=True)
    return thumbnail_path

def get_thumbnail_base64(video_path):
    thumbnail_temp = video_path + ".thumb.jpg"
    try:
        extract_thumbnail(video_path, thumbnail_temp)
        with open(thumbnail_temp, "rb") as f:
            thumb_bytes = f.read()
        base64_thumb = base64.b64encode(thumb_bytes).decode('utf-8')
    except Exception as e:
        base64_thumb = ""
    finally:
        if os.path.exists(thumbnail_temp):
            os.remove(thumbnail_temp)
    return base64_thumb

def log_file_data(filename, uncompressed_size, compressed_size, video_path):
    saved_bytes = uncompressed_size - compressed_size
    saved_percent = (saved_bytes / uncompressed_size * 100) if uncompressed_size else 0
    thumbnail_base64 = get_thumbnail_base64(video_path)
    log_exists = os.path.exists(LOG_CSV)
    
    with open(LOG_CSV, "a", newline="") as csvfile:
        fieldnames = ["timestamp", "filename", "uncompressed_size", "compressed_size", "saved_bytes", "saved_percent", "thumbnail_base64"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not log_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().isoformat(),
            "filename": filename,
            "uncompressed_size": uncompressed_size,
            "compressed_size": compressed_size,
            "saved_bytes": saved_bytes,
            "saved_percent": f"{saved_percent:.2f}",
            "thumbnail_base64": thumbnail_base64
        })

@app.route('/update_metadata', methods=['POST'])
def update_metadata():
    uncompressed_file = request.files.get('uncompressed')
    compressed_file = request.files.get('compressed')
    upload_to_mega_str = request.form.get('uploadToMega', 'false').lower()
    upload_to_mega = upload_to_mega_str in ['true', '1', 'yes']
    
    if not uncompressed_file or not compressed_file:
        return jsonify({"error": "Missing files"}), 400

    # Get file sizes (in bytes)
    uncompressed_file.seek(0, os.SEEK_END)
    uncompressed_size = uncompressed_file.tell()
    uncompressed_file.seek(0)
    
    compressed_file.seek(0, os.SEEK_END)
    compressed_size = compressed_file.tell()
    compressed_file.seek(0)
    
    total_size = uncompressed_size + compressed_size
    temp_dir = get_temp_directory(total_size)
    
    # Create temporary file paths in the chosen directory.
    uncompressed_path = os.path.join(temp_dir, "uncompressed_" + uncompressed_file.filename)
    compressed_path = os.path.join(temp_dir, compressed_file.filename)
    
    # Save both files.
    uncompressed_file.save(uncompressed_path)
    compressed_file.save(compressed_path)
    
    # Extract metadata from uncompressed file.
    metadata_command = f'"C:\\ExifTool\\exiftool.exe" -json "{uncompressed_path}"'
    try:
        result = subprocess.run(metadata_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        metadata = result.stdout  # For debugging if needed
        
        # Apply extracted metadata to compressed file.
        apply_command = f'"C:\\ExifTool\\exiftool.exe" -TagsFromFile "{uncompressed_path}" -All:All -overwrite_original "{compressed_path}"'
        subprocess.run(apply_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        
        # Log file data.
        log_file_data(compressed_file.filename, uncompressed_size, os.path.getsize(compressed_path), compressed_path)
        
        # Prepare Mega upload status.
        mega_status = None
        if upload_to_mega:
            # Attempt to upload the uncompressed file.
            mega_status = upload_uncompressed_file(uncompressed_path)
        
        # Delete the uncompressed file after processing (whether uploaded or not).
        os.remove(uncompressed_path)
        
        # Build the response.
        response_data = {
            "success": True,
            "message": "Metadata transferred successfully",
            "compressed_file": compressed_file.filename,
            "mega_upload_status": mega_status,  # This will be None if not requested.
            "download_url": f"http://192.168.68.117:5000/download/{compressed_file.filename}"
        }
        
        return jsonify(response_data)
        
    except subprocess.CalledProcessError as e:
        return jsonify({"error": "ExifTool failed", "details": e.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "ExifTool timed out"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

# Route to serve the compressed file.
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_file(os.path.join(get_temp_directory(0), filename), as_attachment=True, download_name=filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
