"""
AI-powered texture generation using Stable Diffusion.
"""

import os
import random
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageFilter, ImageOps
import numpy as np

from .recipe import TextureParameters
from .config import Config


class TextureGenerator:
    """Generates textures using AI (Stable Diffusion) or procedural methods."""

    def __init__(self, config: Config):
        self.config = config
        self.pipe = None
        self.device = "cuda" if config.texture.use_local else "cpu"

    def _load_pipeline(self):
        """Lazy load the Stable Diffusion pipeline."""
        if self.pipe is None:
            try:
                from diffusers import StableDiffusionPipeline
                import torch

                self.pipe = StableDiffusionPipeline.from_pretrained(
                    self.config.texture.model_id,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                )
                self.pipe = self.pipe.to(self.device)

                # Enable memory optimizations
                if self.device == "cuda":
                    self.pipe.enable_attention_slicing()

            except ImportError:
                print("Warning: diffusers not installed. Using procedural textures.")
                self.pipe = None
            except Exception as e:
                print(f"Warning: Could not load Stable Diffusion: {e}")
                self.pipe = None

    def generate_texture_set(
        self,
        params: TextureParameters,
        seed: int,
        output_path: str,
        asset_name: str,
    ) -> Dict[str, str]:
        """
        Generate a complete set of PBR textures.

        Args:
            params: Texture generation parameters
            seed: Random seed for variation
            output_path: Directory to save textures
            asset_name: Name for the asset

        Returns:
            Dictionary mapping texture type to file path
        """
        os.makedirs(output_path, exist_ok=True)
        results = {}

        # Generate base albedo/diffuse texture
        if params.generate_albedo:
            albedo_path = self._generate_albedo(params, seed, output_path, asset_name)
            results["albedo"] = albedo_path

            # Generate derived maps from albedo
            if params.generate_normal:
                normal_path = self._generate_normal_map(albedo_path, output_path, asset_name)
                results["normal"] = normal_path

            if params.generate_roughness:
                roughness_path = self._generate_roughness_map(
                    albedo_path, params, output_path, asset_name
                )
                results["roughness"] = roughness_path

            if params.generate_metallic:
                metallic_path = self._generate_metallic_map(
                    albedo_path, params, output_path, asset_name
                )
                results["metallic"] = metallic_path

            if params.generate_ao:
                ao_path = self._generate_ao_map(albedo_path, output_path, asset_name)
                results["ao"] = ao_path

            if params.generate_emission:
                emission_path = self._generate_emission_map(
                    albedo_path, params, output_path, asset_name
                )
                results["emission"] = emission_path

        return results

    def _generate_albedo(
        self,
        params: TextureParameters,
        seed: int,
        output_path: str,
        asset_name: str,
    ) -> str:
        """Generate the main albedo/diffuse texture."""
        output_file = os.path.join(output_path, f"{asset_name}_albedo.png")

        # Try AI generation first
        if self.config.texture.use_local:
            self._load_pipeline()

        if self.pipe is not None:
            image = self._generate_with_ai(params, seed)
        else:
            # Fallback to procedural generation
            image = self._generate_procedural(params, seed)

        # Make seamless if required
        if params.seamless:
            image = self._make_seamless(image)

        # Save
        image.save(output_file)
        return output_file

    def _generate_with_ai(self, params: TextureParameters, seed: int) -> Image.Image:
        """Generate texture using Stable Diffusion."""
        import torch

        prompt = params.build_prompt()

        generator = torch.Generator(device=self.device).manual_seed(seed)

        image = self.pipe(
            prompt=prompt,
            negative_prompt=self.config.texture.negative_prompt,
            width=params.texture_resolution,
            height=params.texture_resolution,
            num_inference_steps=self.config.texture.num_inference_steps,
            guidance_scale=self.config.texture.guidance_scale,
            generator=generator,
        ).images[0]

        return image

    def _generate_procedural(
        self, params: TextureParameters, seed: int
    ) -> Image.Image:
        """Generate texture procedurally (fallback method)."""
        random.seed(seed)
        np.random.seed(seed)

        resolution = params.texture_resolution
        image = Image.new("RGB", (resolution, resolution))
        pixels = np.array(image, dtype=np.float32)

        # Base color from palette
        if params.color_palette:
            base_color = self._parse_color(random.choice(params.color_palette))
        else:
            base_color = (128, 128, 128)

        # Fill with base color
        pixels[:, :] = base_color

        # Add noise pattern
        noise = np.random.randn(resolution, resolution, 3) * 20
        pixels += noise

        # Add material-specific patterns
        if params.material_type == "metal":
            pixels = self._add_metal_pattern(pixels, seed)
        elif params.material_type == "wood":
            pixels = self._add_wood_pattern(pixels, seed)
        elif params.material_type == "stone":
            pixels = self._add_stone_pattern(pixels, seed)

        # Add weathering
        if params.weathering > 0:
            pixels = self._add_weathering(pixels, params.weathering, seed)

        # Add dirt
        if params.dirt_amount > 0:
            pixels = self._add_dirt(pixels, params.dirt_amount, seed)

        # Add scratches
        if params.scratch_amount > 0:
            pixels = self._add_scratches(pixels, params.scratch_amount, seed)

        # Clamp values
        pixels = np.clip(pixels, 0, 255).astype(np.uint8)

        return Image.fromarray(pixels)

    def _parse_color(self, color_name: str) -> Tuple[int, int, int]:
        """Parse color name to RGB tuple."""
        colors = {
            "red": (180, 60, 60),
            "green": (60, 180, 60),
            "blue": (60, 60, 180),
            "gray": (128, 128, 128),
            "grey": (128, 128, 128),
            "orange": (200, 120, 60),
            "yellow": (200, 200, 60),
            "purple": (140, 60, 180),
            "brown": (120, 80, 60),
            "black": (40, 40, 40),
            "white": (220, 220, 220),
            "silver": (192, 192, 192),
            "gold": (212, 175, 55),
        }
        return colors.get(color_name.lower(), (128, 128, 128))

    def _add_metal_pattern(self, pixels: np.ndarray, seed: int) -> np.ndarray:
        """Add metallic brushed pattern."""
        h, w = pixels.shape[:2]

        # Add horizontal brush strokes
        for y in range(h):
            offset = np.sin(y * 0.1 + seed) * 10
            pixels[y, :] += offset

        return pixels

    def _add_wood_pattern(self, pixels: np.ndarray, seed: int) -> np.ndarray:
        """Add wood grain pattern."""
        h, w = pixels.shape[:2]

        for y in range(h):
            for x in range(w):
                # Wood grain
                grain = np.sin((x + y * 0.1) * 0.05 + seed) * 30
                pixels[y, x] += grain

        return pixels

    def _add_stone_pattern(self, pixels: np.ndarray, seed: int) -> np.ndarray:
        """Add stone/rock pattern."""
        # Add larger scale noise for stone texture
        h, w = pixels.shape[:2]
        large_noise = np.random.randn(h // 4, w // 4, 3) * 40
        large_noise = np.repeat(np.repeat(large_noise, 4, axis=0), 4, axis=1)
        pixels += large_noise[: h, : w]

        return pixels

    def _add_weathering(
        self, pixels: np.ndarray, amount: float, seed: int
    ) -> np.ndarray:
        """Add weathering effects."""
        np.random.seed(seed + 1000)

        # Darken edges and corners
        h, w = pixels.shape[:2]
        y, x = np.ogrid[:h, :w]

        # Distance from edges
        edge_dist = np.minimum(
            np.minimum(x, w - 1 - x), np.minimum(y, h - 1 - y)
        ).astype(float)
        edge_dist = edge_dist / edge_dist.max()

        # Apply darkening
        darkening = (1 - edge_dist) * amount * 50
        pixels -= darkening[:, :, np.newaxis]

        return pixels

    def _add_dirt(
        self, pixels: np.ndarray, amount: float, seed: int
    ) -> np.ndarray:
        """Add dirt/grime overlay."""
        np.random.seed(seed + 2000)
        h, w = pixels.shape[:2]

        # Create dirt patches
        dirt_mask = np.random.rand(h, w) < amount * 0.3
        dirt_color = np.array([60, 50, 40])

        for c in range(3):
            pixels[:, :, c] = np.where(
                dirt_mask, pixels[:, :, c] * 0.7 + dirt_color[c] * 0.3, pixels[:, :, c]
            )

        return pixels

    def _add_scratches(
        self, pixels: np.ndarray, amount: float, seed: int
    ) -> np.ndarray:
        """Add scratch marks."""
        np.random.seed(seed + 3000)
        h, w = pixels.shape[:2]

        num_scratches = int(amount * 50)

        for _ in range(num_scratches):
            # Random scratch line
            x1, y1 = np.random.randint(0, w), np.random.randint(0, h)
            length = np.random.randint(10, 50)
            angle = np.random.rand() * np.pi

            for i in range(length):
                x = int(x1 + i * np.cos(angle)) % w
                y = int(y1 + i * np.sin(angle)) % h
                pixels[y, x] = pixels[y, x] * 0.8 + np.array([200, 200, 200]) * 0.2

        return pixels

    def _make_seamless(self, image: Image.Image) -> Image.Image:
        """Make texture seamlessly tileable."""
        # Simple cross-blend method
        width, height = image.size
        result = image.copy()
        pixels = np.array(result, dtype=np.float32)

        # Blend edges
        blend_size = width // 8

        # Horizontal blending
        for x in range(blend_size):
            alpha = x / blend_size
            pixels[:, x] = pixels[:, x] * alpha + pixels[:, width - blend_size + x] * (1 - alpha)
            pixels[:, width - 1 - x] = pixels[:, width - 1 - x] * alpha + pixels[:, blend_size - 1 - x] * (1 - alpha)

        # Vertical blending
        for y in range(blend_size):
            alpha = y / blend_size
            pixels[y, :] = pixels[y, :] * alpha + pixels[height - blend_size + y, :] * (1 - alpha)
            pixels[height - 1 - y, :] = pixels[height - 1 - y, :] * alpha + pixels[blend_size - 1 - y, :] * (1 - alpha)

        pixels = np.clip(pixels, 0, 255).astype(np.uint8)
        return Image.fromarray(pixels)

    def _generate_normal_map(
        self, albedo_path: str, output_path: str, asset_name: str
    ) -> str:
        """Generate normal map from albedo using Sobel operators."""
        output_file = os.path.join(output_path, f"{asset_name}_normal.png")

        # Load albedo and convert to grayscale
        albedo = Image.open(albedo_path).convert("L")
        albedo_array = np.array(albedo, dtype=np.float32) / 255.0

        # Sobel operators
        h, w = albedo_array.shape
        normal_map = np.zeros((h, w, 3), dtype=np.float32)

        # Calculate gradients
        dx = np.zeros_like(albedo_array)
        dy = np.zeros_like(albedo_array)

        dx[:, 1:-1] = albedo_array[:, 2:] - albedo_array[:, :-2]
        dy[1:-1, :] = albedo_array[2:, :] - albedo_array[:-2, :]

        # Scale gradients
        strength = 2.0
        dx *= strength
        dy *= strength

        # Normal map: R = dx, G = dy, B = 1.0
        normal_map[:, :, 0] = dx * 0.5 + 0.5  # R
        normal_map[:, :, 1] = dy * 0.5 + 0.5  # G
        normal_map[:, :, 2] = 1.0  # B

        # Normalize
        normal_map = np.clip(normal_map * 255, 0, 255).astype(np.uint8)

        Image.fromarray(normal_map).save(output_file)
        return output_file

    def _generate_roughness_map(
        self, albedo_path: str, params: TextureParameters, output_path: str, asset_name: str
    ) -> str:
        """Generate roughness map."""
        output_file = os.path.join(output_path, f"{asset_name}_roughness.png")

        # Base roughness from albedo luminance (inverted)
        albedo = Image.open(albedo_path).convert("L")
        roughness = ImageOps.invert(albedo)

        # Adjust based on material type
        if params.material_type == "metal":
            # Metal is smoother
            roughness = ImageOps.autocontrast(roughness)
            roughness = roughness.point(lambda x: x * 0.6)
        elif params.material_type == "stone":
            # Stone is rougher
            roughness = roughness.point(lambda x: min(255, x * 1.3))

        # Add weathering effect
        if params.weathering > 0:
            # Weathered areas are rougher
            roughness = roughness.point(lambda x: min(255, x + params.weathering * 50))

        roughness.save(output_file)
        return output_file

    def _generate_metallic_map(
        self, albedo_path: str, params: TextureParameters, output_path: str, asset_name: str
    ) -> str:
        """Generate metallic map."""
        output_file = os.path.join(output_path, f"{asset_name}_metallic.png")

        albedo = Image.open(albedo_path)
        width, height = albedo.size

        if params.material_type == "metal":
            # High metallic value
            metallic = Image.new("L", (width, height), 200)
        else:
            # Non-metallic
            metallic = Image.new("L", (width, height), 20)

        metallic.save(output_file)
        return output_file

    def _generate_ao_map(
        self, albedo_path: str, output_path: str, asset_name: str
    ) -> str:
        """Generate ambient occlusion map."""
        output_file = os.path.join(output_path, f"{asset_name}_ao.png")

        # Simple AO approximation from albedo edges
        albedo = Image.open(albedo_path).convert("L")
        edges = albedo.filter(ImageFilter.FIND_EDGES)

        # Invert and blur for AO
        ao = ImageOps.invert(edges)
        ao = ao.filter(ImageFilter.GaussianBlur(radius=3))

        # Brighten overall
        ao = ao.point(lambda x: min(255, x + 100))

        ao.save(output_file)
        return output_file

    def _generate_emission_map(
        self, albedo_path: str, params: TextureParameters, output_path: str, asset_name: str
    ) -> str:
        """Generate emission map."""
        output_file = os.path.join(output_path, f"{asset_name}_emission.png")

        albedo = Image.open(albedo_path)
        width, height = albedo.size

        # Default: no emission
        emission = Image.new("RGB", (width, height), (0, 0, 0))

        # Add some glowing spots for sci-fi materials
        if "sci-fi" in params.style_keywords or "futuristic" in params.style_keywords:
            emission_array = np.zeros((height, width, 3), dtype=np.uint8)

            # Add random glowing spots
            np.random.seed(42)
            num_spots = 5
            for _ in range(num_spots):
                x, y = np.random.randint(0, width), np.random.randint(0, height)
                radius = np.random.randint(10, 30)

                for dy in range(-radius, radius):
                    for dx in range(-radius, radius):
                        dist = np.sqrt(dx**2 + dy**2)
                        if dist < radius:
                            px, py = (x + dx) % width, (y + dy) % height
                            intensity = int(255 * (1 - dist / radius))
                            emission_array[py, px] = [intensity, intensity // 2, 0]

            emission = Image.fromarray(emission_array)

        emission.save(output_file)
        return output_file
