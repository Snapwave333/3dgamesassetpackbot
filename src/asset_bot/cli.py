#!/usr/bin/env python3
"""
Command-line interface for the Asset Pack Bot.
"""

import os
import sys
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from .config import Config
from .recipe import Recipe
from .pipeline import AssetPipeline


console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="Asset Pack Bot")
def main():
    """
    Asset Pack Bot - Automated 3D Game Asset Pack Generator

    Generate thousands of unique 3D game assets with procedural meshes,
    AI-generated textures, automatic LOD generation, and Unity packaging.
    """
    pass


@main.command()
@click.argument("recipe_path", type=click.Path(exists=True))
@click.option(
    "--config", "-c", "config_path",
    type=click.Path(exists=True),
    help="Path to configuration file"
)
@click.option(
    "--output", "-o", "output_dir",
    type=click.Path(),
    help="Output directory (overrides config)"
)
@click.option(
    "--count", "-n",
    type=int,
    help="Override asset count from recipe"
)
@click.option(
    "--parallel", "-p",
    type=int,
    default=1,
    help="Number of parallel workers"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate recipe without generating"
)
def generate(recipe_path, config_path, output_dir, count, parallel, dry_run):
    """
    Generate an asset pack from a recipe file.

    RECIPE_PATH: Path to the YAML recipe file
    """
    console.print(Panel.fit(
        "[bold green]Asset Pack Bot[/bold green]\n"
        "Automated 3D Game Asset Generator",
        border_style="green"
    ))

    # Load configuration
    if config_path:
        config = Config.from_yaml(config_path)
        console.print(f"Loaded config from: {config_path}")
    else:
        config = Config()
        console.print("Using default configuration")

    # Override output directory if specified
    if output_dir:
        config.output_dir = Path(output_dir)

    # Load recipe
    console.print(f"Loading recipe: {recipe_path}")
    recipe = Recipe.from_yaml(recipe_path)

    # Override count if specified
    if count:
        recipe.asset_count = count

    # Show recipe summary
    table = Table(title="Recipe Summary")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Name", recipe.name)
    table.add_row("Asset Count", str(recipe.asset_count))
    table.add_row("Base Shape", recipe.mesh.base_shape)
    table.add_row("Style", recipe.mesh.style)
    table.add_row("Material", recipe.texture.material_type)
    table.add_row("Texture Resolution", f"{recipe.texture.texture_resolution}px")
    table.add_row("Tags", ", ".join(recipe.tags))

    console.print(table)

    # Create pipeline
    pipeline = AssetPipeline(config)

    # Validate recipe
    issues = pipeline.validate_recipe(recipe)
    if issues:
        console.print("\n[yellow]Recipe Validation:[/yellow]")
        for issue in issues:
            if issue.startswith("Warning"):
                console.print(f"  [yellow]⚠ {issue}[/yellow]")
            else:
                console.print(f"  [red]✗ {issue}[/red]")

    # Estimate time
    estimated_time = pipeline.estimate_generation_time(recipe)
    hours = int(estimated_time // 3600)
    minutes = int((estimated_time % 3600) // 60)
    seconds = int(estimated_time % 60)

    console.print(f"\n[blue]Estimated generation time:[/blue] {hours}h {minutes}m {seconds}s")

    if dry_run:
        console.print("\n[yellow]Dry run complete. No assets generated.[/yellow]")
        return

    # Confirm generation
    if not click.confirm("\nProceed with generation?"):
        console.print("Generation cancelled.")
        return

    # Generate assets
    console.print("\n[bold]Starting asset generation...[/bold]\n")

    try:
        if parallel > 1:
            stats = pipeline.generate_batch_parallel(recipe, parallel)
        else:
            stats = pipeline.generate_asset_pack(recipe)

        # Show results
        console.print("\n[bold green]Generation Complete![/bold green]")

        results_table = Table(title="Generation Results")
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Value", style="green")

        results_table.add_row("Assets Generated", str(stats["successfully_generated"]))
        results_table.add_row("Assets Failed", str(stats["failed"]))
        results_table.add_row(
            "Total Time",
            f"{stats['elapsed_time_seconds']:.2f} seconds"
        )
        results_table.add_row(
            "Avg Time/Asset",
            f"{stats['average_time_per_asset']:.2f} seconds"
        )
        results_table.add_row("Output Directory", stats["output_directory"])
        results_table.add_row("Unity Package", stats["package_path"])

        console.print(results_table)

        if stats["failed"]:
            console.print(f"\n[yellow]Failed assets: {len(stats['failed_assets'])}[/yellow]")
            for failed in stats["failed_assets"][:5]:
                console.print(f"  - {failed['name']}: {failed['error']}")

    except Exception as e:
        console.print(f"\n[red]Error during generation: {e}[/red]")
        raise


@main.command()
@click.argument("name")
@click.option(
    "--output", "-o",
    type=click.Path(),
    default=".",
    help="Output directory for recipe file"
)
@click.option(
    "--preset", "-p",
    type=click.Choice(["scifi_crate", "stylized_rock", "metal_barrel", "wooden_crate"]),
    default="scifi_crate",
    help="Recipe preset to use"
)
def create_recipe(name, output, preset):
    """
    Create a new recipe file from a preset.

    NAME: Name for the new recipe
    """
    console.print(f"Creating recipe: {name}")

    # Load preset
    recipe = Recipe()
    recipe.name = name
    recipe.author = "Asset Pack Bot"

    if preset == "scifi_crate":
        recipe.description = "Sci-fi themed cargo crates and containers"
        recipe.asset_count = 100
        recipe.tags = ["sci-fi", "crate", "container", "futuristic", "space"]
        recipe.mesh.base_shape = "cube"
        recipe.mesh.style = "stylized"
        recipe.mesh.add_details = True
        recipe.mesh.detail_types = ["panels", "bolts", "vents"]
        recipe.mesh.edge_wear = 0.3
        recipe.texture.material_type = "metal"
        recipe.texture.style_keywords = ["sci-fi", "futuristic", "space station"]
        recipe.texture.color_palette = ["gray", "blue", "orange"]
        recipe.texture.weathering = 0.3
        recipe.texture.scratch_amount = 0.4

    elif preset == "stylized_rock":
        recipe.description = "Stylized rocks and boulders"
        recipe.asset_count = 100
        recipe.tags = ["rock", "stone", "boulder", "nature", "stylized"]
        recipe.mesh.base_shape = "sphere"
        recipe.mesh.style = "stylized"
        recipe.mesh.noise_strength = 0.3
        recipe.mesh.noise_scale = 2.0
        recipe.mesh.add_details = False
        recipe.mesh.add_cracks = True
        recipe.mesh.crack_density = 0.3
        recipe.texture.material_type = "stone"
        recipe.texture.style_keywords = ["rock", "natural", "rough"]
        recipe.texture.color_palette = ["gray", "brown"]
        recipe.texture.weathering = 0.5
        recipe.texture.dirt_amount = 0.4

    elif preset == "metal_barrel":
        recipe.description = "Industrial metal barrels and drums"
        recipe.asset_count = 100
        recipe.tags = ["barrel", "drum", "industrial", "metal", "container"]
        recipe.mesh.base_shape = "cylinder"
        recipe.mesh.style = "realistic"
        recipe.mesh.add_details = True
        recipe.mesh.detail_types = ["panels", "bolts"]
        recipe.mesh.add_dents = True
        recipe.mesh.dent_count = (0, 8)
        recipe.texture.material_type = "metal"
        recipe.texture.style_keywords = ["industrial", "rusty", "painted"]
        recipe.texture.color_palette = ["red", "blue", "yellow"]
        recipe.texture.weathering = 0.4
        recipe.texture.scratch_amount = 0.5

    elif preset == "wooden_crate":
        recipe.description = "Wooden crates and boxes"
        recipe.asset_count = 100
        recipe.tags = ["wood", "crate", "box", "storage", "rustic"]
        recipe.mesh.base_shape = "cube"
        recipe.mesh.style = "realistic"
        recipe.mesh.add_details = True
        recipe.mesh.detail_types = ["panels"]
        recipe.mesh.edge_wear = 0.2
        recipe.texture.material_type = "wood"
        recipe.texture.style_keywords = ["wooden", "planks", "cargo"]
        recipe.texture.color_palette = ["brown"]
        recipe.texture.weathering = 0.3
        recipe.texture.dirt_amount = 0.3

    # Save recipe
    output_path = Path(output) / f"{name.replace(' ', '_')}.yaml"
    recipe.save_yaml(str(output_path))

    console.print(f"[green]Recipe created: {output_path}[/green]")
    console.print(f"Edit this file to customize your asset pack, then run:")
    console.print(f"  [cyan]asset-bot generate {output_path}[/cyan]")


@main.command()
@click.option(
    "--output", "-o",
    type=click.Path(),
    default="config.yaml",
    help="Output path for config file"
)
def init_config(output):
    """
    Create a default configuration file.
    """
    config = Config()
    config.save_yaml(output)

    console.print(f"[green]Configuration file created: {output}[/green]")
    console.print("Edit this file to customize paths and settings.")


@main.command()
@click.argument("recipe_path", type=click.Path(exists=True))
def validate(recipe_path):
    """
    Validate a recipe file without generating assets.
    """
    console.print(f"Validating recipe: {recipe_path}")

    try:
        recipe = Recipe.from_yaml(recipe_path)
        config = Config()
        pipeline = AssetPipeline(config)

        issues = pipeline.validate_recipe(recipe)

        if issues:
            console.print("\n[yellow]Issues found:[/yellow]")
            for issue in issues:
                console.print(f"  - {issue}")
        else:
            console.print("\n[green]Recipe is valid![/green]")

        # Show summary
        console.print(f"\nRecipe: {recipe.name}")
        console.print(f"Assets: {recipe.asset_count}")
        console.print(f"Base Shape: {recipe.mesh.base_shape}")
        console.print(f"Style: {recipe.mesh.style}")

    except Exception as e:
        console.print(f"[red]Error loading recipe: {e}[/red]")


@main.command()
def list_presets():
    """
    List available recipe presets.
    """
    table = Table(title="Available Presets")
    table.add_column("Preset", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Base Shape", style="magenta")

    table.add_row(
        "scifi_crate",
        "Sci-fi cargo crates and containers",
        "cube"
    )
    table.add_row(
        "stylized_rock",
        "Stylized rocks and boulders",
        "sphere"
    )
    table.add_row(
        "metal_barrel",
        "Industrial metal barrels and drums",
        "cylinder"
    )
    table.add_row(
        "wooden_crate",
        "Wooden crates and boxes",
        "cube"
    )

    console.print(table)
    console.print("\nUse: [cyan]asset-bot create-recipe NAME --preset PRESET[/cyan]")


@main.command()
def info():
    """
    Show system information and check dependencies.
    """
    import platform

    table = Table(title="System Information")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")

    # Python version
    table.add_row("Python", platform.python_version())

    # Check Blender
    try:
        import subprocess
        result = subprocess.run(
            ["blender", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.split("\n")[0]
            table.add_row("Blender", version)
        else:
            table.add_row("Blender", "[red]Not found[/red]")
    except Exception:
        table.add_row("Blender", "[red]Not found[/red]")

    # Check PyTorch
    try:
        import torch
        cuda = "CUDA" if torch.cuda.is_available() else "CPU only"
        table.add_row("PyTorch", f"{torch.__version__} ({cuda})")
    except ImportError:
        table.add_row("PyTorch", "[yellow]Not installed[/yellow]")

    # Check Diffusers
    try:
        import diffusers
        table.add_row("Diffusers", diffusers.__version__)
    except ImportError:
        table.add_row("Diffusers", "[yellow]Not installed[/yellow]")

    # Check PIL
    try:
        from PIL import Image
        import PIL
        table.add_row("Pillow", PIL.__version__)
    except ImportError:
        table.add_row("Pillow", "[red]Not installed[/red]")

    console.print(table)

    console.print("\n[bold]Notes:[/bold]")
    console.print("- Blender is required for mesh generation")
    console.print("- PyTorch + Diffusers are optional (for AI textures)")
    console.print("- Without AI dependencies, procedural textures will be used")


if __name__ == "__main__":
    main()
