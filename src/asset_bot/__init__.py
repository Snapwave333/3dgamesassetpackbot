"""
Asset Pack Bot - Automated 3D Game Asset Pack Generator

This bot generates thousands of unique 3D game assets by:
1. Procedurally generating meshes with randomized parameters
2. Creating AI-generated textures using Stable Diffusion
3. Auto UV unwrapping and material application
4. Generating LODs for performance optimization
5. Packaging into Unity-compatible .unitypackage files
"""

__version__ = "1.0.0"
__author__ = "Asset Pack Bot"

from .config import Config
from .recipe import Recipe
from .pipeline import AssetPipeline

__all__ = ["Config", "Recipe", "AssetPipeline", "__version__"]
