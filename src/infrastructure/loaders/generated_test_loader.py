"""
Test Case Loader

Loads pre-generated test cases from generated_tests directory for direct use during test execution
instead of runtime reinjection.
"""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from src.domain.testing.value_objects.execution_config import GenerationConfig


def _extract_dataset_from_path(test_dir: Path) -> str:
    """Extract dataset name from test_dir path.

    test_dir format: generated_tests/{dataset}/{method}/
    Example: generated_tests/skills_from_skill0/template_injection/

    Args:
        test_dir: Test directory path

    Returns:
        Dataset name, returns "skills_from_skill0" if unable to extract
    """
    # Convert to Path object
    test_dir = Path(test_dir)

    # Find generated_tests directory
    parts = test_dir.parts
    try:
        generated_tests_idx = parts.index("generated_tests")
        # dataset is the next level after generated_tests
        if generated_tests_idx + 1 < len(parts):
            return parts[generated_tests_idx + 1]
    except ValueError:
        pass

    # Default value
    return "skills_from_skill0"


def load_generated_test(test_id: str, config_path: str | None = None) -> dict | None:
    """Load pre-generated test case from generated_tests.

    New directory structure: {skill_name} / {attack_type} / iteration_0 /

    Args:
        test_id: Test ID, format is {skill_name}_{attack_type}
                Example: adaptyv_information_disclosure
        config_path: Configuration file path (optional, for dynamically calculating test_dir)

    Returns:
        Test case dictionary containing:
        - test_id: Test ID
        - skill_path: Path to injected SKILL.md file
        - layer: Injection layer (description/instruction/resource)
        - attack_type: Attack type
        - payload_name: Payload name
        - severity: Severity level
        - injected_resource_file: Injected resource file (only for RESOURCE layer)
        - should_be_blocked: Whether it should be blocked
        - dataset: Dataset name
        Or None (if not found)
    """
    from .paths import get_project_paths

    paths = get_project_paths(config_path)
    test_dir = Path(paths["test_dir"])

    # Extract dataset from test_dir
    # test_dir format: generated_tests/{dataset}/{method}/
    # Example: generated_tests/skills_from_skill0/template_injection/
    dataset = _extract_dataset_from_path(test_dir)

    # Parse test_id to get skill_name and attack_type
    # New format: {skill_name}_{attack_type}
    parts = test_id.split("_")
    if len(parts) < 2:
        return None

    # 4 core attack types
    attack_types = [
        "information_disclosure",
        "privilege_escalation",
        "unauthorized_write",
        "backdoor_injection",
    ]

    # Match attack type from back (since skill_name may contain underscores)
    attack_type = None
    for at in attack_types:
        if test_id.endswith(at):
            attack_type = at
            skill_name = test_id[: -(len(at) + 1)]  # +1 for underscore
            break

    if not attack_type:
        return None

    # Try new format path: {skill_name}/{attack_type}/iteration_0/SKILL.md
    candidate_path = test_dir / skill_name / attack_type / "iteration_0" / "SKILL.md"
    if candidate_path.exists():
        # Try to get additional info from metadata (if available)
        metadata_info = _try_get_metadata(test_dir, test_id)
        return {
            "test_id": test_id,
            "skill_path": str(candidate_path),
            "layer": metadata_info.get("injection_layer", "instruction")
            if metadata_info
            else "instruction",
            "attack_type": attack_type,
            "payload_name": metadata_info.get("payload_name") if metadata_info else None,
            "severity": metadata_info.get("severity") if metadata_info else None,
            "injected_resource_file": metadata_info.get("injected_resource_file", "")
            if metadata_info
            else "",
            "should_be_blocked": metadata_info.get("should_be_blocked", True)
            if metadata_info
            else True,
            "test_case_dir": str(test_dir / skill_name / attack_type / "iteration_0"),
            "injection_points": metadata_info.get("injection_points", []) if metadata_info else [],
            "dataset": dataset,
            "skill_name": skill_name,
        }

    # If new format lookup fails, try finding through metadata
    metadata_file = test_dir / "test_metadata.json"
    if not metadata_file.exists():
        return None

    with open(metadata_file) as f:
        metadata = json.load(f)

    # Find matching test
    tests = metadata.get("tests", [])
    matching = [t for t in tests if t.get("test_id") == test_id]

    if not matching:
        return None

    test_metadata = matching[0]

    # Build path using new directory structure
    skill_path = test_dir / skill_name / attack_type / "iteration_0" / "SKILL.md"

    # Verify SKILL.md exists
    if not skill_path.exists():
        return None

    return {
        "test_id": test_metadata["test_id"],
        "skill_path": str(skill_path),
        "layer": test_metadata.get("injection_layer", "instruction"),
        "attack_type": attack_type,
        "payload_name": test_metadata.get("payload_name"),
        "severity": test_metadata.get("severity"),
        "injected_resource_file": test_metadata.get("injected_resource_file", ""),
        "should_be_blocked": test_metadata.get("should_be_blocked", True),
        "test_case_dir": str(test_dir / skill_name / attack_type / "iteration_0"),
        "dataset": dataset,
        "skill_name": skill_name,
    }


def _try_get_metadata(test_dir: Path, test_id: str) -> dict | None:
    """Try to get additional test information from metadata file.

    Args:
        test_dir: Test directory
        test_id: Test ID

    Returns:
        Metadata dictionary (if found), otherwise None
    """
    metadata_file = test_dir / "test_metadata.json"
    if not metadata_file.exists():
        return None

    try:
        with open(metadata_file) as f:
            metadata = json.load(f)

        tests = metadata.get("tests", [])
        matching = [t for t in tests if t.get("test_id") == test_id]

        if matching:
            return matching[0]
    except Exception:
        pass

    return None


def list_generated_tests(
    layer: str | None = None,
    attack_type: str | None = None,
    skill_name: str | None = None,
    config_path: str | None = None,
) -> list[dict]:
    """List pre-generated test cases.

    New directory structure: {skill_name} / {attack_type} / iteration_0 /

    Args:
        layer: Filter by injection layer (description/instruction/resource)
        attack_type: Filter by attack type
        skill_name: Filter by skill name
        config_path: Configuration file path (optional, for dynamically calculating test_dir)

    Returns:
        List of test cases, each element contains:
        - test_id: Test ID
        - name: Test name
        - layer: Injection layer
        - attack_type: Attack type
        - payload_name: Payload name
        - severity: Severity level
        - skill_path: SKILL.md file path
        - test_case_dir: Test case directory path
        - skill_name: Skill name
    """
    from .paths import get_project_paths

    paths = get_project_paths(config_path)
    test_dir = Path(paths["test_dir"])

    # Try loading from metadata file
    metadata_file = test_dir / "test_metadata.json"
    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata = json.load(f)
        tests = metadata.get("tests", [])

        # Apply filters
        if layer:
            tests = [t for t in tests if t.get("injection_layer") == layer]
        if attack_type:
            tests = [t for t in tests if t.get("attack_type") == attack_type]
        if skill_name:
            tests = [t for t in tests if t.get("skill_name") == skill_name]

        # Build return result (using new directory structure)
        result = []
        for t in tests:
            test_skill_name = t.get("skill_name")
            test_attack_type = t.get("attack_type", "information_disclosure")
            test_id = t["test_id"]
            skill_path = test_dir / test_skill_name / test_attack_type / "iteration_0" / "SKILL.md"

            result.append(
                {
                    "test_id": test_id,
                    "name": t.get("name", ""),
                    "layer": t.get("injection_layer", "instruction"),
                    "attack_type": test_attack_type,
                    "payload_name": t.get("payload_name"),
                    "severity": t.get("severity"),
                    "skill_path": str(skill_path),
                    "test_case_dir": str(
                        test_dir / test_skill_name / test_attack_type / "iteration_0"
                    ),
                    "should_be_blocked": t.get("should_be_blocked", True),
                    "skill_name": test_skill_name,
                }
            )
        return result

    # If no metadata file, scan directory structure
    result = []
    attack_types = [
        "information_disclosure",
        "privilege_escalation",
        "unauthorized_write",
        "backdoor_injection",
    ]

    for skill_dir in test_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        if skill_name and skill_dir.name != skill_name:
            continue

        for at_dir in skill_dir.iterdir():
            if not at_dir.is_dir() or at_dir.name not in attack_types:
                continue
            if attack_type and at_dir.name != attack_type:
                continue

            iteration_0_dir = at_dir / "iteration_0"
            if not iteration_0_dir.exists():
                continue

            skill_path = iteration_0_dir / "SKILL.md"
            if not skill_path.exists():
                continue

            # Try to get layer info from metadata file
            metadata_info = _try_get_metadata_from_dir(at_dir)

            test_id = f"{skill_dir.name}_{at_dir.name}"
            result.append(
                {
                    "test_id": test_id,
                    "name": skill_dir.name,
                    "layer": metadata_info.get("injection_layer", "instruction")
                    if metadata_info
                    else "instruction",
                    "attack_type": at_dir.name,
                    "payload_name": metadata_info.get("payload_name") if metadata_info else None,
                    "severity": metadata_info.get("severity") if metadata_info else None,
                    "skill_path": str(skill_path),
                    "test_case_dir": str(iteration_0_dir),
                    "should_be_blocked": metadata_info.get("should_be_blocked", True)
                    if metadata_info
                    else True,
                    "skill_name": skill_dir.name,
                }
            )

    return result


def get_test_case_metadata(test_case_dir: str | Path) -> dict | None:
    """Get metadata from test case directory

    Supports new_format: {skill_name}/{attack_type}/iteration_0/
    Supports old_format: {skill_name}_{layer}_{attack_type}_{payload_name}/

    Args:
        test_case_dir: Test case directory path

    Returns:
        Metadata dictionary containing information parsed from directory name
    """
    test_case_path = Path(test_case_dir)
    if not test_case_path.exists():
        return None

    # Check if new format path (contains iteration_0)
    if "iteration_0" in test_case_path.parts:
        # New format: Extract skill_name and attack_type from path
        parts = test_case_path.parts
        iteration_idx = parts.index("iteration_0")
        if iteration_idx >= 2:
            attack_type = parts[iteration_idx - 1]
            skill_name = parts[iteration_idx - 2]
            # Get layer and payload_name from metadata file
            metadata_info = _try_get_metadata_from_dir(test_case_path.parent)
            return {
                "test_id": f"{skill_name}_{attack_type}",
                "skill_name": skill_name,
                "layer": metadata_info.get("injection_layer", "instruction")
                if metadata_info
                else "instruction",
                "attack_type": attack_type,
                "payload_name": metadata_info.get("payload_name") if metadata_info else None,
                "format": "new",
            }

    # Parse info from directory name (old format)
    # Format: {skill_name}_{layer}_{attack_type}_{payload_name}
    dir_name = test_case_path.name
    parts = dir_name.split("_")

    if len(parts) < 4:
        return None

    # List of known layer names (descending length, prioritize compound names)
    known_layers = [
        "instruction_resource",
        "description_resource",
        "all",
        "description",
        "instruction",
        "resource",
    ]

    # List of known attack types (unified 4 core attack types)
    known_attack_types = [
        "information_disclosure",
        "privilege_escalation",
        "unauthorized_write",
        "backdoor_injection",
    ]

    # Find layer name (may be compound name)
    layer = None
    layer_end_idx = 1  # Default: parts[1] is layer name

    for known_layer in known_layers:
        layer_parts = known_layer.split("_")
        if len(parts) >= len(layer_parts) + 1:
            candidate = "_".join(parts[1 : 1 + len(layer_parts)])
            if candidate == known_layer:
                layer = known_layer
                layer_end_idx = 1 + len(layer_parts)
                break

    # If no known layer found, use default logic
    if layer is None:
        layer = parts[1] if len(parts) > 1 else None
        layer_end_idx = 2

    # Find attack type (e.g., information_disclosure)
    attack_type = None
    attack_type_end_idx = layer_end_idx

    for known_attack in known_attack_types:
        attack_parts = known_attack.split("_")
        if len(parts) >= layer_end_idx + len(attack_parts):
            candidate = "_".join(parts[layer_end_idx : layer_end_idx + len(attack_parts)])
            if candidate == known_attack:
                attack_type = known_attack
                attack_type_end_idx = layer_end_idx + len(attack_parts)
                break

    # If no known attack type found, use default logic
    if attack_type is None:
        attack_type = parts[layer_end_idx] if len(parts) > layer_end_idx else None
        attack_type_end_idx = layer_end_idx + 1

    # Remaining parts are payload_name
    payload_name = "_".join(parts[attack_type_end_idx:]) if len(parts) > attack_type_end_idx else ""

    return {
        "test_id": dir_name,
        "skill_name": parts[0],
        "layer": layer,
        "attack_type": attack_type,
        "payload_name": payload_name,
        "format": "old",
    }


def _try_get_metadata_from_dir(test_dir: Path) -> dict | None:
    """Get info from metadata file in test directory

    Args:
        test_dir: Test directory path

    Returns:
        Metadata dictionary if found, otherwise None
    """
    # Try to find metadata file
    for metadata_file_name in ["test_metadata.json", "metadata.json", ".test_metadata"]:
        metadata_file = test_dir / metadata_file_name
        if metadata_file.exists():
            try:
                with open(metadata_file) as f:
                    return json.load(f)
            except Exception:
                pass
    return None


InjectionLayer = Literal[
    "description",
    "instruction",
    "resource",
    "description_resource",  # Dual-layer injection
    "instruction_resource",  # Dual-layer injection
    "all",  # Three-layer injection
]


def get_layer_for_test_id(test_id: str, config_path: str | None = None) -> InjectionLayer | None:
    """Parse injection layer from test_id

    Args:
        test_id: Test ID
        config_path: Config file path (optional, for dynamically computing test_dir)

    Returns:
        Injection layer (description/instruction/resource) or None
    """
    from .paths import get_project_paths

    paths = get_project_paths(config_path)
    test_dir = Path(paths["test_dir"])
    metadata_file = test_dir / "test_metadata.json"

    if not metadata_file.exists():
        return None

    with open(metadata_file) as f:
        metadata = json.load(f)

    tests = metadata.get("tests", [])
    matching = [t for t in tests if t.get("test_id") == test_id]

    if matching:
        layer = matching[0].get("injection_layer")
        if layer in (
            "description",
            "instruction",
            "resource",
            "description_resource",
            "instruction_resource",
            "all",
        ):
            return layer

    return None


def generate_test_id_from_parts(
    skill_name: str,
    attack_type: str,
) -> str:
    """Generate test_id from components (new format)

    Args:
        skill_name: Skill name
        attack_type: Attack type

    Returns:
        Formatted test_id: {skill_name}_{attack_type}
    """
    return f"{skill_name}_{attack_type}"


def load_tests_from_config(generation_config: "GenerationConfig") -> list[dict]:
    """Load generated test cases based on GenerationConfig

    New directory structure: attack_type / layer / test_id /

    Use computed_output_dir to get correct path:
    generated_tests/{dataset_name}/{method_dir}/

    Args:
        generation_config: Generation config object

    Returns:
        List of test cases, each element contains:
        - test_id: Test ID
        - layer: Injection layer
        - attack_type: Attack type
        - severity: Severity level
        - skill_path: SKILL.md file path
        - test_case_dir: Test case directory path
        - should_be_blocked: Whether should be blocked
        - dataset: Dataset name
    """
    # Use computed_output_dir to get correct path
    test_dir = generation_config.computed_output_dir

    # Extract dataset from test_dir
    dataset = _extract_dataset_from_path(test_dir)

    # Uniformly use test_metadata.json
    metadata_file = test_dir / "test_metadata.json"

    if not metadata_file.exists():
        return []

    with open(metadata_file, encoding="utf-8") as f:
        metadata = json.load(f)

    # Parse test cases (using new structure)
    result = []
    for test_meta in metadata.get("tests", []):
        attack_type = test_meta.get("attack_type", "information_disclosure")
        layer = test_meta.get("injection_layer", "description")
        test_id = test_meta.get("test_id")
        skill_path = test_dir / attack_type / layer / test_id / "SKILL.md"

        result.append(
            {
                "test_id": test_id,
                "layer": layer,
                "attack_type": attack_type,
                "severity": test_meta.get("severity"),
                "skill_path": str(skill_path),
                "test_case_dir": str(test_dir / attack_type / layer / test_id),
                "should_be_blocked": test_meta.get("should_be_blocked", True),
                "injected_resource_file": test_meta.get("injected_resource_file", ""),
                "injection_points": test_meta.get("injection_points", []),
                "dataset": dataset,
            }
        )

    return result
# mypy: disable-error-code="assignment,no-any-return"
