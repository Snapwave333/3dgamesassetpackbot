# 3D Game Asset Pack Bot

An automated pipeline for generating thousands of unique 3D game assets with procedural meshes, AI-generated textures, automatic LOD generation, and Unity packaging.

## Features

- **Procedural Mesh Generation**: Create unique 3D meshes using Blender with customizable parameters
- **AI Texture Generation**: Generate seamless PBR textures using Stable Diffusion
- **Automatic UV Unwrapping**: Smart UV projection for optimal texture mapping
- **LOD Generation**: Multiple levels of detail for performance optimization
- **Unity Packaging**: Export directly to `.unitypackage` format
- **Batch Processing**: Generate hundreds or thousands of assets automatically
- **Recipe System**: Define asset packs with YAML configuration files
- **Complete PBR Pipeline**: Albedo, Normal, Roughness, Metallic, AO, and Emission maps

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/3dgamesassetpackbot.git
cd 3dgamesassetpackbot

# Install Python dependencies
pip install -e .

# For AI texture generation (optional)
pip install -e ".[ai]"
```

### 2. Prerequisites

- **Python 3.8+**
- **Blender 3.0+** (must be accessible from command line)
- **PyTorch + CUDA** (optional, for AI texture generation)

### 3. Generate Your First Asset Pack

```bash
# Create a recipe from a preset
asset-bot create-recipe "My Sci-Fi Crates" --preset scifi_crate

# Generate the asset pack
asset-bot generate My_Sci-Fi_Crates.yaml
```

## Usage

### CLI Commands

```bash
# Generate assets from a recipe
asset-bot generate recipe.yaml

# Create a new recipe from preset
asset-bot create-recipe "Pack Name" --preset scifi_crate

# Validate a recipe
asset-bot validate recipe.yaml

# List available presets
asset-bot list-presets

# Check system dependencies
asset-bot info

# Create default configuration
asset-bot init-config
```

### Command Options

```bash
asset-bot generate recipe.yaml \
  --config config.yaml \     # Custom configuration file
  --output ./my_output \     # Override output directory
  --count 100 \              # Override asset count
  --parallel 4 \             # Number of parallel workers
  --dry-run                  # Validate without generating
```

## Recipe System

Recipes define what assets to generate using YAML files:

```yaml
name: "1000 Stylized Sci-Fi Crates Pack"
description: "Sci-fi cargo crates for space stations"
asset_count: 1000
tags: [sci-fi, crate, futuristic]

mesh:
  base_shape: "cube"           # cube, sphere, cylinder, cone
  size_x: [0.8, 1.4]          # Min/max size range
  subdivisions: 2              # Mesh detail level
  add_details: true            # Add panels, bolts, vents
  edge_wear: 0.3               # Beveled edges
  add_dents: true              # Damage variations

texture:
  material_type: "metal"       # metal, wood, stone, plastic
  style_keywords: ["sci-fi", "futuristic"]
  color_palette: ["gray", "blue", "orange"]
  weathering: 0.35             # Wear and tear
  texture_resolution: 1024     # Texture size
  generate_normal: true        # PBR maps
  generate_roughness: true
  generate_metallic: true
```

### Available Presets

| Preset | Description | Base Shape |
|--------|-------------|------------|
| `scifi_crate` | Sci-fi cargo crates | Cube |
| `stylized_rock` | Stylized rocks/boulders | Sphere |
| `metal_barrel` | Industrial metal barrels | Cylinder |
| `wooden_crate` | Wooden cargo crates | Cube |

## Configuration

Create a `config.yaml` file to customize the pipeline:

```yaml
output_dir: "./output"
blender:
  executable_path: "blender"
  use_gpu: true

texture:
  model_id: "stabilityai/stable-diffusion-2-1"
  use_local: true              # Use local Stable Diffusion
  resolution: 1024
  guidance_scale: 7.5

lod:
  generate_lods: true
  lod_levels: [1.0, 0.5, 0.25, 0.1]

packaging:
  include_prefabs: true
  include_materials: true
  unity_version: "2021.3"

max_workers: 4
log_level: "INFO"
```

## Output Structure

```
output/
└── My_Asset_Pack/
    ├── recipe.yaml              # Copy of generation recipe
    ├── generation_stats.json    # Performance statistics
    ├── ASSET_STORE_DESCRIPTION.md
    ├── meshes/
    │   ├── asset_0001.fbx
    │   ├── asset_0001.obj
    │   ├── asset_0001.blend
    │   └── ...
    ├── textures/
    │   ├── asset_0001_albedo.png
    │   ├── asset_0001_normal.png
    │   ├── asset_0001_roughness.png
    │   ├── asset_0001_metallic.png
    │   ├── asset_0001_ao.png
    │   └── ...
    ├── lods/
    │   ├── asset_0001_LOD0.fbx
    │   ├── asset_0001_LOD1.fbx
    │   ├── asset_0001_LOD2.fbx
    │   └── ...
    └── package/
        ├── My_Asset_Pack.unitypackage
        └── My_Asset_Pack_metadata.json
```

## Python API

```python
from asset_bot import Config, Recipe, AssetPipeline

# Load configuration
config = Config.from_yaml("config.yaml")

# Load or create recipe
recipe = Recipe.from_yaml("recipe.yaml")
# Or programmatically:
recipe = Recipe()
recipe.name = "Custom Pack"
recipe.asset_count = 100
recipe.mesh.base_shape = "cube"
recipe.texture.material_type = "metal"

# Create pipeline
pipeline = AssetPipeline(config)

# Validate
issues = pipeline.validate_recipe(recipe)
print(f"Issues: {issues}")

# Estimate time
time_estimate = pipeline.estimate_generation_time(recipe)
print(f"Estimated time: {time_estimate:.2f} seconds")

# Generate!
stats = pipeline.generate_asset_pack(recipe)
print(f"Generated {stats['successfully_generated']} assets")
```

## The Business Model

1. **Define**: Create a recipe (e.g., "stylized sci-fi crates")
2. **Generate**: Run the bot for a week to create 1000+ unique assets
3. **Package**: Automatically bundled into Unity/Unreal-ready packages
4. **Sell**: Upload to Unity Asset Store or Unreal Marketplace

**Example**: A "1000 Stylized Sci-Fi Crates Pack" selling for $75 on the Unity Asset Store.

## Performance Tips

- **GPU Acceleration**: Enable CUDA for faster texture generation
- **Batch Size**: Adjust based on available RAM
- **Parallel Workers**: Match to CPU core count
- **LOD Levels**: Reduce for faster generation
- **Texture Resolution**: 512px for faster iteration, 2048px for production

## Estimated Generation Times

| Assets | Without AI | With AI (GPU) | With AI (CPU) |
|--------|-----------|---------------|---------------|
| 100 | ~10 min | ~25 min | ~4 hours |
| 500 | ~50 min | ~2 hours | ~20 hours |
| 1000 | ~1.7 hours | ~4 hours | ~40 hours |

*Times vary based on hardware and complexity settings*

## Dependencies

### Required
- Python 3.8+
- Blender 3.0+ (command-line accessible)
- NumPy
- Pillow (PIL)
- PyYAML
- Click
- Rich (CLI formatting)
- tqdm (progress bars)

### Optional (AI Textures)
- PyTorch 2.0+
- Diffusers
- Transformers
- Accelerate
- CUDA toolkit (for GPU acceleration)

## Troubleshooting

### Blender not found
```bash
# Add Blender to PATH or specify in config
blender:
  executable_path: "/usr/bin/blender"
```

### Out of memory during texture generation
- Reduce `texture_resolution` in recipe
- Disable AI textures: `use_local: false`
- Reduce `batch_size` in config

### Slow generation
- Enable GPU: `use_gpu: true`
- Reduce `subdivisions` in mesh parameters
- Lower `num_inference_steps` for AI textures

## Future Enhancements

- [ ] Unreal Engine package support
- [ ] More base shapes (custom meshes)
- [ ] Advanced texture compositing
- [ ] Animation/rigging support
- [ ] Cloud-based generation
- [ ] Asset marketplace integration
- [ ] Real-time preview

## License

MIT License - Commercial use allowed.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Support

For issues and feature requests, please open a GitHub issue.

---

**Happy Asset Generation!** 🎮
