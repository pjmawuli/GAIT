import subprocess
import sys
import time

# --- CONFIGURATION ---
BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"  # Update if needed
BLENDER_SCRIPT = r"d:\Gait Project\Master\workspace\Manual_Automation.py"     # Your automation script
BLEND_FILE = r"d:\Gait Project\Master\workspace\Master.blend"                 # Your .blend file (optional)
CAMERA_BATCHES = [
    (0, 3),   # First batch: cameras 0-3
    (4, 7),   # Second batch: cameras 4-7
    (8, 10),  # Third batch: cameras 8-10
]
# Add more batches as needed

def run_blender_batch(start_idx, end_idx):
    print(f"\n[INFO] Starting Blender batch for cameras {start_idx} to {end_idx}...")
    cmd = [
        BLENDER_EXE,
        "--background",
        BLEND_FILE,
        "--python", BLENDER_SCRIPT,
        "--",
        f"--start_idx={start_idx}",
        f"--end_idx={end_idx}"
    ]
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print(f"[INFO] Batch {start_idx}-{end_idx} completed successfully.")
    else:
        print(f"[ERROR] Batch {start_idx}-{end_idx} failed with code {result.returncode}.")

def main():
    for start_idx, end_idx in CAMERA_BATCHES:
        run_blender_batch(start_idx, end_idx)
        print("[INFO] Waiting 5 seconds before next batch...")
        time.sleep(5)  # Optional: give system a short break

if __name__ == "__main__":
    main()