from flask import Flask, request, jsonify, send_file
import subprocess
import os
import shutil

app = Flask(__name__)

# Folder where processed files are stored
PHOTOS_DIR = os.path.expanduser("~/Pictures")  # Adjust for Mac/Linux

@app.route('/update_metadata', methods=['POST'])
def update_metadata():
    time_date = request.form.get('time_date')
    file = request.files.get('file')

    if not time_date or not file:
        return jsonify({"error": "Missing parameters"}), 400

    # Save file temporarily
    file_path = os.path.join("./", file.filename)
    file.save(file_path)

    # Run ExifTool command
    command = f'"C:\\ExifTool\\exiftool.exe" -AllDates="{time_date}" -overwrite_original "{file_path}"'

    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)

        # Move file to final storage
        new_path = os.path.join(PHOTOS_DIR, file.filename)
        shutil.move(file_path, new_path)

        return jsonify({
            "success": True,
            "message": f"File {file.filename} saved with new date {time_date}",
            "filename": file.filename,
            "date": time_date,
            "status": "Metadata updated",
            "download_url": f"http://192.168.68.117:5000/download/{file.filename}"
        })

    except subprocess.CalledProcessError as e:
        return jsonify({"error": "ExifTool failed", "details": e.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "ExifTool timed out"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

# Serve files for Shortcuts to download
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(PHOTOS_DIR, filename)
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
