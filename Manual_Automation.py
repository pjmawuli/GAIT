"""
Blender Automation Script (Import + Retarget)
----------------------------------------
Loads ONE MakeHuman subject (.mhm) using MPFB.
Loads ONE BVH file and retargets it onto the subject using MakeWalk MCP.
No cameras, no rendering.
Just import + console confirmation.
"""

import bpy
import os

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
RENDER_ENGINE = 'BLENDER_EEVEE'  # Use 'BLENDER_WORKBENCH' for simpler rendering
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

    # Ensure target armature is active
    bpy.context.view_layer.objects.active = target
    target.select_set(True)

    # Run MakeWalk’s retarget operator
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
    Add cameras in a semicircle around the camera array center at specified height.
    Each camera points to the subject's origin (empty).
    """
    import math

    # Create an empty at the subject's origin for camera tracking
    empty_name = "CameraTarget"
    empty_location = (0, 0, EMPTY_HEIGHT)
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=empty_location)
    target_empty = bpy.context.active_object
    target_empty.name = empty_name

    angles_deg = [i * CAMERA_ANGLE_STEP for i in range(CAMERA_COUNT)]  # e.g. 0°, 18°, ..., 180°
    for angle in angles_deg:
        angle_rad = math.radians(angle + 90)  # Offset by +90° so 0° is in front (positive Y axis)
        x = 0 + CAMERA_RADIUS * math.cos(angle_rad)  # Cameras centered at (0, 0)
        y = 0 + CAMERA_RADIUS * math.sin(angle_rad)
        z = CAMERA_HEIGHT

        bpy.ops.object.camera_add(location=(x, y, z))
        cam = bpy.context.active_object
        cam.name = f"Camera_{angle:03d}"

        # Add Track To constraint
        constraint = cam.constraints.new(type='TRACK_TO')
        constraint.target = target_empty
        constraint.track_axis = 'TRACK_NEGATIVE_Z'
        constraint.up_axis = 'UP_Y'

        print(f"[INFO] Added camera at {angle}°: {cam.name}")

def render_all_cameras():
    """
    Loop through all cameras and render animation frames for each.
    Each camera's frames are saved in its own folder.
    """
    # Set render settings
    bpy.context.scene.render.image_settings.file_format = RENDER_IMAGE_FORMAT
    bpy.context.scene.render.resolution_x = RENDER_RESOLUTION_X
    bpy.context.scene.render.resolution_y = RENDER_RESOLUTION_Y
    
    # Use simpler render engine
    bpy.context.scene.render.engine = RENDER_ENGINE
    
    # If using Eevee, lower the sample count
    if RENDER_ENGINE == 'BLENDER_EEVEE':
        bpy.context.scene.eevee.taa_render_samples = RENDER_SAMPLES
        # Turn off features that might cause issues
        bpy.context.scene.eevee.use_gtao = False
        bpy.context.scene.eevee.use_bloom = False
        bpy.context.scene.eevee.use_ssr = False
        
    # Set frame range for rendering
    bpy.context.scene.frame_start = RENDER_FRAME_START
    bpy.context.scene.frame_end = RENDER_FRAME_END

    # Find all cameras by name pattern
    cameras = [obj for obj in bpy.data.objects if obj.type == 'CAMERA' and obj.name.startswith("Camera_")]
    if not cameras:
        print("[ERROR] No cameras found for rendering.")
        return

    for cam in cameras:
        # Set active camera
        bpy.context.scene.camera = cam

        # Prepare output directory for this camera
        cam_output_dir = os.path.join(RENDER_OUTPUT_DIR, cam.name)
        os.makedirs(cam_output_dir, exist_ok=True)
        bpy.context.scene.render.filepath = os.path.join(cam_output_dir, "frame_")

        # Render in smaller batches
        for batch_start in range(RENDER_FRAME_START, RENDER_FRAME_END + 1, RENDER_BATCH_SIZE):
            batch_end = min(batch_start + RENDER_BATCH_SIZE - 1, RENDER_FRAME_END)
            bpy.context.scene.frame_start = batch_start
            bpy.context.scene.frame_end = batch_end
            print(f"[RENDER] {cam.name}: frames {batch_start}-{batch_end}")
            
            try:
                bpy.ops.render.render(animation=True, write_still=True)
            except Exception as e:
                print(f"[ERROR] Rendering failed for camera {cam.name}, frames {batch_start}-{batch_end}: {str(e)}")
                # Continue with next batch instead of failing completely

    print("[RENDER] All cameras rendered.")

# --------------------------
# MAIN PIPELINE (DEBUG)
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

    print("[STEP] Rendering animation from all cameras…")
    render_all_cameras()

    print(f"[DONE] Subject with animation and cameras in scene: {subject.name}")

if __name__ == "__main__":
    main()
