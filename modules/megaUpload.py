import subprocess
import json
import os

def get_mega_about(remote="mega:"):
    try:
        result = subprocess.run(
            [r"D:\Apps\rclone-v1.69.1-windows-amd64\rclone.exe", "about", remote, "--json"],
            capture_output=True, text=True, check=True
        )
        print("Raw JSON Output:", result.stdout)  # Debugging line
        about_data = json.loads(result.stdout)
        return about_data
    except subprocess.CalledProcessError:
        return None


def upload_uncompressed_file(file_path, remote="Mega-nz_DamosWinlosECU_Backup_2:"):
    if not os.path.exists(file_path):
        return {"success": False, "message": "File does not exist."}
    
    file_size = os.path.getsize(file_path)
    about_data = get_mega_about(remote)  # Now correctly passing `remote`

    if not about_data:
        return {"success": False, "message": "Failed to get Mega storage info."}
    
    # Correcting the key name (lowercase 'free')
    free_space = int(about_data.get("free", 0))  

    print(f"File size: {file_size} bytes")
    print(f"Mega free space: {free_space} bytes")

    if file_size > free_space:
        return {
            "success": False,
            "message": f"Not enough storage on Mega for file '{os.path.basename(file_path)}'. "
                       f"File size: {file_size} bytes, Free space: {free_space} bytes. "
                       "Please upload manually and/or consider a new Mega account."
        }

    try:
        result = subprocess.run(
            [r"D:\Apps\rclone-v1.69.1-windows-amd64\rclone.exe", "copy", file_path, remote],
            capture_output=True, text=True, check=True
        )
        return {"success": True, "message": "File uploaded successfully to Mega."}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"Upload failed: {e.stderr}"}


file_path = r"D:\Sublime Text\Python\IPhone-photos-compresser\file_log.csv"
remote = "IPhoneUncompressedN4E1:"
result = upload_uncompressed_file(file_path, remote)
print(result)
