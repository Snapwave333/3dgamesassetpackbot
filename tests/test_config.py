"""
Tests for configuration system.
"""

import pytest
import tempfile
import os
from pathlib import Path
from asset_bot.config import Config, BlenderConfig, TextureConfig, LODConfig


def test_config_default_creation():
    """Test creating default configuration."""
    config = Config()
    assert config.output_dir == Path("./output")
    assert config.batch_size == 10
    assert config.max_workers == 4


def test_blender_config():
    """Test Blender configuration."""
    config = BlenderConfig()
    assert config.executable_path == "blender"
    assert config.use_gpu is True
    assert config.gpu_device == "CUDA"


def test_texture_config():
    """Test texture configuration."""
    config = TextureConfig()
    assert config.resolution == 1024
    assert config.guidance_scale == 7.5
    assert config.seamless is True


def test_lod_config():
    """Test LOD configuration."""
    config = LODConfig()
    assert config.generate_lods is True
    assert len(config.lod_levels) == 4
    assert config.lod_levels[0] == 1.0


def test_config_save_load_yaml():
    """Test saving and loading config to/from YAML."""
    config = Config()
    config.batch_size = 20
    config.blender.use_gpu = False
    config.texture.resolution = 2048

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        temp_path = f.name

    try:
        config.save_yaml(temp_path)
        loaded = Config.from_yaml(temp_path)

        assert loaded.batch_size == 20
        assert loaded.blender.use_gpu is False
        assert loaded.texture.resolution == 2048
    finally:
        os.unlink(temp_path)


def test_config_to_dict():
    """Test converting config to dictionary."""
    config = Config()
    config.log_level = "DEBUG"

    data = config.to_dict()

    assert data["log_level"] == "DEBUG"
    assert "blender" in data
    assert "texture" in data
    assert "lod" in data
    assert "packaging" in data


def test_config_ensure_directories():
    """Test directory creation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = Config()
        config.output_dir = Path(temp_dir) / "output"
        config.recipes_dir = Path(temp_dir) / "recipes"
        config.temp_dir = Path(temp_dir) / "temp"
        config.blender_scripts_dir = Path(temp_dir) / "scripts"

        config.ensure_directories()

        assert config.output_dir.exists()
        assert config.recipes_dir.exists()
        assert config.temp_dir.exists()
        assert config.blender_scripts_dir.exists()
