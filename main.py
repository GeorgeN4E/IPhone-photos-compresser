from flask import Flask, request, jsonify, send_file
import subprocess
import os
import psutil

app = Flask(__name__)

# Define your SSD folder (fallback) and the mounted RAM disk folder (via lmdisk)
SSD_DIR = os.path.expanduser("~/Videos")
RAM_DISK_DIR = "R:/temp"  # Change this to the drive/path where lmdisk is mounted

def get_temp_directory(total_size):
    avail_ram = psutil.virtual_memory().available
    # Use the RAM disk if total size is less than 50% of available RAM; adjust this threshold as needed.
    if total_size < 0.5 * avail_ram:
        if not os.path.exists(RAM_DISK_DIR):
            os.makedirs(RAM_DISK_DIR, exist_ok=True)
        return RAM_DISK_DIR
    else:
        os.makedirs(SSD_DIR, exist_ok=True)
        return SSD_DIR

@app.route('/update_metadata', methods=['POST'])
def update_metadata():
    uncompressed_file = request.files.get('uncompressed')
    compressed_file = request.files.get('compressed')

    if not uncompressed_file or not compressed_file:
        return jsonify({"error": "Missing files"}), 400

    # Determine file sizes without consuming the streams
    uncompressed_file.seek(0, os.SEEK_END)
    uncompressed_size = uncompressed_file.tell()
    uncompressed_file.seek(0)
    
    compressed_file.seek(0, os.SEEK_END)
    compressed_size = compressed_file.tell()
    compressed_file.seek(0)
    
    total_size = uncompressed_size + compressed_size
    temp_dir = get_temp_directory(total_size)
    
    # Set file paths in the chosen temporary directory
    uncompressed_path = os.path.join(temp_dir, "uncompressed_" + uncompressed_file.filename)
    compressed_path = os.path.join(temp_dir, compressed_file.filename)
    
    # Save both files to the temporary directory (RAM disk if conditions met, otherwise SSD)
    uncompressed_file.save(uncompressed_path)
    compressed_file.save(compressed_path)
    
    # Extract metadata from the uncompressed video
    metadata_command = f'"C:\\ExifTool\\exiftool.exe" -json "{uncompressed_path}"'
    try:
        result = subprocess.run(metadata_command, shell=True, check=True, 
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                  text=True, timeout=10)
        metadata = result.stdout  # For debugging, if needed

        # Apply extracted metadata to the compressed video
        apply_command = f'"C:\\ExifTool\\exiftool.exe" -TagsFromFile "{uncompressed_path}" -All:All -overwrite_original "{compressed_path}"'
        subprocess.run(apply_command, shell=True, check=True, 
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                       text=True, timeout=10)
        
        # Optionally, remove the uncompressed file once metadata is transferred
        os.remove(uncompressed_path)
        
        # Send the updated (compressed) file back to the requester
        return send_file(compressed_path, as_attachment=True, download_name=compressed_file.filename)
        
    except subprocess.CalledProcessError as e:
        return jsonify({"error": "ExifTool failed", "details": e.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "ExifTool timed out"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
