from flask import Flask, request, jsonify, send_from_directory
import subprocess
import os

app = Flask(__name__)

UPLOAD_DIR = os.path.expanduser("~/Videos")  # Adjust for Mac/Linux
os.makedirs(UPLOAD_DIR, exist_ok=True)  # Ensure upload directory exists

@app.route('/update_metadata', methods=['POST'])
def update_metadata():
    uncompressed_file = request.files.get('uncompressed')
    compressed_file = request.files.get('compressed')

    if not uncompressed_file or not compressed_file:
        return jsonify({"error": "Missing files"}), 400

    # Save both files
    uncompressed_path = os.path.join(UPLOAD_DIR, "uncompressed_" + uncompressed_file.filename)
    compressed_path = os.path.join(UPLOAD_DIR, compressed_file.filename)

    uncompressed_file.save(uncompressed_path)
    compressed_file.save(compressed_path)

    # Extract metadata from uncompressed video
    metadata_command = f'"C:\\ExifTool\\exiftool.exe" -json "{uncompressed_path}"'
    try:
        result = subprocess.run(metadata_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        metadata = result.stdout

        # Apply extracted metadata to compressed video
        apply_command = f'"C:\\ExifTool\\exiftool.exe" -TagsFromFile "{uncompressed_path}" -All:All -overwrite_original "{compressed_path}"'
        subprocess.run(apply_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)

        # Delete uncompressed file after applying metadata
        os.remove(uncompressed_path)

        return jsonify({
            "success": True,
            "message": "Metadata transferred successfully",
            "compressed_file": compressed_file.filename,
            "download_url": f"http://192.168.68.117:5000/download/{compressed_file.filename}"
        })

    except subprocess.CalledProcessError as e:
        return jsonify({"error": "ExifTool failed", "details": e.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "ExifTool timed out"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

# ✅ Route to serve the compressed video for download
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
