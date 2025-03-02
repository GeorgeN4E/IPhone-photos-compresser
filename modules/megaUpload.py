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
    about_data = get_mega_about(remote)

    if not about_data:
        return {"success": False, "message": "Failed to get Mega storage info."}
    
    free_space = int(about_data.get("free", 0))  
    if file_size > free_space:
        return {
            "success": False,
            "message": f"Not enough storage on Mega for file '{os.path.basename(file_path)}'. "
                       f"File size: {file_size} bytes, Free space: {free_space} bytes."
        }

    try:
        subprocess.run(
            [r"D:\Apps\rclone-v1.69.1-windows-amd64\rclone.exe", "copy", file_path, remote],
            capture_output=True, text=True, check=True
        )

        # Extract the uploaded file link
        remote_file_path = f"{remote}/{os.path.basename(file_path)}"
        link_result = subprocess.run(
            [r"D:\Apps\rclone-v1.69.1-windows-amd64\rclone.exe", "link", remote_file_path],
            capture_output=True, text=True, check=True
        )
        
        link = link_result.stdout.strip()  # Get the Mega link

        # Extract account name from `remote` (remove trailing `:`)
        mega_account = remote.rstrip(":")

        return {
            "success": True,
            "message": "File uploaded successfully to Mega.",
            "mega_link": link,
            "mega_account": mega_account
        }
    
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"Upload failed: {e.stderr}"}
