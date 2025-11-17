"""
Main asset generation pipeline orchestrator.
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from tqdm import tqdm

from .config import Config
from .recipe import Recipe
from .mesh_generator import MeshGenerator, create_blender_script
from .texture_generator import TextureGenerator
from .lod_generator import LODGenerator, create_lod_blender_script
from .unity_packager import UnityPackager


class AssetPipeline:
    """
    Main orchestrator for the asset generation pipeline.

    Coordinates mesh generation, texture creation, LOD generation,
    and final packaging into Unity-compatible formats.
    """

    def __init__(self, config: Config):
        self.config = config
        self.logger = self._setup_logging()

        # Initialize generators
        self.mesh_generator = MeshGenerator(config)
        self.texture_generator = TextureGenerator(config)
        self.lod_generator = LODGenerator(config)
        self.packager = UnityPackager(config)

        # Ensure directories exist
        config.ensure_directories()

        # Create Blender scripts
        self._setup_blender_scripts()

    def _setup_logging(self) -> logging.Logger:
        """Configure logging for the pipeline."""
        logger = logging.getLogger("AssetPipeline")
        logger.setLevel(getattr(logging, self.config.log_level))

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler if configured
        if self.config.log_file:
            file_handler = logging.FileHandler(self.config.log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def _setup_blender_scripts(self) -> None:
        """Create necessary Blender Python scripts."""
        scripts_dir = self.config.blender_scripts_dir
        scripts_dir.mkdir(parents=True, exist_ok=True)

        create_blender_script(scripts_dir)
        create_lod_blender_script(scripts_dir)

        self.logger.info(f"Blender scripts created in {scripts_dir}")

    def generate_asset_pack(
        self,
        recipe: Recipe,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Generate a complete asset pack from a recipe.

        Args:
            recipe: Recipe defining the asset pack parameters
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with generation results and statistics
        """
        start_time = time.time()

        self.logger.info(f"Starting asset pack generation: {recipe.name}")
        self.logger.info(f"Target count: {recipe.asset_count} assets")

        # Create output directory for this pack
        pack_output_dir = self.config.output_dir / recipe.name.replace(" ", "_")
        pack_output_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        meshes_dir = pack_output_dir / "meshes"
        textures_dir = pack_output_dir / "textures"
        lods_dir = pack_output_dir / "lods"
        package_dir = pack_output_dir / "package"

        for d in [meshes_dir, textures_dir, lods_dir, package_dir]:
            d.mkdir(exist_ok=True)

        # Save recipe for reference
        recipe.save_yaml(str(pack_output_dir / "recipe.yaml"))

        # Generate assets
        generated_assets = []
        failed_assets = []

        # Use progress bar
        with tqdm(total=recipe.asset_count, desc="Generating assets") as pbar:
            for i in range(recipe.asset_count):
                seed = recipe.variation_seed_start + i if recipe.enable_variations else i

                asset_name = recipe.asset_name_pattern.format(
                    index=i,
                    seed=seed,
                    style=recipe.mesh.style,
                    type=recipe.mesh.base_shape,
                )

                try:
                    asset_result = self._generate_single_asset(
                        recipe, seed, asset_name, meshes_dir, textures_dir, lods_dir
                    )
                    generated_assets.append(asset_result)

                    if progress_callback:
                        progress_callback(i + 1, recipe.asset_count, asset_name)

                except Exception as e:
                    self.logger.error(f"Failed to generate {asset_name}: {e}")
                    failed_assets.append({"name": asset_name, "error": str(e)})

                pbar.update(1)

        # Create Unity package
        self.logger.info("Creating Unity package...")
        package_path = self.packager.create_package(
            generated_assets,
            recipe.name.replace(" ", "_"),
            str(package_dir),
            metadata={
                "name": recipe.name,
                "version": recipe.version,
                "author": recipe.author,
                "description": recipe.description,
                "asset_count": len(generated_assets),
                "tags": recipe.tags,
                "generation_time": time.time() - start_time,
            },
        )

        # Generate asset store description
        description = self.packager.create_asset_store_description(
            recipe.name, len(generated_assets), recipe.tags
        )
        desc_path = pack_output_dir / "ASSET_STORE_DESCRIPTION.md"
        with open(desc_path, "w") as f:
            f.write(description)

        # Calculate statistics
        elapsed_time = time.time() - start_time
        stats = {
            "total_requested": recipe.asset_count,
            "successfully_generated": len(generated_assets),
            "failed": len(failed_assets),
            "elapsed_time_seconds": elapsed_time,
            "average_time_per_asset": elapsed_time / max(len(generated_assets), 1),
            "output_directory": str(pack_output_dir),
            "package_path": package_path,
            "failed_assets": failed_assets,
        }

        # Save statistics
        import json
        stats_path = pack_output_dir / "generation_stats.json"
        with open(stats_path, "w") as f:
            json.dump(stats, f, indent=2)

        self.logger.info(f"Asset pack generation complete!")
        self.logger.info(f"Generated {len(generated_assets)}/{recipe.asset_count} assets")
        self.logger.info(f"Total time: {elapsed_time:.2f} seconds")
        self.logger.info(f"Output: {pack_output_dir}")

        return stats

    def _generate_single_asset(
        self,
        recipe: Recipe,
        seed: int,
        asset_name: str,
        meshes_dir: Path,
        textures_dir: Path,
        lods_dir: Path,
    ) -> Dict[str, Any]:
        """
        Generate a single complete asset with mesh, textures, and LODs.

        Args:
            recipe: Generation recipe
            seed: Random seed for this asset
            asset_name: Name for the asset
            meshes_dir: Directory for mesh files
            textures_dir: Directory for texture files
            lods_dir: Directory for LOD files

        Returns:
            Dictionary with all generated file paths
        """
        self.logger.debug(f"Generating asset: {asset_name} (seed={seed})")

        result = {
            "asset_name": asset_name,
            "seed": seed,
        }

        # Step 1: Generate mesh
        self.logger.debug(f"  Generating mesh...")
        mesh_files = self.mesh_generator.generate_mesh(
            recipe.mesh, seed, str(meshes_dir), asset_name
        )
        result.update(mesh_files)

        # Step 2: Generate textures
        self.logger.debug(f"  Generating textures...")
        texture_files = self.texture_generator.generate_texture_set(
            recipe.texture, seed, str(textures_dir), asset_name
        )
        result["textures"] = texture_files

        # Step 3: Generate LODs
        if self.config.lod.generate_lods and "blend" in mesh_files:
            self.logger.debug(f"  Generating LODs...")
            lod_files = self.lod_generator.generate_lods(
                mesh_files["blend"], str(lods_dir), asset_name
            )
            result["lods"] = lod_files

        # Step 4: Generate thumbnail (if requested)
        if recipe.generate_thumbnails:
            self.logger.debug(f"  Generating thumbnail...")
            thumbnail_path = self._generate_thumbnail(
                result, textures_dir, asset_name, recipe.thumbnail_size
            )
            result["thumbnail"] = thumbnail_path

        return result

    def _generate_thumbnail(
        self,
        asset_data: Dict[str, Any],
        output_dir: Path,
        asset_name: str,
        size: tuple,
    ) -> str:
        """Generate a thumbnail image for the asset."""
        from PIL import Image

        # Use albedo texture as thumbnail base
        if "textures" in asset_data and "albedo" in asset_data["textures"]:
            albedo_path = asset_data["textures"]["albedo"]
            if os.path.exists(albedo_path):
                img = Image.open(albedo_path)
                img.thumbnail(size)

                thumbnail_path = str(output_dir / f"{asset_name}_thumbnail.png")
                img.save(thumbnail_path)
                return thumbnail_path

        return ""

    def generate_batch_parallel(
        self,
        recipe: Recipe,
        num_workers: int = None,
    ) -> Dict[str, Any]:
        """
        Generate assets in parallel for better performance.

        Note: This requires Blender to be run multiple times in parallel,
        which may use significant system resources.

        Args:
            recipe: Recipe defining the asset pack
            num_workers: Number of parallel workers (default: config.max_workers)

        Returns:
            Generation statistics
        """
        if num_workers is None:
            num_workers = self.config.max_workers

        self.logger.info(f"Starting parallel generation with {num_workers} workers")

        # Split work into batches
        batch_size = recipe.asset_count // num_workers
        batches = []

        for i in range(num_workers):
            start_idx = i * batch_size
            end_idx = start_idx + batch_size
            if i == num_workers - 1:
                end_idx = recipe.asset_count  # Last worker handles remainder
            batches.append((start_idx, end_idx))

        # Note: Actual parallel implementation would need careful handling
        # of Blender subprocess calls and resource management.
        # For now, we fall back to sequential processing.

        self.logger.warning(
            "Parallel generation not fully implemented yet. "
            "Falling back to sequential processing."
        )
        return self.generate_asset_pack(recipe)

    def validate_recipe(self, recipe: Recipe) -> List[str]:
        """
        Validate a recipe for potential issues.

        Args:
            recipe: Recipe to validate

        Returns:
            List of warning/error messages
        """
        issues = []

        # Check asset count
        if recipe.asset_count < 1:
            issues.append("Asset count must be at least 1")
        if recipe.asset_count > 10000:
            issues.append(
                f"Warning: Generating {recipe.asset_count} assets may take a very long time"
            )

        # Check mesh parameters
        if recipe.mesh.subdivisions > 4:
            issues.append(
                f"Warning: {recipe.mesh.subdivisions} subdivisions will create very dense meshes"
            )

        # Check texture resolution
        if recipe.texture.texture_resolution > 4096:
            issues.append(
                f"Warning: Texture resolution {recipe.texture.texture_resolution} is very high"
            )

        # Check base shape
        valid_shapes = ["cube", "sphere", "cylinder", "cone"]
        if recipe.mesh.base_shape not in valid_shapes:
            issues.append(
                f"Unknown base shape: {recipe.mesh.base_shape}. "
                f"Valid options: {valid_shapes}"
            )

        # Check output directory space (rough estimate)
        estimated_size_mb = (
            recipe.asset_count *
            (10 + recipe.texture.texture_resolution * recipe.texture.texture_resolution * 4 / 1024 / 1024)
        )
        if estimated_size_mb > 10000:
            issues.append(
                f"Warning: Estimated output size is {estimated_size_mb:.0f} MB"
            )

        return issues

    def estimate_generation_time(self, recipe: Recipe) -> float:
        """
        Estimate the time required to generate an asset pack.

        Args:
            recipe: Recipe to estimate

        Returns:
            Estimated time in seconds
        """
        # Rough estimates (in seconds per asset)
        mesh_time = 5.0  # Blender mesh generation
        texture_time = 10.0 if self.config.texture.use_local else 2.0  # AI vs procedural
        lod_time = 3.0 if self.config.lod.generate_lods else 0.0
        packaging_time = 0.5

        time_per_asset = mesh_time + texture_time + lod_time + packaging_time
        total_time = time_per_asset * recipe.asset_count

        return total_time

    def cleanup_temp_files(self) -> None:
        """Clean up temporary files from generation."""
        import shutil

        if self.config.temp_dir.exists():
            shutil.rmtree(self.config.temp_dir)
            self.config.temp_dir.mkdir()
            self.logger.info("Cleaned up temporary files")
