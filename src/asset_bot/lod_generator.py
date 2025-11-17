"""
Level of Detail (LOD) generation for meshes.
"""

import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any

from .config import Config


class LODGenerator:
    """Generates LOD variants of meshes using Blender's decimate modifier."""

    def __init__(self, config: Config):
        self.config = config
        self.blender_path = config.blender.executable_path

    def generate_lods(
        self,
        input_blend_path: str,
        output_path: str,
        asset_name: str,
        lod_levels: List[float] = None,
    ) -> Dict[str, List[str]]:
        """
        Generate LOD variants for a mesh.

        Args:
            input_blend_path: Path to the source .blend file
            output_path: Directory to save LOD meshes
            asset_name: Base name for the asset
            lod_levels: List of decimation ratios (e.g., [1.0, 0.5, 0.25, 0.1])

        Returns:
            Dictionary mapping LOD level to exported file paths
        """
        if lod_levels is None:
            lod_levels = self.config.lod.lod_levels

        # Create parameter file
        param_data = {
            "input_blend_path": input_blend_path,
            "output_path": output_path,
            "asset_name": asset_name,
            "lod_levels": lod_levels,
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(param_data, f)
            param_file = f.name

        try:
            # Get the Blender script path
            script_path = self.config.blender_scripts_dir / "generate_lods.py"

            # Run Blender
            cmd = [
                self.blender_path,
                "--background",
                "--python",
                str(script_path),
                "--",
                param_file,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"LOD generation failed: {result.stderr}")

            # Build result dictionary
            lod_files = {}
            for i, level in enumerate(lod_levels):
                lod_name = f"{asset_name}_LOD{i}"
                lod_files[f"LOD{i}"] = {
                    "level": level,
                    "fbx": str(Path(output_path) / f"{lod_name}.fbx"),
                    "obj": str(Path(output_path) / f"{lod_name}.obj"),
                }

            return lod_files

        finally:
            if os.path.exists(param_file):
                os.remove(param_file)


def create_lod_blender_script(output_path: Path) -> None:
    """Create the Blender Python script for LOD generation."""

    script_content = '''
"""
Blender script for LOD generation.
Run with: blender --background --python generate_lods.py -- params.json
"""

import bpy
import json
import sys
import os


def load_blend_file(filepath):
    """Load a .blend file."""
    bpy.ops.wm.open_mainfile(filepath=filepath)


def get_mesh_objects():
    """Get all mesh objects in the scene."""
    return [obj for obj in bpy.data.objects if obj.type == "MESH"]


def create_lod_variant(obj, ratio, lod_index):
    """Create a decimated LOD variant of an object."""
    # Duplicate object
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.duplicate()

    lod_obj = bpy.context.active_object
    lod_obj.name = f"{obj.name}_LOD{lod_index}"

    # Apply decimate modifier if ratio < 1.0
    if ratio < 1.0:
        mod = lod_obj.modifiers.new(name="Decimate", type="DECIMATE")
        mod.ratio = ratio
        mod.use_collapse_triangulate = True

        # Apply the modifier
        bpy.ops.object.modifier_apply(modifier=mod.name)

    return lod_obj


def export_lod(obj, output_path, name):
    """Export a single LOD object."""
    # Deselect all
    bpy.ops.object.select_all(action="DESELECT")

    # Select only this object
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Export FBX
    fbx_path = os.path.join(output_path, f"{name}.fbx")
    bpy.ops.export_scene.fbx(
        filepath=fbx_path,
        use_selection=True,
        global_scale=1.0,
        apply_unit_scale=True,
        object_types={"MESH"},
        use_mesh_modifiers=True,
    )

    # Export OBJ
    obj_path = os.path.join(output_path, f"{name}.obj")
    bpy.ops.wm.obj_export(
        filepath=obj_path,
        export_selected_objects=True,
    )

    print(f"EXPORTED LOD: {fbx_path}")
    print(f"EXPORTED LOD: {obj_path}")


def main():
    # Get parameter file
    argv = sys.argv
    argv = argv[argv.index("--") + 1:]
    param_file = argv[0]

    # Load parameters
    with open(param_file, "r") as f:
        params = json.load(f)

    # Load the source blend file
    load_blend_file(params["input_blend_path"])

    # Get mesh objects
    mesh_objects = get_mesh_objects()

    if not mesh_objects:
        print("ERROR: No mesh objects found in blend file")
        sys.exit(1)

    # Use first mesh object
    source_obj = mesh_objects[0]

    # Ensure output directory exists
    os.makedirs(params["output_path"], exist_ok=True)

    # Generate LOD variants
    for i, ratio in enumerate(params["lod_levels"]):
        lod_obj = create_lod_variant(source_obj, ratio, i)
        lod_name = f"{params['asset_name']}_LOD{i}"
        export_lod(lod_obj, params["output_path"], lod_name)

        # Get vertex count for info
        vertex_count = len(lod_obj.data.vertices)
        print(f"LOD{i}: ratio={ratio}, vertices={vertex_count}")

    print(f"SUCCESS: Generated {len(params['lod_levels'])} LOD levels")


if __name__ == "__main__":
    main()
'''

    script_path = output_path / "generate_lods.py"
    with open(script_path, "w") as f:
        f.write(script_content)
