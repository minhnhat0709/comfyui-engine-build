import os
import json
from datetime import datetime
import threading

import httpx
from tqdm import tqdm


metadata_lock = threading.Lock()

def download_file_with_storage_management(url, file_name, storage_folder, max_memory_capacity):
    # Create a directory if it doesn't exist
    # if not os.path.exists(storage_folder):
    #     os.makedirs(storage_folder)
    
    # Define the paths for the JSON metadata file and the downloaded file
    print("Started")
    json_file_path = os.path.join(storage_folder, "metadata.json")
    file_path = os.path.join(storage_folder, file_name)
    
    # Load existing metadata or create an empty dictionary if it doesn't exist
    metadata = {}
    if os.path.exists(json_file_path):
        with open(json_file_path, 'r') as json_file:
            metadata = json.load(json_file)
    
    # Check if the URL already exists in the metadata
    if url in metadata:
        # Update the last usage datetime
        metadata[url]["last_usage"] = datetime.now().isoformat()
    else:
        # Download the file
        with metadata_lock:
          if check_file_exists(file_path) == False:
            with httpx.stream("GET", url, follow_redirects=True) as stream:
              total = int(stream.headers["Content-Length"])
              with open(file_path, "wb") as f, tqdm(
                  total=total, unit_scale=True, unit_divisor=1024, unit="B"
              ) as progress:
                  num_bytes_downloaded = stream.num_bytes_downloaded
                  for data in stream.iter_bytes():
                      f.write(data)
                      progress.update(
                          stream.num_bytes_downloaded - num_bytes_downloaded
                      )
                      num_bytes_downloaded = stream.num_bytes_downloaded
                
            # Add the URL to the metadata
            metadata[url] = {
                "file_path": file_path,
                "last_usage": datetime.now().isoformat()
            }
                
                # Check and manage memory capacity
          while calculate_folder_size(storage_folder) > max_memory_capacity:
              # Find the file with the oldest last usage and delete it
              oldest_url = min(metadata, key=lambda x: metadata[x]["last_usage"])
              oldest_file_path = metadata[oldest_url]["file_path"]

              print(f"oldest_file_path {oldest_file_path}")
              del metadata[oldest_url]
              try:
                os.remove(oldest_file_path)
              except:
                pass
    
    # Save the updated metadata
    with open(json_file_path, 'w') as json_file:
        json.dump(metadata, json_file, indent=4)

def check_file_exists(file_path):
    return os.path.exists(file_path)

def calculate_folder_size(folder):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            total_size += os.path.getsize(file_path)

    print(f"filesize: {total_size}")
    return total_size

# Example usage
url = "https://example.com/sample_file.pdf"
storage_folder = "/root/models/loras"
max_memory_capacity = 1024 * 1024 * 1024 * (float(os.environ.get('MAX_MEMORY_CAPACITY') or 30)) # 10 GB
# max_memory_capacity = 1024 * 1024 * 500  # 100 MB

# download_file_with_storage_management(url, storage_folder, max_memory_capacity)

def load_loras(loras):
  for lora in loras:
      print(f"lora: {lora}")
      if lora.get('download_url', None) != None:
        download_file_with_storage_management(lora["download_url"], lora["name"], storage_folder, max_memory_capacity)