import subprocess

time_date = "2025-02-28T20:28:29+02:00"
file_path = "img.mov"

command = f'"C:\\ExifTool\\exiftool.exe" -AllDates="{time_date}" -overwrite_original "{file_path}"'

print("Running command:", command)

try:
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
    print("ExifTool Output:\n", result.stdout)
    print("ExifTool Error:\n", result.stderr)
except subprocess.TimeoutExpired:
    print("Error: ExifTool timed out")
except subprocess.CalledProcessError as e:
    print("Error: ExifTool execution failed", e.stderr)
