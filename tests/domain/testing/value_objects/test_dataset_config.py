"""Tests for DatasetConfig path detection and instruction override."""

from pathlib import Path

from src.domain.testing.value_objects.execution_config import DatasetConfig


class TestDatasetConfigPathDetection:
    """Test DatasetConfig.from_dict path vs name detection."""

    def test_plain_name_unchanged(self) -> None:
        ds = DatasetConfig.from_dict("skills_sample")
        assert ds.name == "skills_sample"
        assert ds.base_dir == Path("data/skills_sample")
        assert ds.instruction_base_dir is None
        assert ds.resolved_instruction_base_dir == Path("data/instruction/skills_sample")

    def test_relative_path_detected(self) -> None:
        ds = DatasetConfig.from_dict("data/skill_inject")
        assert ds.name == "skill_inject"
        assert ds.base_dir == Path("data/skill_inject")

    def test_absolute_path_detected(self) -> None:
        ds = DatasetConfig.from_dict("/absolute/path/to/my/skills")
        assert ds.name == "skills"
        assert ds.base_dir == Path("/absolute/path/to/my/skills")

    def test_dot_relative_path_detected(self) -> None:
        ds = DatasetConfig.from_dict("./local/skills")
        assert ds.name == "skills"
        assert ds.base_dir == Path("./local/skills")

    def test_dict_with_base_dir_derives_name(self) -> None:
        ds = DatasetConfig.from_dict({"base_dir": "data/custom_set"})
        assert ds.name == "custom_set"
        assert ds.base_dir == Path("data/custom_set")

    def test_dict_with_explicit_name_preserved(self) -> None:
        ds = DatasetConfig.from_dict({"name": "my_name", "base_dir": "data/custom_set"})
        assert ds.name == "my_name"
        assert ds.base_dir == Path("data/custom_set")

    def test_dict_without_name_or_base_dir_uses_defaults(self) -> None:
        ds = DatasetConfig.from_dict({})
        assert ds.name == "skills_from_skill0"
        assert ds.base_dir == Path("data/skills_from_skill0")

    def test_dict_with_instruction_base_dir(self) -> None:
        ds = DatasetConfig.from_dict(
            {"name": "skills_sample", "instruction_base_dir": "data/instruction/custom"}
        )
        assert ds.instruction_base_dir == Path("data/instruction/custom")
        assert ds.resolved_instruction_base_dir == Path("data/instruction/custom")

    def test_datasetconfig_passthrough(self) -> None:
        original = DatasetConfig(name="test", base_dir=Path("data/test"))
        assert DatasetConfig.from_dict(original) is original

    def test_none_returns_default(self) -> None:
        ds = DatasetConfig.from_dict(None)
        assert ds.name == "skills_from_skill0"

    def test_backslash_path_detected(self) -> None:
        ds = DatasetConfig.from_dict("C:\\Users\\data\\skills")
        assert ds.name == "skills"
        assert ds.base_dir == Path("C:\\Users\\data\\skills")


class TestDatasetConfigInstructionOverride:
    """Test instruction_base_dir behavior after construction."""

    def test_resolved_instruction_uses_explicit_when_set(self) -> None:
        ds = DatasetConfig(
            name="test",
            base_dir=Path("data/test"),
            instruction_base_dir=Path("custom/instructions"),
        )
        assert ds.resolved_instruction_base_dir == Path("custom/instructions")

    def test_resolved_instruction_derives_from_name(self) -> None:
        ds = DatasetConfig(name="my_dataset", base_dir=Path("data/my_dataset"))
        assert ds.resolved_instruction_base_dir == Path("data/instruction/my_dataset")
