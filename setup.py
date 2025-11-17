from setuptools import setup, find_packages

setup(
    name="asset-pack-bot",
    version="1.0.0",
    description="Automated 3D Game Asset Pack Generator",
    author="Asset Pack Bot",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "click>=8.0.0",
        "pyyaml>=6.0",
        "pillow>=9.0.0",
        "numpy>=1.21.0",
        "requests>=2.28.0",
        "tqdm>=4.64.0",
        "jinja2>=3.1.0",
        "colorama>=0.4.6",
        "rich>=12.0.0",
    ],
    extras_require={
        "ai": [
            "diffusers>=0.21.0",
            "transformers>=4.30.0",
            "accelerate>=0.20.0",
            "torch>=2.0.0",
            "safetensors>=0.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "asset-bot=asset_bot.cli:main",
        ],
    },
    python_requires=">=3.8",
)
