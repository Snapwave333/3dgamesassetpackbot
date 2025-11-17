"""
Unity package (.unitypackage) builder.
"""

import os
import json
import tarfile
import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

from .config import Config


class UnityPackager:
    """Creates Unity-compatible .unitypackage files."""

    def __init__(self, config: Config):
        self.config = config

    def create_package(
        self,
        assets: List[Dict[str, Any]],
        package_name: str,
        output_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a .unitypackage file from generated assets.

        Args:
            assets: List of asset dictionaries with file paths
            package_name: Name for the package
            output_path: Directory to save the package
            metadata: Optional package metadata

        Returns:
            Path to the created .unitypackage file
        """
        os.makedirs(output_path, exist_ok=True)

        # Create temporary directory for package structure
        with tempfile.TemporaryDirectory() as temp_dir:
            package_root = Path(temp_dir) / "package"
            package_root.mkdir()

            # Process each asset
            for asset in assets:
                self._add_asset_to_package(asset, package_root)

            # Create the tarball (.unitypackage is just a gzipped tar)
            package_file = os.path.join(output_path, f"{package_name}.unitypackage")

            with tarfile.open(package_file, "w:gz") as tar:
                for item in package_root.iterdir():
                    tar.add(str(item), arcname=item.name)

            # Create metadata file
            if metadata:
                meta_file = os.path.join(output_path, f"{package_name}_metadata.json")
                with open(meta_file, "w") as f:
                    json.dump(metadata, f, indent=2)

            return package_file

    def _add_asset_to_package(
        self, asset: Dict[str, Any], package_root: Path
    ) -> None:
        """
        Add a single asset to the package structure.

        Args:
            asset: Asset dictionary with paths and metadata
            package_root: Root directory for package structure
        """
        asset_name = asset.get("asset_name", "unnamed")

        # Unity package structure:
        # Each asset gets a GUID folder containing:
        # - asset (the actual file)
        # - asset.meta (metadata file)
        # - pathname (path in Unity project)

        # Process different file types
        files_to_package = []

        # Add mesh files
        if "fbx" in asset:
            files_to_package.append(
                (asset["fbx"], f"Assets/Meshes/{asset_name}.fbx", "Mesh")
            )

        # Add textures
        if "textures" in asset:
            for tex_type, tex_path in asset["textures"].items():
                if os.path.exists(tex_path):
                    unity_path = f"Assets/Textures/{asset_name}_{tex_type}.png"
                    files_to_package.append((tex_path, unity_path, "Texture"))

        # Add LODs
        if "lods" in asset:
            for lod_name, lod_data in asset["lods"].items():
                if "fbx" in lod_data:
                    unity_path = f"Assets/Meshes/{asset_name}_{lod_name}.fbx"
                    files_to_package.append((lod_data["fbx"], unity_path, "Mesh"))

        # Create package entries
        for source_path, unity_path, asset_type in files_to_package:
            if os.path.exists(source_path):
                self._create_package_entry(
                    source_path, unity_path, asset_type, package_root
                )

        # Create prefab
        if self.config.packaging.include_prefabs:
            self._create_prefab(asset, package_root)

        # Create material
        if self.config.packaging.include_materials and "textures" in asset:
            self._create_material(asset, package_root)

    def _create_package_entry(
        self,
        source_path: str,
        unity_path: str,
        asset_type: str,
        package_root: Path,
    ) -> str:
        """
        Create a single package entry with GUID folder structure.

        Args:
            source_path: Path to the source file
            unity_path: Path within Unity project
            asset_type: Type of asset (Mesh, Texture, etc.)
            package_root: Root of package structure

        Returns:
            Generated GUID
        """
        # Generate GUID from file path
        guid = self._generate_guid(unity_path)

        # Create GUID folder
        guid_folder = package_root / guid
        guid_folder.mkdir()

        # Copy the actual asset
        asset_file = guid_folder / "asset"
        shutil.copy2(source_path, asset_file)

        # Create pathname file
        pathname_file = guid_folder / "pathname"
        with open(pathname_file, "w") as f:
            f.write(unity_path)

        # Create meta file
        meta_content = self._generate_meta_file(unity_path, guid, asset_type)
        meta_file = guid_folder / "asset.meta"
        with open(meta_file, "w") as f:
            f.write(meta_content)

        return guid

    def _generate_guid(self, path: str) -> str:
        """Generate a deterministic GUID from path."""
        hash_obj = hashlib.md5(path.encode())
        return hash_obj.hexdigest()

    def _generate_meta_file(self, path: str, guid: str, asset_type: str) -> str:
        """Generate Unity .meta file content."""
        meta = {
            "fileFormatVersion": 2,
            "guid": guid,
            "timeCreated": 1234567890,
            "licenseType": "Free",
        }

        if asset_type == "Mesh":
            meta["ModelImporter"] = {
                "serializedVersion": 23,
                "fileIDToRecycleName": {},
                "meshes": {
                    "lODScreenPercentages": [],
                    "globalScale": 1,
                    "meshCompression": 0,
                    "addColliders": False,
                    "useSRGBMaterialColor": True,
                    "importVisibility": True,
                    "importBlendShapes": True,
                    "importCameras": True,
                    "importLights": True,
                    "swapUVChannels": False,
                    "generateSecondaryUV": False,
                    "useFileUnits": True,
                    "keepQuads": False,
                    "weldVertices": True,
                    "preserveHierarchy": False,
                    "skinWeightsMode": 0,
                    "maxBonesPerVertex": 4,
                    "minBoneWeight": 0.001,
                    "meshOptimizationFlags": -1,
                    "indexFormat": 0,
                    "secondaryUVAngleDistortion": 8,
                    "secondaryUVAreaDistortion": 15.000001,
                    "secondaryUVHardAngle": 88,
                    "secondaryUVPackMargin": 4,
                },
                "tangentSpace": {
                    "normalSmoothAngle": 60,
                    "normalImportMode": 0,
                    "tangentImportMode": 3,
                    "normalCalculationMode": 4,
                },
                "importAnimation": 1,
                "copyAvatar": 0,
                "humanDescription": {
                    "serializedVersion": 3,
                    "human": [],
                    "skeleton": [],
                    "armTwist": 0.5,
                    "foreArmTwist": 0.5,
                    "upperLegTwist": 0.5,
                    "legTwist": 0.5,
                    "armStretch": 0.05,
                    "legStretch": 0.05,
                    "feetSpacing": 0,
                    "hasTranslationDoF": 0,
                },
            }

        elif asset_type == "Texture":
            meta["TextureImporter"] = {
                "serializedVersion": 12,
                "mipmaps": {
                    "mipMapMode": 0,
                    "enableMipMap": 1,
                    "sRGBTexture": 1,
                    "linearTexture": 0,
                    "fadeOut": 0,
                    "borderMipMap": 0,
                    "mipMapsPreserveCoverage": 0,
                },
                "bumpmap": {
                    "convertToNormalMap": 0,
                    "externalNormalMap": 0,
                    "heightScale": 0.25,
                    "normalMapFilter": 0,
                },
                "isReadable": 0,
                "grayScaleToAlpha": 0,
                "generateCubemap": 6,
                "cubemapConvolution": 0,
                "seamlessCubemap": 0,
                "textureFormat": 1,
                "maxTextureSize": 2048,
                "textureSettings": {
                    "serializedVersion": 2,
                    "filterMode": 1,
                    "aniso": 1,
                    "mipBias": 0,
                    "wrapU": 0,
                    "wrapV": 0,
                    "wrapW": 0,
                },
                "nPOTScale": 1,
                "lightmap": 0,
                "compressionQuality": 50,
                "spriteMode": 0,
                "spriteExtrude": 1,
                "spriteMeshType": 1,
                "alignment": 0,
                "spritePivot": {"x": 0.5, "y": 0.5},
                "spritePixelsToUnits": 100,
                "spriteBorder": {"x": 0, "y": 0, "z": 0, "w": 0},
                "spriteGenerateFallbackPhysicsShape": 1,
                "alphaUsage": 1,
                "alphaIsTransparency": 0,
                "spriteTessellationDetail": -1,
                "textureType": 0,
                "textureShape": 1,
                "singleChannelComponent": 0,
            }

        return yaml.dump(meta, default_flow_style=False, sort_keys=False)

    def _create_prefab(self, asset: Dict[str, Any], package_root: Path) -> None:
        """Create a Unity prefab for the asset."""
        asset_name = asset.get("asset_name", "unnamed")
        unity_path = f"Assets/Prefabs/{asset_name}.prefab"

        # Generate GUID
        guid = self._generate_guid(unity_path)
        guid_folder = package_root / guid
        guid_folder.mkdir()

        # Create pathname
        pathname_file = guid_folder / "pathname"
        with open(pathname_file, "w") as f:
            f.write(unity_path)

        # Create prefab content (simplified YAML format)
        prefab_content = f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!1 &1
GameObject:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  serializedVersion: 6
  m_Component:
  - component: {{fileID: 4}}
  - component: {{fileID: 33}}
  - component: {{fileID: 23}}
  m_Layer: 0
  m_Name: {asset_name}
  m_TagString: Untagged
  m_Icon: {{fileID: 0}}
  m_NavMeshLayer: 0
  m_StaticEditorFlags: 0
  m_IsActive: 1
--- !u!4 &4
Transform:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 1}}
  m_LocalRotation: {{x: 0, y: 0, z: 0, w: 1}}
  m_LocalPosition: {{x: 0, y: 0, z: 0}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
  m_Children: []
  m_Father: {{fileID: 0}}
  m_RootOrder: 0
  m_LocalEulerAnglesHint: {{x: 0, y: 0, z: 0}}
--- !u!33 &33
MeshFilter:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 1}}
  m_Mesh: {{fileID: 0}}
--- !u!23 &23
MeshRenderer:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 1}}
  m_Enabled: 1
  m_CastShadows: 1
  m_ReceiveShadows: 1
  m_DynamicOccludee: 1
  m_MotionVectors: 1
  m_LightProbeUsage: 1
  m_ReflectionProbeUsage: 1
  m_RenderingLayerMask: 1
  m_RendererPriority: 0
  m_Materials:
  - {{fileID: 0}}
  m_StaticBatchInfo:
    firstSubMesh: 0
    subMeshCount: 0
  m_StaticBatchRoot: {{fileID: 0}}
  m_ProbeAnchor: {{fileID: 0}}
  m_LightProbeVolumeOverride: {{fileID: 0}}
  m_ScaleInLightmap: 1
  m_ReceiveGI: 1
  m_PreserveUVs: 0
  m_IgnoreNormalsForChartDetection: 0
  m_ImportantGI: 0
  m_StitchLightmapSeams: 1
  m_SelectedEditorRenderState: 3
  m_MinimumChartSize: 4
  m_AutoUVMaxDistance: 0.5
  m_AutoUVMaxAngle: 89
  m_LightmapParameters: {{fileID: 0}}
  m_SortingLayerID: 0
  m_SortingLayer: 0
  m_SortingOrder: 0
"""

        # Write prefab file
        asset_file = guid_folder / "asset"
        with open(asset_file, "w") as f:
            f.write(prefab_content)

        # Create meta file
        meta_content = self._generate_meta_file(unity_path, guid, "Prefab")
        meta_file = guid_folder / "asset.meta"
        with open(meta_file, "w") as f:
            f.write(meta_content)

    def _create_material(self, asset: Dict[str, Any], package_root: Path) -> None:
        """Create a Unity material for the asset."""
        asset_name = asset.get("asset_name", "unnamed")
        unity_path = f"Assets/Materials/{asset_name}_Material.mat"

        # Generate GUID
        guid = self._generate_guid(unity_path)
        guid_folder = package_root / guid
        guid_folder.mkdir()

        # Create pathname
        pathname_file = guid_folder / "pathname"
        with open(pathname_file, "w") as f:
            f.write(unity_path)

        # Create material content (Standard shader)
        material_content = f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 6
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_Name: {asset_name}_Material
  m_Shader: {{fileID: 46, guid: 0000000000000000f000000000000000, type: 0}}
  m_SavedProperties:
    serializedVersion: 3
    m_TexEnvs:
    - _MainTex:
        m_Texture: {{fileID: 0}}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _BumpMap:
        m_Texture: {{fileID: 0}}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _MetallicGlossMap:
        m_Texture: {{fileID: 0}}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _OcclusionMap:
        m_Texture: {{fileID: 0}}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    m_Floats:
    - _BumpScale: 1
    - _Cutoff: 0.5
    - _DetailNormalMapScale: 1
    - _DstBlend: 0
    - _GlossMapScale: 1
    - _Glossiness: 0.5
    - _GlossyReflections: 1
    - _Metallic: 0
    - _Mode: 0
    - _OcclusionStrength: 1
    - _Parallax: 0.02
    - _SmoothnessTextureChannel: 0
    - _SpecularHighlights: 1
    - _SrcBlend: 1
    - _UVSec: 0
    - _ZWrite: 1
    m_Colors:
    - _Color: {{r: 1, g: 1, b: 1, a: 1}}
    - _EmissionColor: {{r: 0, g: 0, b: 0, a: 1}}
"""

        # Write material file
        asset_file = guid_folder / "asset"
        with open(asset_file, "w") as f:
            f.write(material_content)

        # Create meta file
        meta_content = self._generate_meta_file(unity_path, guid, "Material")
        meta_file = guid_folder / "asset.meta"
        with open(meta_file, "w") as f:
            f.write(meta_content)

    def create_asset_store_description(
        self, package_name: str, asset_count: int, tags: List[str]
    ) -> str:
        """Generate an asset store description template."""
        return f"""
# {package_name}

## Description
This asset pack contains {asset_count} unique, procedurally generated 3D assets.
Each asset includes:
- High-quality FBX meshes
- Multiple LOD levels for performance optimization
- Complete PBR texture sets (Albedo, Normal, Roughness, Metallic, AO)
- Pre-configured Unity materials
- Ready-to-use prefabs

## Features
- Unique variations - no two assets are exactly alike
- Optimized for real-time rendering
- LOD support for large-scale scenes
- PBR-ready materials
- Clean UV mapping

## Technical Details
- Poly Count: Varies (LOD0 ~500-2000 tris, LOD3 ~50-200 tris)
- Texture Resolution: 1024x1024 (configurable)
- File Formats: FBX, OBJ
- Unity Version: {self.config.packaging.unity_version}+

## Tags
{', '.join(tags)}

## License
Commercial use allowed. No redistribution of source files.
"""
