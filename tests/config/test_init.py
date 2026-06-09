"""Tests for minisweagent.config.__init__."""

import pytest

from minisweagent.config import _key_value_spec_to_nested_dict, get_config_from_spec, get_config_path


class TestKeyValueSpecToNestedDict:
    """Tests for _key_value_spec_to_nested_dict function."""

    def test_simple_string_value(self):
        assert _key_value_spec_to_nested_dict("key=value") == {"key": "value"}

    def test_simple_string_with_quotes(self):
        assert _key_value_spec_to_nested_dict('key="value"') == {"key": "value"}

    def test_nested_single_level(self):
        assert _key_value_spec_to_nested_dict("agent.mode=yolo") == {"agent": {"mode": "yolo"}}

    def test_nested_multiple_levels(self):
        assert _key_value_spec_to_nested_dict("a.b.c=value") == {"a": {"b": {"c": "value"}}}

    def test_deeply_nested(self):
        assert _key_value_spec_to_nested_dict("a.b.c.d.e=value") == {"a": {"b": {"c": {"d": {"e": "value"}}}}}

    def test_integer_value(self):
        assert _key_value_spec_to_nested_dict("count=42") == {"count": 42}

    def test_negative_integer(self):
        assert _key_value_spec_to_nested_dict("value=-10") == {"value": -10}

    def test_float_value(self):
        assert _key_value_spec_to_nested_dict("temperature=0.7") == {"temperature": 0.7}

    def test_negative_float(self):
        assert _key_value_spec_to_nested_dict("value=-3.14") == {"value": -3.14}

    def test_boolean_true(self):
        assert _key_value_spec_to_nested_dict("enabled=true") == {"enabled": True}

    def test_boolean_false(self):
        assert _key_value_spec_to_nested_dict("enabled=false") == {"enabled": False}

    def test_null_value(self):
        assert _key_value_spec_to_nested_dict("value=null") == {"value": None}

    def test_list_value(self):
        assert _key_value_spec_to_nested_dict('tags=["a","b","c"]') == {"tags": ["a", "b", "c"]}

    def test_list_of_numbers(self):
        assert _key_value_spec_to_nested_dict("numbers=[1,2,3]") == {"numbers": [1, 2, 3]}

    def test_dict_value(self):
        assert _key_value_spec_to_nested_dict('config={"key":"value"}') == {"config": {"key": "value"}}

    def test_nested_with_integer(self):
        assert _key_value_spec_to_nested_dict("model.max_tokens=1000") == {"model": {"max_tokens": 1000}}

    def test_nested_with_float(self):
        assert _key_value_spec_to_nested_dict("model.temperature=0.5") == {"model": {"temperature": 0.5}}

    def test_nested_with_boolean(self):
        assert _key_value_spec_to_nested_dict("agent.verbose=true") == {"agent": {"verbose": True}}

    def test_model_name_example(self):
        result = _key_value_spec_to_nested_dict("model.model_name=anthropic/claude-sonnet-4-5-20250929")
        assert result == {"model": {"model_name": "anthropic/claude-sonnet-4-5-20250929"}}

    def test_empty_string_value(self):
        assert _key_value_spec_to_nested_dict('key=""') == {"key": ""}

    def test_value_with_spaces(self):
        assert _key_value_spec_to_nested_dict('message="hello world"') == {"message": "hello world"}

    def test_zero_integer(self):
        assert _key_value_spec_to_nested_dict("value=0") == {"value": 0}

    def test_zero_float(self):
        assert _key_value_spec_to_nested_dict("value=0.0") == {"value": 0.0}


class TestGetConfigFromSpec:
    """Tests for get_config_from_spec function."""

    def test_uses_key_value_spec_for_equals_sign(self):
        result = get_config_from_spec("agent.mode=yolo")
        assert result == {"agent": {"mode": "yolo"}}

    def test_uses_key_value_spec_with_number(self):
        result = get_config_from_spec("model.max_tokens=500")
        assert result == {"model": {"max_tokens": 500}}

    def test_loads_yaml_file_when_no_equals(self, tmp_path):
        config_file = tmp_path / "test.yaml"
        config_file.write_text("key: value\nnumber: 42")
        result = get_config_from_spec(config_file)
        assert result == {"key": "value", "number": 42}


class TestGetConfigPath:
    """Tests for get_config_path function.

    The docs/advanced/yaml_configuration.md change references the swebench_xml config
    via ``--8<-- "src/minisweagent/config/extra/swebench_xml.yaml"`` — i.e. the file
    lives in the ``extra/`` subdirectory.  get_config_path must resolve the short-name
    ``"swebench_xml"`` (no directory, no extension) to that file.
    """

    def test_swebench_xml_resolves_from_extra_subdir(self):
        """swebench_xml config is found in the builtin extra/ directory."""
        path = get_config_path("swebench_xml")
        assert path.exists(), f"swebench_xml.yaml not found at {path}"
        assert path.name == "swebench_xml.yaml"
        assert "extra" in path.parts, f"Expected path to be under extra/, got {path}"

    def test_swebench_xml_path_with_yaml_suffix(self):
        """get_config_path appends .yaml automatically if not provided."""
        path_no_suffix = get_config_path("swebench_xml")
        path_with_suffix = get_config_path("swebench_xml.yaml")
        assert path_no_suffix == path_with_suffix

    def test_extra_configs_are_loadable(self):
        """All extra/ configs referenced in docs can be loaded via their short names."""
        for name in ("swebench_xml",):
            path = get_config_path(name)
            result = get_config_from_spec(path)
            assert isinstance(result, dict), f"Config '{name}' did not load as a dict"

    def test_nonexistent_config_raises_file_not_found(self):
        """get_config_path raises FileNotFoundError for unknown config names."""
        with pytest.raises(FileNotFoundError):
            get_config_path("this_config_does_not_exist_ever")

    def test_builtin_configs_are_reachable_by_short_name(self):
        """Core builtin configs (mini, default) resolve without specifying a full path."""
        for name in ("mini", "default"):
            path = get_config_path(name)
            assert path.exists(), f"Builtin config '{name}' not found at {path}"
