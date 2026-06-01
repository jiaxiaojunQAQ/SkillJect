"""
Injection Layer Value Object

Extends injection layer definition, adding layer combination functionality.
"""

from enum import Enum

from src.shared.types import InjectionLayer


class InjectionLayerGroup(Enum):
    """Injection layer group"""

    SINGLE = "single"  # Single layer injection
    DOUBLE = "double"  # Double layer injection
    TRIPLE = "triple"  # Triple layer injection

    @classmethod
    def from_layer(cls, layer: InjectionLayer) -> "InjectionLayerGroup":
        """Get group from InjectionLayer"""
        if layer == InjectionLayer.ALL:
            return cls.TRIPLE
        elif layer in (InjectionLayer.DESCRIPTION_RESOURCE, InjectionLayer.INSTRUCTION_RESOURCE):
            return cls.DOUBLE
        else:
            return cls.SINGLE

    def get_layers(self) -> list[InjectionLayer]:
        """Get all layers in this group"""
        mapping = {
            InjectionLayerGroup.SINGLE: [
                InjectionLayer.DESCRIPTION,
                InjectionLayer.INSTRUCTION,
                InjectionLayer.RESOURCE,
            ],
            InjectionLayerGroup.DOUBLE: [
                InjectionLayer.DESCRIPTION_RESOURCE,
                InjectionLayer.INSTRUCTION_RESOURCE,
            ],
            InjectionLayerGroup.TRIPLE: [
                InjectionLayer.ALL,
            ],
        }
        return mapping.get(self, [])

    def get_description(self) -> str:
        """Get group description"""
        descriptions = {
            InjectionLayerGroup.SINGLE: "Single layer injection - Inject malicious payload at only one location",
            InjectionLayerGroup.DOUBLE: "Double layer injection - Inject malicious payload at two locations simultaneously",
            InjectionLayerGroup.TRIPLE: "Triple layer injection - Inject malicious payload at all locations",
        }
        return descriptions.get(self, "Unknown")


class InjectionPointInfo:
    """Injection point information

    Provides detailed information and locations about injection layers.
    """

    _layer_info = {
        InjectionLayer.DESCRIPTION: {
            "name": "Description layer",
            "location": "description field in SKILL.md frontmatter",
            "accessibility": "Low - requires modifying SKILL.md",
            "detection_difficulty": "Medium",
        },
        InjectionLayer.INSTRUCTION: {
            "name": "Instruction layer",
            "location": "Main content of SKILL.md",
            "accessibility": "Low - requires modifying SKILL.md",
            "detection_difficulty": "High",
        },
        InjectionLayer.RESOURCE: {
            "name": "Resource layer",
            "location": "Referenced resource files (e.g., README.md)",
            "accessibility": "Medium - requires modifying resource files",
            "detection_difficulty": "High",
        },
        InjectionLayer.DESCRIPTION_RESOURCE: {
            "name": "Description + Resource double layer",
            "location": "description field + resource files",
            "accessibility": "Low - requires modifying multiple files",
            "detection_difficulty": "Medium",
        },
        InjectionLayer.INSTRUCTION_RESOURCE: {
            "name": "Instruction + Resource double layer",
            "location": "Main content + resource files",
            "accessibility": "Low - requires modifying multiple files",
            "detection_difficulty": "High",
        },
        InjectionLayer.ALL: {
            "name": "Full layer injection",
            "location": "description + main content + resource files",
            "accessibility": "Very low - requires modifying multiple files",
            "detection_difficulty": "Very high",
        },
    }

    @classmethod
    def get_info(cls, layer: InjectionLayer) -> dict[str, str]:
        """Get injection layer information"""
        return cls._layer_info.get(layer, {})

    @classmethod
    def get_name(cls, layer: InjectionLayer) -> str:
        """Get injection layer name"""
        return cls.get_info(layer).get("name", "Unknown")

    @classmethod
    def get_location(cls, layer: InjectionLayer) -> str:
        """Get injection location"""
        return cls.get_info(layer).get("location", "Unknown")

    @classmethod
    def is_multi_layer(cls, layer: InjectionLayer) -> bool:
        """Check if multi-layer injection"""
        group = InjectionLayerGroup.from_layer(layer)
        return group != InjectionLayerGroup.SINGLE

    @classmethod
    def get_component_layers(cls, layer: InjectionLayer) -> list[InjectionLayer]:
        """Get component layers of combined layer"""
        if layer == InjectionLayer.ALL:
            return [
                InjectionLayer.DESCRIPTION,
                InjectionLayer.INSTRUCTION,
                InjectionLayer.RESOURCE,
            ]
        elif layer == InjectionLayer.DESCRIPTION_RESOURCE:
            return [InjectionLayer.DESCRIPTION, InjectionLayer.RESOURCE]
        elif layer == InjectionLayer.INSTRUCTION_RESOURCE:
            return [InjectionLayer.INSTRUCTION, InjectionLayer.RESOURCE]
        else:
            return [layer]
