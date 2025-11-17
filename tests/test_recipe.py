"""
Tests for recipe system.
"""

import pytest
import tempfile
import os
from asset_bot.recipe import Recipe, MeshParameters, TextureParameters


def test_recipe_default_creation():
    """Test creating a default recipe."""
    recipe = Recipe()
    assert recipe.name == "Unnamed Asset Pack"
    assert recipe.asset_count == 100
    assert recipe.mesh.base_shape == "cube"
    assert recipe.texture.material_type == "metal"


def test_mesh_parameters():
    """Test mesh parameters."""
    params = MeshParameters()
    assert params.base_shape == "cube"
    assert params.subdivisions == 2
    assert params.add_details is True
    assert "panels" in params.detail_types


def test_texture_parameters():
    """Test texture parameters."""
    params = TextureParameters()
    assert params.material_type == "metal"
    assert params.texture_resolution == 1024
    assert params.seamless is True


def test_texture_prompt_building():
    """Test building texture generation prompts."""
    params = TextureParameters()
    params.material_type = "metal"
    params.style_keywords = ["sci-fi", "futuristic"]
    params.color_palette = ["gray", "blue"]
    params.weathering = 0.6
    params.scratch_amount = 0.4

    prompt = params.build_prompt()

    assert "metal" in prompt
    assert "sci-fi" in prompt
    assert "futuristic" in prompt
    assert "gray" in prompt
    assert "blue" in prompt
    assert "weathered" in prompt


def test_recipe_save_load_yaml():
    """Test saving and loading recipe to/from YAML."""
    recipe = Recipe()
    recipe.name = "Test Pack"
    recipe.asset_count = 50
    recipe.mesh.base_shape = "sphere"
    recipe.texture.material_type = "stone"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        temp_path = f.name

    try:
        recipe.save_yaml(temp_path)
        loaded = Recipe.from_yaml(temp_path)

        assert loaded.name == "Test Pack"
        assert loaded.asset_count == 50
        assert loaded.mesh.base_shape == "sphere"
        assert loaded.texture.material_type == "stone"
    finally:
        os.unlink(temp_path)


def test_recipe_to_dict():
    """Test converting recipe to dictionary."""
    recipe = Recipe()
    recipe.name = "Dict Test"
    recipe.tags = ["test", "example"]

    data = recipe.to_dict()

    assert data["name"] == "Dict Test"
    assert data["tags"] == ["test", "example"]
    assert "mesh" in data
    assert "texture" in data


def test_recipe_from_dict():
    """Test creating recipe from dictionary."""
    data = {
        "name": "From Dict",
        "asset_count": 200,
        "mesh": {
            "base_shape": "cylinder",
            "subdivisions": 3,
        },
        "texture": {
            "material_type": "wood",
            "texture_resolution": 2048,
        },
    }

    recipe = Recipe.from_dict(data)

    assert recipe.name == "From Dict"
    assert recipe.asset_count == 200
    assert recipe.mesh.base_shape == "cylinder"
    assert recipe.mesh.subdivisions == 3
    assert recipe.texture.material_type == "wood"
    assert recipe.texture.texture_resolution == 2048
