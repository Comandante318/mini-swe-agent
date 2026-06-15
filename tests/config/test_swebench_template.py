from dataclasses import dataclass
from pathlib import Path

import yaml
from jinja2 import StrictUndefined, Template

from minisweagent.agents.default import AgentConfig


@dataclass
class MockOutput:
    """Mock output object for testing the template"""

    returncode: int
    output: str
    exception_info: str = ""


def test_observation_template_short_output():
    """Test that short output (< 10000 chars) is displayed in full"""
    # Load the swebench config
    config_path = Path(__file__).parent.parent.parent / "src" / "minisweagent" / "config" / "extra" / "swebench.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Extract the template (now in model section)
    template_str = config["model"]["observation_template"]
    template = Template(template_str, undefined=StrictUndefined)

    # Create mock output with short content
    output = MockOutput(returncode=0, output="Success! Operation completed.\nWarning: minor issue")

    # Render the template
    result = template.render(output=output)

    # Verify the result contains all parts and no truncation
    assert "<returncode>" in result
    assert "0" in result
    assert "<output>" in result
    assert "Success! Operation completed." in result
    assert "Warning: minor issue" in result

    # Should not contain truncation elements for short output
    assert "<output_head>" not in result
    assert "<elided_chars>" not in result
    assert "<output_tail>" not in result
    assert "<warning>" not in result


def test_observation_template_long_output():
    """Test that long output (> 10000 chars) is truncated with head/tail format"""
    # Load the swebench config
    config_path = Path(__file__).parent.parent.parent / "src" / "minisweagent" / "config" / "extra" / "swebench.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Extract the template (now in model section)
    template_str = config["model"]["observation_template"]
    template = Template(template_str, undefined=StrictUndefined)

    # Create mock output with long content
    long_output = "A" * 8000 + "B" * 3000  # 11000 characters total
    # Total will be > 10000 chars

    output = MockOutput(returncode=1, output=long_output)

    # Render the template
    result = template.render(output=output)

    # Should contain truncation elements for long output
    assert "<warning>" in result
    assert "The output of your last command was too long" in result
    assert "<output_head>" in result
    assert "<elided_chars>" in result
    assert "characters elided" in result
    assert "<output_tail>" in result

    # Should still contain the basic structure
    assert "<returncode>" in result
    assert "1" in result

    # Verify the head contains first part of output
    head_start = result.find("<output_head>")
    head_end = result.find("</output_head>")
    head_content = result[head_start:head_end]
    assert "AAAA" in head_content  # Should contain start of output

    # Verify the tail contains last part of output
    tail_start = result.find("<output_tail>")
    tail_end = result.find("</output_tail>")
    tail_content = result[tail_start:tail_end]
    assert "BBBB" in tail_content  # Should contain end of output


def test_observation_template_edge_case_exactly_10000_chars():
    """Test the boundary case where output is around 10000 characters"""
    # Load the swebench config
    config_path = Path(__file__).parent.parent.parent / "src" / "minisweagent" / "config" / "extra" / "swebench.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Extract the template (now in model section)
    template_str = config["model"]["observation_template"]
    template = Template(template_str, undefined=StrictUndefined)

    # Use a large amount of data that will definitely exceed 10000 chars when rendered
    output = MockOutput(returncode=0, output="X" * 10000)

    # Render the template
    result = template.render(output=output)

    # Should use truncated format for large output
    assert "<output_head>" in result
    assert "<elided_chars>" in result
    assert "<output_tail>" in result
    assert "<warning>" in result
    # The X's should still be present in head or tail
    assert "XXXX" in result


def test_observation_template_just_under_10000_chars():
    """Test that smaller output shows full output without truncation"""
    # Load the swebench config
    config_path = Path(__file__).parent.parent.parent / "src" / "minisweagent" / "config" / "extra" / "swebench.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Extract the template (now in model section)
    template_str = config["model"]["observation_template"]
    template = Template(template_str, undefined=StrictUndefined)

    # Use a reasonably sized output that should be well under 10000 chars when rendered
    output = MockOutput(returncode=0, output="Y" * 8000)

    # Render the template
    result = template.render(output=output)

    # Should show full output without truncation
    assert "<output_head>" not in result
    assert "<elided_chars>" not in result
    assert "<output_tail>" not in result
    assert "<warning>" not in result
    assert "Y" * 8000 in result


def test_agent_config_requires_templates():
    """Test that AgentConfig now requires all template fields (no defaults in code)"""
    import pytest
    from pydantic import ValidationError

    # AgentConfig should require all template fields now (Pydantic raises ValidationError)
    with pytest.raises(ValidationError, match="validation error"):
        AgentConfig()


def test_exception_info_template():
    """Test that config files have observation_template with exception handling"""
    from pathlib import Path

    import yaml

    config_files = [
        Path("src/minisweagent/config/default.yaml"),
        Path("src/minisweagent/config/mini.yaml"),
        Path("src/minisweagent/config/github_issue.yaml"),
        Path("src/minisweagent/config/extra/swebench.yaml"),
        Path("src/minisweagent/config/extra/swebench_xml.yaml"),
        Path("src/minisweagent/config/extra/swebench_roulette.yaml"),
    ]

    for config_file in config_files:
        with open(config_file) as f:
            config = yaml.safe_load(f)

        action_template = config.get("model", {}).get("observation_template")
        assert action_template is not None, f"{config_file} missing observation_template in model section"

        # Verify it handles exception_info
        template = Template(action_template, undefined=StrictUndefined)

        # Test with exception
        output_with_exception = MockOutput(
            returncode=-1, output="partial output", exception_info="Command timed out after 30s"
        )
        result = template.render(output=output_with_exception)
        assert "Command timed out after 30s" in result, f"{config_file} doesn't render exception_info"

        # Test without exception (should not error)
        output_normal = MockOutput(returncode=0, output="success", exception_info="")
        result = template.render(output=output_normal)
        assert "success" in result


# ---------------------------------------------------------------------------
# Tests for the PR changes: new submission workflow across all modified configs
# ---------------------------------------------------------------------------

EXTRA_CONFIG_DIR = Path(__file__).parent.parent.parent / "src" / "minisweagent" / "config" / "extra"

ALL_MODIFIED_CONFIGS = [
    EXTRA_CONFIG_DIR / "swebench.yaml",
    EXTRA_CONFIG_DIR / "swebench_roulette.yaml",
    EXTRA_CONFIG_DIR / "swebench_toolcall.yaml",
    EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml",
    EXTRA_CONFIG_DIR / "swebench_xml.yaml",
]


def _load_config(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _get_instance_template(config: dict) -> str:
    return config["agent"]["instance_template"]


def test_all_modified_configs_are_valid_yaml():
    """All five modified config files must load as valid YAML without errors."""
    for config_path in ALL_MODIFIED_CONFIGS:
        config = _load_config(config_path)
        assert isinstance(config, dict), f"{config_path.name} did not load as a dict"


def test_all_modified_configs_have_required_top_level_keys():
    """All modified configs must contain agent, environment, and model sections."""
    for config_path in ALL_MODIFIED_CONFIGS:
        config = _load_config(config_path)
        for key in ("agent", "environment", "model"):
            assert key in config, f"{config_path.name} is missing top-level key '{key}'"


def test_submission_section_references_patch_txt():
    """All modified configs must reference patch.txt in the submission instructions."""
    for config_path in ALL_MODIFIED_CONFIGS:
        config = _load_config(config_path)
        instance_template = _get_instance_template(config)
        assert "patch.txt" in instance_template, (
            f"{config_path.name}: submission section does not reference patch.txt"
        )


def test_submission_section_has_three_step_process():
    """All modified configs must include the three-step submission process."""
    for config_path in ALL_MODIFIED_CONFIGS:
        config = _load_config(config_path)
        instance_template = _get_instance_template(config)
        assert "Step 1" in instance_template, f"{config_path.name}: missing 'Step 1' in submission"
        assert "Step 2" in instance_template, f"{config_path.name}: missing 'Step 2' in submission"
        assert "Step 3" in instance_template, f"{config_path.name}: missing 'Step 3' in submission"


def test_submission_command_uses_cat_patch_txt():
    """All modified configs must use the new submit command: cat patch.txt."""
    expected_fragment = "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt"
    for config_path in ALL_MODIFIED_CONFIGS:
        config = _load_config(config_path)
        instance_template = _get_instance_template(config)
        assert expected_fragment in instance_template, (
            f"{config_path.name}: expected submit command '{expected_fragment}' not found"
        )


def test_submission_does_not_use_old_git_add_command():
    """None of the modified configs should use the old git-add-based submit flow."""
    for config_path in ALL_MODIFIED_CONFIGS:
        config = _load_config(config_path)
        instance_template = _get_instance_template(config)
        # The old command used 'git add <files> && git diff --cached'
        assert "git diff --cached" not in instance_template, (
            f"{config_path.name}: still contains old 'git diff --cached' submit command"
        )
        # Ensure there is no 'git add <file1>' placeholder pattern
        assert "git add <file1>" not in instance_template, (
            f"{config_path.name}: still contains old placeholder 'git add <file1>'"
        )


def test_submission_has_important_and_critical_uppercase_tags():
    """All modified configs must use uppercase <IMPORTANT> and <CRITICAL> tags."""
    for config_path in ALL_MODIFIED_CONFIGS:
        config = _load_config(config_path)
        instance_template = _get_instance_template(config)
        assert "<IMPORTANT>" in instance_template, (
            f"{config_path.name}: missing uppercase <IMPORTANT> tag in submission"
        )
        assert "</IMPORTANT>" in instance_template, (
            f"{config_path.name}: missing closing </IMPORTANT> tag in submission"
        )
        assert "<CRITICAL>" in instance_template, (
            f"{config_path.name}: missing <CRITICAL> tag in submission"
        )
        assert "</CRITICAL>" in instance_template, (
            f"{config_path.name}: missing closing </CRITICAL> tag in submission"
        )


def test_submission_important_lists_excluded_file_types():
    """The <IMPORTANT> block must list file categories excluded from the patch."""
    expected_phrases = [
        "test and reproduction files",
        "binary or compiled files",
    ]
    for config_path in ALL_MODIFIED_CONFIGS:
        config = _load_config(config_path)
        instance_template = _get_instance_template(config)
        for phrase in expected_phrases:
            assert phrase in instance_template, (
                f"{config_path.name}: missing excluded-file phrase '{phrase}' in <IMPORTANT> block"
            )


def test_submission_critical_warns_against_separate_commands():
    """The <CRITICAL> block must warn that patch creation and submission must be separate."""
    for config_path in ALL_MODIFIED_CONFIGS:
        config = _load_config(config_path)
        instance_template = _get_instance_template(config)
        assert "MUST be separate" in instance_template, (
            f"{config_path.name}: <CRITICAL> block missing 'MUST be separate' warning"
        )
        assert "You CANNOT continue working" in instance_template, (
            f"{config_path.name}: <CRITICAL> block missing post-submit warning"
        )


def test_toolcall_format_error_template_references_bash_tool():
    """swebench_toolcall.yaml format_error_template must reference the 'bash' tool."""
    config = _load_config(EXTRA_CONFIG_DIR / "swebench_toolcall.yaml")
    fmt_error = config["model"]["format_error_template"]
    assert "bash" in fmt_error, "format_error_template must reference the 'bash' tool"
    assert "Tool call error" in fmt_error, "format_error_template must start with 'Tool call error'"


def test_toolcall_format_error_template_contains_submit_command():
    """swebench_toolcall.yaml format_error_template must include the submit command."""
    config = _load_config(EXTRA_CONFIG_DIR / "swebench_toolcall.yaml")
    fmt_error = config["model"]["format_error_template"]
    assert "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt" in fmt_error


def test_toolcall_format_error_template_no_longer_references_mswea_code_blocks():
    """swebench_toolcall.yaml format_error_template must not use the old mswea_bash_command format."""
    config = _load_config(EXTRA_CONFIG_DIR / "swebench_toolcall.yaml")
    fmt_error = config["model"]["format_error_template"]
    assert "mswea_bash_command" not in fmt_error, (
        "format_error_template should not reference old mswea_bash_command code-block format"
    )
    assert "triple backticks" not in fmt_error, (
        "format_error_template should not reference old triple-backtick instructions"
    )


def test_toolcall_verbose_has_all_required_agent_keys():
    """swebench_toolcall_verbose.yaml must have system_template, instance_template, step_limit, cost_limit."""
    config = _load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
    agent = config["agent"]
    for key in ("system_template", "instance_template", "step_limit", "cost_limit"):
        assert key in agent, f"swebench_toolcall_verbose.yaml agent section missing '{key}'"


def test_toolcall_verbose_system_template_mentions_one_tool_call():
    """swebench_toolcall_verbose.yaml system_template must instruct the agent to make exactly one tool call."""
    config = _load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
    system_template = config["agent"]["system_template"]
    assert "ONE command" in system_template or "one" in system_template.lower(), (
        "system_template must instruct agent to use exactly one command/tool call"
    )
    assert "bash" in system_template.lower(), (
        "system_template must reference the bash tool"
    )


def test_toolcall_verbose_format_error_template_references_bash_tool():
    """swebench_toolcall_verbose.yaml format_error_template must reference the 'bash' tool."""
    config = _load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
    fmt_error = config["model"]["format_error_template"]
    assert "bash" in fmt_error
    assert "Tool call error" in fmt_error


def test_toolcall_verbose_format_error_template_contains_submit_command():
    """swebench_toolcall_verbose.yaml format_error_template must include the submit command."""
    config = _load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
    fmt_error = config["model"]["format_error_template"]
    assert "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt" in fmt_error


def test_toolcall_verbose_observation_template_json_format():
    """swebench_toolcall_verbose.yaml observation_template must produce valid JSON for short output."""
    import json

    config = _load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
    template_str = config["model"]["observation_template"]
    template = Template(template_str, undefined=StrictUndefined)

    output = MockOutput(returncode=0, output="hello world", exception_info="")
    result = template.render(output=output)
    parsed = json.loads(result)
    assert parsed["returncode"] == 0
    assert parsed["output"] == "hello world"
    assert "exception_info" not in parsed


def test_toolcall_verbose_observation_template_truncates_long_output():
    """swebench_toolcall_verbose.yaml observation_template must truncate output > 10000 chars."""
    import json

    config = _load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
    template_str = config["model"]["observation_template"]
    template = Template(template_str, undefined=StrictUndefined)

    long_output = "A" * 6000 + "B" * 5000  # 11000 chars
    output = MockOutput(returncode=1, output=long_output, exception_info="")
    result = template.render(output=output)
    parsed = json.loads(result)
    assert "output_head" in parsed
    assert "output_tail" in parsed
    assert "elided_chars" in parsed
    assert parsed["elided_chars"] == 1000
    assert "warning" in parsed


def test_toolcall_configs_have_exception_info_in_observation_template():
    """swebench_toolcall.yaml and swebench_toolcall_verbose.yaml observation_templates handle exception_info."""
    import json

    toolcall_configs = [
        EXTRA_CONFIG_DIR / "swebench_toolcall.yaml",
        EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml",
    ]
    for config_path in toolcall_configs:
        config = _load_config(config_path)
        template_str = config["model"]["observation_template"]
        template = Template(template_str, undefined=StrictUndefined)

        # With exception_info
        output = MockOutput(returncode=-1, output="partial", exception_info="Timed out after 60s")
        result = template.render(output=output)
        parsed = json.loads(result)
        assert "exception_info" in parsed, f"{config_path.name}: exception_info missing from rendered output"
        assert "Timed out after 60s" in parsed["exception_info"]

        # Without exception_info (should not include the key)
        output_ok = MockOutput(returncode=0, output="ok", exception_info="")
        result_ok = template.render(output=output_ok)
        parsed_ok = json.loads(result_ok)
        assert "exception_info" not in parsed_ok, (
            f"{config_path.name}: exception_info should be absent when empty"
        )


def test_all_modified_configs_step_and_cost_limits():
    """All modified configs must have the same step_limit=250 and cost_limit=3.0."""
    for config_path in ALL_MODIFIED_CONFIGS:
        config = _load_config(config_path)
        agent = config["agent"]
        assert agent.get("step_limit") == 250, f"{config_path.name}: unexpected step_limit"
        assert agent.get("cost_limit") == 3.0, f"{config_path.name}: unexpected cost_limit"


def test_all_modified_configs_environment_cwd():
    """All modified configs must set the working directory to /testbed."""
    for config_path in ALL_MODIFIED_CONFIGS:
        config = _load_config(config_path)
        assert config["environment"]["cwd"] == "/testbed", (
            f"{config_path.name}: environment.cwd is not '/testbed'"
        )


def test_submission_verify_step_mentions_patch_txt_inspection():
    """Step 2 (verify) must instruct the agent to inspect patch.txt."""
    for config_path in ALL_MODIFIED_CONFIGS:
        config = _load_config(config_path)
        instance_template = _get_instance_template(config)
        # Step 2 should mention verifying/inspecting patch.txt
        assert "patch.txt" in instance_template
        # Verify the step is present
        verify_step_present = "Step 2" in instance_template and "Verify" in instance_template
        assert verify_step_present, (
            f"{config_path.name}: Step 2 verification step is missing or incomplete"
        )
