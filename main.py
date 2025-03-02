from flask import Flask, request
import subprocess

app = Flask(__name__)

@app.route('/update_metadata', methods=['POST'])
def update_metadata():
    # Get form data
    time_date = request.form.get('time_date')
    file = request.files.get('file')

    if not time_date or not file:
        return {"error": "Missing parameters"}, 400

    file_path = f"./{file.filename}"  # Save file temporarily
    file.save(file_path)

    command = f'"C:\\ExifTool\\exiftool.exe" -AllDates="{time_date}" -overwrite_original "{file_path}"'

    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        return {"success": "Metadata updated", "exif_output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"error": "ExifTool failed", "details": e.stderr}, 500
    except subprocess.TimeoutExpired:
        return {"error": "ExifTool timed out"}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
