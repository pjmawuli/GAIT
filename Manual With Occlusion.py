"""
Blender Automation Script (Manual + Occlusion)
----------------------------------------
Includes Occlusion Handling and manual camera batch rendering.
"""

import bpy
import os
import sys

# --------------------------
# CONFIGURATION
# --------------------------
WORKSPACE_DIR = r"D:\Gait Project\Master\workspace"

SUBJECT_NUM = 2  # change this to test different subjects
SUBJECT_FILE = os.path.join(WORKSPACE_DIR, "subjects", f"subject{SUBJECT_NUM:04d}.mhm")

BVH_FILE = os.path.join(WORKSPACE_DIR, "bvh_pool", "02_01.bvh")  
#  Change this to any test BVH you want

# Camera & Empty Parameters
CAMERA_RADIUS = 10      # Distance from camera array center to cameras
CAMERA_HEIGHT = 1.5      # Camera height (meters)
EMPTY_HEIGHT = 1.0     # Empty height (meters)
CAMERA_COUNT = 11     # Number of cameras
CAMERA_ANGLE_STEP = 18   # Degrees between cameras
SUBJECT_START_OFFSET = -2.0  # Subject starts this far behind the camera array center (meters, along -Y)

# --------------------------
# RENDER CONFIGURATION
# --------------------------
RENDER_OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "renders", f"subject{SUBJECT_NUM:04d}")
RENDER_IMAGE_FORMAT = 'PNG'      # 'PNG', 'JPEG', etc.
RENDER_RESOLUTION_X = 320       # Width in pixels
RENDER_RESOLUTION_Y = 240       # Height in pixels
RENDER_FRAME_START = 2           # Start frame
RENDER_FRAME_END = 75           # End frame
RENDER_BATCH_SIZE = 10  # Reduced from 50 to 10
RENDER_ENGINE = 'BLENDER_WORKBENCH'  # Use 'BLENDER_WORKBENCH' for simpler rendering
RENDER_SAMPLES = 16  # Lower sample count for Eevee

# --------------------------
# UTILITIES
# --------------------------
def clean_scene():
    """Remove everything from the current Blender scene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    print("[INFO] Scene cleaned.")

def import_subject(filepath):
    """Import a MakeHuman .mhm subject via MPFB."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Subject file not found: {filepath}")
    bpy.ops.mpfb.human_from_mhm(filepath=filepath)
    subject = bpy.context.selected_objects[0]
    print(f"[INFO] Imported subject: {subject.name}")
    return subject

def import_and_retarget_bvh(filepath, target):
    """Import BVH and retarget it onto the given MakeHuman armature."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"BVH file not found: {filepath}")

    bpy.context.view_layer.objects.active = target
    target.select_set(True)

    bpy.ops.mcp.load_and_retarget(
        files=[{"name": os.path.basename(filepath)}],
        directory=os.path.dirname(filepath),
        useAutoTarget=True,
        useAutoSource=True,
        useAutoScale=True,
        useAllFrames=True,
        startFrame=1,
        endFrame=250,
        axis_forward='-Z',
        axis_up='Y'
    )

    print(f"[INFO] BVH loaded and retargeted: {filepath}")

def setup_cameras(subject_location=(0, 0, 0)):
    """
    Add cameras in a semicircle at the side of the subject,
    with 0° facing the front (positive Y axis) and 180° facing the back.
    """
    import math

    empty_name = "CameraTarget"
    empty_location = (0, 0, EMPTY_HEIGHT)
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=empty_location)
    target_empty = bpy.context.active_object
    target_empty.name = empty_name

    angles_deg = [i * CAMERA_ANGLE_STEP for i in range(CAMERA_COUNT)]
    for angle in angles_deg:
        angle_rad = math.radians(angle)
        x = -CAMERA_RADIUS * math.sin(angle_rad)
        y = -CAMERA_RADIUS * math.cos(angle_rad)
        z = CAMERA_HEIGHT

        bpy.ops.object.camera_add(location=(x, y, z))
        cam = bpy.context.active_object
        cam.name = f"Camera_{angle:03d}"

        constraint = cam.constraints.new(type='TRACK_TO')
        constraint.target = target_empty
        constraint.track_axis = 'TRACK_NEGATIVE_Z'
        constraint.up_axis = 'UP_Y'

        print(f"[INFO] Added camera at {angle}°: {cam.name} at position ({x:.2f}, {y:.2f}, {z:.2f})")

def import_occlusion_pole(subject_location=(0, 0, 0), offset=(-2.0, 0, 0)):
    """Import pole.fbx as occlusion object and place it beside the subject."""
    pole_path = os.path.join(WORKSPACE_DIR, "occlusions", "pole.fbx")
    if not os.path.exists(pole_path):
        print(f"[WARNING] Occlusion pole not found: {pole_path}")
        return None
    bpy.ops.import_scene.fbx(filepath=pole_path)
    pole_obj = bpy.context.selected_objects[0]
    pole_obj.location = (
        subject_location[0] + offset[0],
        subject_location[1] + offset[1],
        subject_location[2] + offset[2]
    )
    print(f"[INFO] Occlusion pole imported: {pole_obj.name} at {pole_obj.location}")
    return pole_obj

def render_cameras_in_range(start_idx=0, end_idx=3):
    """
    Render cameras in the specified index range [start_idx, end_idx] (inclusive).
    Each camera's frames are saved in its own folder.
    """
    bpy.context.scene.render.image_settings.file_format = RENDER_IMAGE_FORMAT
    bpy.context.scene.render.resolution_x = RENDER_RESOLUTION_X
    bpy.context.scene.render.resolution_y = RENDER_RESOLUTION_Y
    bpy.context.scene.render.engine = RENDER_ENGINE

    if RENDER_ENGINE == 'BLENDER_EEVEE':
        bpy.context.scene.eevee.taa_render_samples = RENDER_SAMPLES
        bpy.context.scene.eevee.use_gtao = False
        bpy.context.scene.eevee.use_bloom = False
        bpy.context.scene.eevee.use_ssr = False

    bpy.context.scene.frame_start = RENDER_FRAME_START
    bpy.context.scene.frame_end = RENDER_FRAME_END

    cameras = [obj for obj in bpy.data.objects if obj.type == 'CAMERA' and obj.name.startswith("Camera_")]
    if not cameras:
        print("[ERROR] No cameras found for rendering.")
        return

    start_idx = max(0, start_idx)
    end_idx = min(len(cameras) - 1, end_idx)

    for idx in range(start_idx, end_idx + 1):
        cam = cameras[idx]
        bpy.context.scene.camera = cam
        cam_output_dir = os.path.join(RENDER_OUTPUT_DIR, cam.name)
        os.makedirs(cam_output_dir, exist_ok=True)
        bpy.context.scene.render.filepath = os.path.join(cam_output_dir, "frame_")

        for batch_start in range(RENDER_FRAME_START, RENDER_FRAME_END + 1, RENDER_BATCH_SIZE):
            batch_end = min(batch_start + RENDER_BATCH_SIZE - 1, RENDER_FRAME_END)
            bpy.context.scene.frame_start = batch_start
            bpy.context.scene.frame_end = batch_end
            print(f"[RENDER] {cam.name}: frames {batch_start}-{batch_end}")
            try:
                bpy.ops.render.render(animation=True, write_still=True)
            except Exception as e:
                print(f"[ERROR] Rendering failed for camera {cam.name}, frames {batch_start}-{batch_end}: {str(e)}")

    print(f"[RENDER] Cameras {start_idx + 1} to {end_idx + 1} rendered.")

def get_camera_range_from_args(default_start=0, default_end=3):
    """
    Parse --start_idx and --end_idx from command-line arguments.
    Returns (start_idx, end_idx) as integers.
    """
    start_idx = default_start
    end_idx = default_end
    for arg in sys.argv:
        if arg.startswith("--start_idx="):
            try:
                start_idx = int(arg.split("=")[1])
            except ValueError:
                pass
        if arg.startswith("--end_idx="):
            try:
                end_idx = int(arg.split("=")[1])
            except ValueError:
                pass
    return start_idx, end_idx

# --------------------------
# MAIN PIPELINE
# --------------------------
def main():
    clean_scene()
    print("[STEP] Importing subject…")
    subject_location = (0, -SUBJECT_START_OFFSET, 0)
    subject = import_subject(SUBJECT_FILE)
    subject.location = subject_location

    print("[STEP] Importing + Retargeting BVH…")
    import_and_retarget_bvh(BVH_FILE, subject)

    print("[STEP] Setting up cameras…")
    setup_cameras(subject_location=subject_location)

    print("[STEP] Importing occlusion pole…")
    import_occlusion_pole(subject_location=subject_location, offset=(-2.0, 0, 0))

    start_idx, end_idx = get_camera_range_from_args()
    print(f"[STEP] Rendering animation from cameras {start_idx} to {end_idx}…")
    render_cameras_in_range(start_idx=start_idx, end_idx=end_idx)

    print(f"[DONE] Subject with animation, occlusion, and cameras in scene: {subject.name}")

if __name__ == "__main__":
    main()