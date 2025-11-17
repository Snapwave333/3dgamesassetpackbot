"""
Global configuration for the Asset Pack Bot.
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class BlenderConfig:
    """Blender-specific configuration."""
    executable_path: str = "blender"
    python_executable: str = ""
    render_samples: int = 128
    use_gpu: bool = True
    gpu_device: str = "CUDA"


@dataclass
class TextureConfig:
    """AI texture generation configuration."""
    model_id: str = "stabilityai/stable-diffusion-2-1"
    use_local: bool = True
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    resolution: int = 1024
    guidance_scale: float = 7.5
    num_inference_steps: int = 50
    negative_prompt: str = "blurry, low quality, distorted, text, watermark"
    seamless: bool = True


@dataclass
class LODConfig:
    """Level of Detail configuration."""
    generate_lods: bool = True
    lod_levels: list = field(default_factory=lambda: [1.0, 0.5, 0.25, 0.1])
    lod_distances: list = field(default_factory=lambda: [0, 10, 20, 50])


@dataclass
class PackagingConfig:
    """Unity package configuration."""
    include_prefabs: bool = True
    include_materials: bool = True
    include_textures: bool = True
    include_meshes: bool = True
    compression: str = "lz4"
    unity_version: str = "2021.3"


@dataclass
class Config:
    """Main configuration class."""

    # Paths
    output_dir: Path = Path("./output")
    recipes_dir: Path = Path("./recipes")
    temp_dir: Path = Path("./temp")
    blender_scripts_dir: Path = Path("./blender_scripts")

    # Sub-configurations
    blender: BlenderConfig = field(default_factory=BlenderConfig)
    texture: TextureConfig = field(default_factory=TextureConfig)
    lod: LODConfig = field(default_factory=LODConfig)
    packaging: PackagingConfig = field(default_factory=PackagingConfig)

    # Generation settings
    batch_size: int = 10
    max_workers: int = 4
    random_seed: Optional[int] = None

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """Load configuration from YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create configuration from dictionary."""
        config = cls()

        # Update paths
        if "output_dir" in data:
            config.output_dir = Path(data["output_dir"])
        if "recipes_dir" in data:
            config.recipes_dir = Path(data["recipes_dir"])
        if "temp_dir" in data:
            config.temp_dir = Path(data["temp_dir"])
        if "blender_scripts_dir" in data:
            config.blender_scripts_dir = Path(data["blender_scripts_dir"])

        # Update blender config
        if "blender" in data:
            for key, value in data["blender"].items():
                if hasattr(config.blender, key):
                    setattr(config.blender, key, value)

        # Update texture config
        if "texture" in data:
            for key, value in data["texture"].items():
                if hasattr(config.texture, key):
                    setattr(config.texture, key, value)

        # Update LOD config
        if "lod" in data:
            for key, value in data["lod"].items():
                if hasattr(config.lod, key):
                    setattr(config.lod, key, value)

        # Update packaging config
        if "packaging" in data:
            for key, value in data["packaging"].items():
                if hasattr(config.packaging, key):
                    setattr(config.packaging, key, value)

        # Update other settings
        for key in ["batch_size", "max_workers", "random_seed", "log_level", "log_file"]:
            if key in data:
                setattr(config, key, data[key])

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "output_dir": str(self.output_dir),
            "recipes_dir": str(self.recipes_dir),
            "temp_dir": str(self.temp_dir),
            "blender_scripts_dir": str(self.blender_scripts_dir),
            "blender": {
                "executable_path": self.blender.executable_path,
                "python_executable": self.blender.python_executable,
                "render_samples": self.blender.render_samples,
                "use_gpu": self.blender.use_gpu,
                "gpu_device": self.blender.gpu_device,
            },
            "texture": {
                "model_id": self.texture.model_id,
                "use_local": self.texture.use_local,
                "api_key": self.texture.api_key,
                "api_url": self.texture.api_url,
                "resolution": self.texture.resolution,
                "guidance_scale": self.texture.guidance_scale,
                "num_inference_steps": self.texture.num_inference_steps,
                "negative_prompt": self.texture.negative_prompt,
                "seamless": self.texture.seamless,
            },
            "lod": {
                "generate_lods": self.lod.generate_lods,
                "lod_levels": self.lod.lod_levels,
                "lod_distances": self.lod.lod_distances,
            },
            "packaging": {
                "include_prefabs": self.packaging.include_prefabs,
                "include_materials": self.packaging.include_materials,
                "include_textures": self.packaging.include_textures,
                "include_meshes": self.packaging.include_meshes,
                "compression": self.packaging.compression,
                "unity_version": self.packaging.unity_version,
            },
            "batch_size": self.batch_size,
            "max_workers": self.max_workers,
            "random_seed": self.random_seed,
            "log_level": self.log_level,
            "log_file": self.log_file,
        }

    def save_yaml(self, path: str) -> None:
        """Save configuration to YAML file."""
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.recipes_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.blender_scripts_dir.mkdir(parents=True, exist_ok=True)
