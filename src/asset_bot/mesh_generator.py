"""
Procedural mesh generation using Blender.
"""

import os
import json
import random
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

from .recipe import MeshParameters
from .config import Config


class MeshGenerator:
    """Generates procedural 3D meshes using Blender."""

    def __init__(self, config: Config):
        self.config = config
        self.blender_path = config.blender.executable_path

    def generate_mesh(
        self,
        params: MeshParameters,
        seed: int,
        output_path: str,
        asset_name: str,
    ) -> Dict[str, Any]:
        """
        Generate a single mesh using Blender.

        Args:
            params: Mesh generation parameters
            seed: Random seed for variation
            output_path: Directory to save the mesh
            asset_name: Name for the asset

        Returns:
            Dictionary with paths to generated files
        """
        # Create parameter file for Blender script
        param_data = {
            "seed": seed,
            "asset_name": asset_name,
            "output_path": output_path,
            "base_shape": params.base_shape,
            "size_x": params.size_x,
            "size_y": params.size_y,
            "size_z": params.size_z,
            "subdivisions": params.subdivisions,
            "use_smooth_shading": params.use_smooth_shading,
            "noise_strength": params.noise_strength,
            "noise_scale": params.noise_scale,
            "edge_wear": params.edge_wear,
            "add_details": params.add_details,
            "detail_density": params.detail_density,
            "detail_types": params.detail_types,
            "add_cracks": params.add_cracks,
            "crack_density": params.crack_density,
            "add_dents": params.add_dents,
            "dent_count": params.dent_count,
            "style": params.style,
        }

        # Write parameters to temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(param_data, f)
            param_file = f.name

        try:
            # Get the Blender script path
            script_path = self.config.blender_scripts_dir / "generate_mesh.py"

            # Run Blender in background mode
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
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"Blender failed: {result.stderr}")

            # Parse output to get generated file paths
            output_files = {
                "blend": str(Path(output_path) / f"{asset_name}.blend"),
                "fbx": str(Path(output_path) / f"{asset_name}.fbx"),
                "obj": str(Path(output_path) / f"{asset_name}.obj"),
            }

            return output_files

        finally:
            # Cleanup temp file
            if os.path.exists(param_file):
                os.remove(param_file)

    def generate_batch(
        self,
        params: MeshParameters,
        seed_start: int,
        count: int,
        output_path: str,
        name_pattern: str,
    ) -> list:
        """
        Generate multiple meshes in batch.

        Args:
            params: Mesh generation parameters
            seed_start: Starting seed number
            count: Number of meshes to generate
            output_path: Directory to save meshes
            name_pattern: Pattern for naming assets

        Returns:
            List of dictionaries with generated file paths
        """
        results = []

        for i in range(count):
            seed = seed_start + i
            asset_name = name_pattern.format(
                index=i,
                seed=seed,
                style=params.style,
                type=params.base_shape,
            )

            result = self.generate_mesh(params, seed, output_path, asset_name)
            result["asset_name"] = asset_name
            result["seed"] = seed
            results.append(result)

        return results


def create_blender_script(output_path: Path) -> None:
    """Create the Blender Python script for mesh generation."""

    script_content = '''
"""
Blender script for procedural mesh generation.
Run with: blender --background --python generate_mesh.py -- params.json
"""

import bpy
import bmesh
import json
import sys
import random
import math
from mathutils import Vector, noise


def clear_scene():
    """Clear all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def create_base_shape(shape_type, size):
    """Create the base mesh shape."""
    if shape_type == "cube":
        bpy.ops.mesh.primitive_cube_add(size=1)
    elif shape_type == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, segments=32, ring_count=16)
    elif shape_type == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=1, vertices=32)
    elif shape_type == "cone":
        bpy.ops.mesh.primitive_cone_add(radius1=0.5, depth=1, vertices=32)
    else:
        bpy.ops.mesh.primitive_cube_add(size=1)

    obj = bpy.context.active_object

    # Apply size
    obj.scale = size
    bpy.ops.object.transform_apply(scale=True)

    return obj


def add_subdivisions(obj, levels):
    """Add subdivision surface modifier."""
    if levels > 0:
        mod = obj.modifiers.new(name="Subdivision", type="SUBSURF")
        mod.levels = levels
        mod.render_levels = levels
        bpy.ops.object.modifier_apply(modifier=mod.name)


def apply_noise_deformation(obj, strength, scale, seed):
    """Apply noise-based deformation to mesh."""
    random.seed(seed)

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    for vert in bm.verts:
        # Calculate noise offset
        noise_val = noise.noise(
            Vector((
                vert.co.x * scale + seed,
                vert.co.y * scale + seed,
                vert.co.z * scale + seed
            ))
        )
        # Displace along normal
        vert.co += vert.normal * noise_val * strength

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def add_edge_wear(obj, amount):
    """Add beveled edges for wear effect."""
    if amount > 0:
        mod = obj.modifiers.new(name="Bevel", type="BEVEL")
        mod.width = amount * 0.05
        mod.segments = 2
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(30)
        bpy.ops.object.modifier_apply(modifier=mod.name)


def add_panel_details(obj, density, seed):
    """Add panel-like details to the mesh."""
    random.seed(seed)

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    # Inset random faces
    faces_to_inset = random.sample(
        list(bm.faces),
        int(len(bm.faces) * density * 0.3)
    )

    for face in faces_to_inset:
        if face.is_valid and len(face.edges) == 4:
            try:
                result = bmesh.ops.inset_individual(
                    bm,
                    faces=[face],
                    thickness=random.uniform(0.02, 0.05),
                    depth=random.uniform(-0.02, 0.01)
                )
            except Exception:
                pass

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def add_bolt_details(obj, density, seed):
    """Add bolt/rivet details."""
    random.seed(seed + 100)

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    # Select random vertices for bolts
    num_bolts = int(len(bm.verts) * density * 0.1)
    bolt_verts = random.sample(list(bm.verts), min(num_bolts, len(bm.verts)))

    for vert in bolt_verts:
        # Create small extrusion for bolt head
        if vert.is_valid:
            # Create bolt geometry
            bolt_pos = vert.co + vert.normal * 0.01
            # Add sphere for bolt head
            bmesh.ops.create_uvsphere(
                bm,
                u_segments=6,
                v_segments=4,
                radius=0.008,
                calc_uvs=True
            )

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def add_vent_details(obj, density, seed):
    """Add vent/grill details."""
    random.seed(seed + 200)

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    # Create vent lines on some faces
    faces = list(bm.faces)
    num_vents = int(len(faces) * density * 0.1)
    vent_faces = random.sample(faces, min(num_vents, len(faces)))

    for face in vent_faces:
        if face.is_valid and len(face.edges) == 4:
            # Create vent slits
            try:
                bmesh.ops.inset_individual(
                    bm,
                    faces=[face],
                    thickness=0.01,
                    depth=-0.015
                )
            except Exception:
                pass

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def add_cracks(obj, density, seed):
    """Add crack/damage details."""
    random.seed(seed + 300)

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    # Displace random edges to create crack-like features
    edges = list(bm.edges)
    num_cracks = int(len(edges) * density * 0.05)
    crack_edges = random.sample(edges, min(num_cracks, len(edges)))

    for edge in crack_edges:
        if edge.is_valid:
            # Displace edge slightly
            mid = (edge.verts[0].co + edge.verts[1].co) / 2
            direction = Vector((
                random.uniform(-1, 1),
                random.uniform(-1, 1),
                random.uniform(-1, 1)
            )).normalized()
            edge.verts[0].co += direction * 0.005
            edge.verts[1].co -= direction * 0.005

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def add_dents(obj, count_range, seed):
    """Add dent deformations."""
    random.seed(seed + 400)

    num_dents = random.randint(count_range[0], count_range[1])

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    for _ in range(num_dents):
        # Pick random vertex
        if bm.verts:
            vert = random.choice(list(bm.verts))
            # Push inward
            vert.co -= vert.normal * random.uniform(0.01, 0.03)

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def apply_smooth_shading(obj, smooth):
    """Apply smooth or flat shading."""
    if smooth:
        bpy.ops.object.shade_smooth()
    else:
        bpy.ops.object.shade_flat()


def auto_uv_unwrap(obj):
    """Automatically UV unwrap the mesh."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")


def export_mesh(obj, output_path, asset_name):
    """Export mesh to various formats."""
    import os

    # Ensure output directory exists
    os.makedirs(output_path, exist_ok=True)

    # Save .blend file
    blend_path = os.path.join(output_path, f"{asset_name}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    # Export FBX
    fbx_path = os.path.join(output_path, f"{asset_name}.fbx")
    bpy.ops.export_scene.fbx(
        filepath=fbx_path,
        use_selection=True,
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        bake_space_transform=False,
        object_types={"MESH"},
        use_mesh_modifiers=True,
        mesh_smooth_type="FACE",
        use_tspace=True,
    )

    # Export OBJ
    obj_path = os.path.join(output_path, f"{asset_name}.obj")
    bpy.ops.wm.obj_export(
        filepath=obj_path,
        export_selected_objects=True,
        forward_axis="NEGATIVE_Z",
        up_axis="Y",
    )

    print(f"EXPORTED: {blend_path}")
    print(f"EXPORTED: {fbx_path}")
    print(f"EXPORTED: {obj_path}")


def main():
    # Get parameter file from command line
    argv = sys.argv
    argv = argv[argv.index("--") + 1:]
    param_file = argv[0]

    # Load parameters
    with open(param_file, "r") as f:
        params = json.load(f)

    # Set random seed
    seed = params["seed"]
    random.seed(seed)

    # Clear scene
    clear_scene()

    # Determine size with randomization
    size_x = random.uniform(params["size_x"][0], params["size_x"][1])
    size_y = random.uniform(params["size_y"][0], params["size_y"][1])
    size_z = random.uniform(params["size_z"][0], params["size_z"][1])
    size = Vector((size_x, size_y, size_z))

    # Create base shape
    obj = create_base_shape(params["base_shape"], size)
    obj.name = params["asset_name"]

    # Add subdivisions
    add_subdivisions(obj, params["subdivisions"])

    # Apply noise deformation
    if params["noise_strength"] > 0:
        apply_noise_deformation(
            obj,
            params["noise_strength"],
            params["noise_scale"],
            seed
        )

    # Add edge wear
    add_edge_wear(obj, params["edge_wear"])

    # Add details
    if params["add_details"]:
        detail_types = params["detail_types"]
        density = params["detail_density"]

        if "panels" in detail_types:
            add_panel_details(obj, density, seed)
        if "bolts" in detail_types:
            add_bolt_details(obj, density, seed)
        if "vents" in detail_types:
            add_vent_details(obj, density, seed)

    # Add damage
    if params["add_cracks"]:
        add_cracks(obj, params["crack_density"], seed)

    if params["add_dents"]:
        add_dents(obj, params["dent_count"], seed)

    # Apply shading
    apply_smooth_shading(obj, params["use_smooth_shading"])

    # Auto UV unwrap
    auto_uv_unwrap(obj)

    # Select object for export
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Export
    export_mesh(obj, params["output_path"], params["asset_name"])

    print(f"SUCCESS: Generated {params['asset_name']} with seed {seed}")


if __name__ == "__main__":
    main()
'''

    script_path = output_path / "generate_mesh.py"
    with open(script_path, "w") as f:
        f.write(script_content)
