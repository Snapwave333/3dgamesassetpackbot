"""
Recipe system for defining asset generation parameters.
"""

import yaml
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class MeshParameters:
    """Parameters for procedural mesh generation."""

    # Base shape
    base_shape: str = "cube"  # cube, sphere, cylinder, cone, custom

    # Size parameters (min, max for randomization)
    size_x: Tuple[float, float] = (0.8, 1.2)
    size_y: Tuple[float, float] = (0.8, 1.2)
    size_z: Tuple[float, float] = (0.8, 1.2)

    # Subdivision and detail
    subdivisions: int = 2
    use_smooth_shading: bool = False

    # Deformation parameters
    noise_strength: float = 0.1
    noise_scale: float = 1.0
    edge_wear: float = 0.0  # 0-1, amount of edge beveling/wear

    # Additional features
    add_details: bool = True
    detail_density: float = 0.5
    detail_types: List[str] = field(default_factory=lambda: ["panels", "bolts", "vents"])

    # Damage/variation
    add_cracks: bool = False
    crack_density: float = 0.2
    add_dents: bool = False
    dent_count: Tuple[int, int] = (0, 5)

    # Style modifiers
    style: str = "stylized"  # realistic, stylized, low_poly


@dataclass
class TextureParameters:
    """Parameters for AI texture generation."""

    # Main prompt components
    material_type: str = "metal"  # metal, wood, stone, plastic, etc.
    style_keywords: List[str] = field(default_factory=lambda: ["sci-fi", "futuristic"])
    color_palette: List[str] = field(default_factory=lambda: ["gray", "blue", "orange"])

    # Surface properties
    weathering: float = 0.3  # 0-1, amount of wear/weathering
    dirt_amount: float = 0.2
    scratch_amount: float = 0.3

    # Texture maps to generate
    generate_albedo: bool = True
    generate_normal: bool = True
    generate_roughness: bool = True
    generate_metallic: bool = True
    generate_ao: bool = True
    generate_emission: bool = False

    # Resolution
    texture_resolution: int = 1024

    # Seamless tiling
    seamless: bool = True

    # Custom prompt override
    custom_prompt: Optional[str] = None

    def build_prompt(self) -> str:
        """Build the full prompt for texture generation."""
        if self.custom_prompt:
            return self.custom_prompt

        # Build base prompt
        style_str = " ".join(self.style_keywords)
        color_str = " and ".join(self.color_palette)

        prompt = f"seamless {style_str} {self.material_type} texture, {color_str} colors"

        # Add weathering
        if self.weathering > 0.5:
            prompt += ", heavily weathered and worn"
        elif self.weathering > 0.2:
            prompt += ", slightly weathered"

        # Add dirt
        if self.dirt_amount > 0.5:
            prompt += ", dirty and grimy"
        elif self.dirt_amount > 0.2:
            prompt += ", some dust and dirt"

        # Add scratches
        if self.scratch_amount > 0.5:
            prompt += ", heavily scratched"
        elif self.scratch_amount > 0.2:
            prompt += ", minor scratches"

        # Quality keywords
        prompt += ", high quality, detailed, PBR texture, game asset"

        if self.seamless:
            prompt += ", tileable, seamless pattern"

        return prompt


@dataclass
class Recipe:
    """Complete recipe for generating an asset pack."""

    # Metadata
    name: str = "Unnamed Asset Pack"
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)

    # Generation parameters
    asset_count: int = 100
    asset_name_pattern: str = "{style}_{type}_{index:04d}"

    # Mesh and texture parameters
    mesh: MeshParameters = field(default_factory=MeshParameters)
    texture: TextureParameters = field(default_factory=TextureParameters)

    # Variations
    enable_variations: bool = True
    variation_seed_start: int = 0

    # Output settings
    export_formats: List[str] = field(default_factory=lambda: ["fbx", "obj"])
    generate_thumbnails: bool = True
    thumbnail_size: Tuple[int, int] = (256, 256)

    @classmethod
    def from_yaml(cls, path: str) -> "Recipe":
        """Load recipe from YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Recipe":
        """Create recipe from dictionary."""
        recipe = cls()

        # Update metadata
        for key in ["name", "description", "version", "author", "tags"]:
            if key in data:
                setattr(recipe, key, data[key])

        # Update generation parameters
        for key in ["asset_count", "asset_name_pattern", "enable_variations",
                    "variation_seed_start", "export_formats", "generate_thumbnails"]:
            if key in data:
                setattr(recipe, key, data[key])

        if "thumbnail_size" in data:
            recipe.thumbnail_size = tuple(data["thumbnail_size"])

        # Update mesh parameters
        if "mesh" in data:
            mesh_data = data["mesh"]
            for key, value in mesh_data.items():
                if hasattr(recipe.mesh, key):
                    # Convert lists to tuples for range parameters
                    if key in ["size_x", "size_y", "size_z", "dent_count"] and isinstance(value, list):
                        value = tuple(value)
                    setattr(recipe.mesh, key, value)

        # Update texture parameters
        if "texture" in data:
            tex_data = data["texture"]
            for key, value in tex_data.items():
                if hasattr(recipe.texture, key):
                    setattr(recipe.texture, key, value)

        return recipe

    def to_dict(self) -> Dict[str, Any]:
        """Convert recipe to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "asset_count": self.asset_count,
            "asset_name_pattern": self.asset_name_pattern,
            "enable_variations": self.enable_variations,
            "variation_seed_start": self.variation_seed_start,
            "export_formats": self.export_formats,
            "generate_thumbnails": self.generate_thumbnails,
            "thumbnail_size": list(self.thumbnail_size),
            "mesh": {
                "base_shape": self.mesh.base_shape,
                "size_x": list(self.mesh.size_x),
                "size_y": list(self.mesh.size_y),
                "size_z": list(self.mesh.size_z),
                "subdivisions": self.mesh.subdivisions,
                "use_smooth_shading": self.mesh.use_smooth_shading,
                "noise_strength": self.mesh.noise_strength,
                "noise_scale": self.mesh.noise_scale,
                "edge_wear": self.mesh.edge_wear,
                "add_details": self.mesh.add_details,
                "detail_density": self.mesh.detail_density,
                "detail_types": self.mesh.detail_types,
                "add_cracks": self.mesh.add_cracks,
                "crack_density": self.mesh.crack_density,
                "add_dents": self.mesh.add_dents,
                "dent_count": list(self.mesh.dent_count),
                "style": self.mesh.style,
            },
            "texture": {
                "material_type": self.texture.material_type,
                "style_keywords": self.texture.style_keywords,
                "color_palette": self.texture.color_palette,
                "weathering": self.texture.weathering,
                "dirt_amount": self.texture.dirt_amount,
                "scratch_amount": self.texture.scratch_amount,
                "generate_albedo": self.texture.generate_albedo,
                "generate_normal": self.texture.generate_normal,
                "generate_roughness": self.texture.generate_roughness,
                "generate_metallic": self.texture.generate_metallic,
                "generate_ao": self.texture.generate_ao,
                "generate_emission": self.texture.generate_emission,
                "texture_resolution": self.texture.texture_resolution,
                "seamless": self.texture.seamless,
                "custom_prompt": self.texture.custom_prompt,
            },
        }

    def save_yaml(self, path: str) -> None:
        """Save recipe to YAML file."""
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

    def save_json(self, path: str) -> None:
        """Save recipe to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
