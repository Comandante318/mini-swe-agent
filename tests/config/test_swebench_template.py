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


# ---- Tests for PR changes: new patch.txt submission workflow ----

SWEBENCH_CONFIGS_WITH_NEW_SUBMISSION = [
    Path("src/minisweagent/config/extra/swebench.yaml"),
    Path("src/minisweagent/config/extra/swebench_roulette.yaml"),
    Path("src/minisweagent/config/extra/swebench_toolcall.yaml"),
    Path("src/minisweagent/config/extra/swebench_toolcall_verbose.yaml"),
    Path("src/minisweagent/config/extra/swebench_xml.yaml"),
]


def _load_instance_template(config_path: Path) -> str:
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config["agent"]["instance_template"]


def test_submission_uses_patch_txt_workflow():
    """All changed configs must describe the new 3-step patch.txt submission workflow."""
    for config_path in SWEBENCH_CONFIGS_WITH_NEW_SUBMISSION:
        template_str = _load_instance_template(config_path)
        assert "patch.txt" in template_str, f"{config_path} does not reference patch.txt in submission instructions"


def test_submission_exact_command_present():
    """All changed configs must contain the exact final submission command."""
    for config_path in SWEBENCH_CONFIGS_WITH_NEW_SUBMISSION:
        template_str = _load_instance_template(config_path)
        assert "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt" in template_str, (
            f"{config_path} is missing exact submission command "
            "'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt'"
        )


def test_submission_no_longer_uses_git_add_cached():
    """All changed configs must NOT reference the old git-add-based submission."""
    for config_path in SWEBENCH_CONFIGS_WITH_NEW_SUBMISSION:
        template_str = _load_instance_template(config_path)
        assert "git diff --cached" not in template_str, (
            f"{config_path} still contains old 'git diff --cached' submission pattern"
        )
        assert "git add" not in template_str, f"{config_path} still contains old 'git add' submission pattern"


def test_submission_three_step_process_present():
    """All changed configs must describe the three submission steps."""
    for config_path in SWEBENCH_CONFIGS_WITH_NEW_SUBMISSION:
        template_str = _load_instance_template(config_path)
        assert "Step 1" in template_str, f"{config_path} missing 'Step 1' in submission instructions"
        assert "Step 2" in template_str, f"{config_path} missing 'Step 2' in submission instructions"
        assert "Step 3" in template_str, f"{config_path} missing 'Step 3' in submission instructions"


def test_submission_critical_tag_present():
    """All changed configs must include the CRITICAL constraints block."""
    for config_path in SWEBENCH_CONFIGS_WITH_NEW_SUBMISSION:
        template_str = _load_instance_template(config_path)
        assert "CRITICAL" in template_str, f"{config_path} is missing the CRITICAL constraints tag"


def test_submission_critical_separate_commands_requirement():
    """The CRITICAL block must state that creating/viewing the patch and submitting are separate."""
    for config_path in SWEBENCH_CONFIGS_WITH_NEW_SUBMISSION:
        template_str = _load_instance_template(config_path)
        assert "separate" in template_str.lower(), (
            f"{config_path} CRITICAL block does not mention that patch creation and submission "
            "must be separate operations"
        )


def test_submission_important_tag_excludes_test_files():
    """The IMPORTANT block must list test/reproduction files as exclusions."""
    for config_path in SWEBENCH_CONFIGS_WITH_NEW_SUBMISSION:
        template_str = _load_instance_template(config_path)
        # The new IMPORTANT section uses plain text instead of bullet points
        assert "test" in template_str.lower(), (
            f"{config_path} does not mention excluding test files in submission instructions"
        )
        assert "binary" in template_str.lower(), (
            f"{config_path} does not mention excluding binary files in submission instructions"
        )


def test_submission_verify_step_mentions_patch_txt():
    """Step 2 (verify) must instruct inspecting patch.txt."""
    for config_path in SWEBENCH_CONFIGS_WITH_NEW_SUBMISSION:
        template_str = _load_instance_template(config_path)
        assert "Verify" in template_str or "verify" in template_str, f"{config_path} does not have a verification step"
        assert "patch.txt" in template_str, f"{config_path} does not mention patch.txt in the verify step"


# ---- Tests for swebench_toolcall.yaml format_error_template changes ----


def test_toolcall_format_error_references_bash_tool():
    """swebench_toolcall.yaml format_error_template must instruct using the 'bash' tool."""
    config_path = Path("src/minisweagent/config/extra/swebench_toolcall.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    fmt_err = config["model"]["format_error_template"]
    assert "bash" in fmt_err, "swebench_toolcall.yaml format_error_template should instruct using the 'bash' tool"
    assert "Tool call error" in fmt_err, (
        "swebench_toolcall.yaml format_error_template should start with 'Tool call error'"
    )


def test_toolcall_format_error_references_patch_txt_submission():
    """swebench_toolcall.yaml format_error_template must reference the patch.txt submission command."""
    config_path = Path("src/minisweagent/config/extra/swebench_toolcall.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    fmt_err = config["model"]["format_error_template"]
    assert "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt" in fmt_err, (
        "swebench_toolcall.yaml format_error_template must include the patch.txt submission command"
    )


def test_toolcall_format_error_no_longer_references_mswea_bash_command_codeblock():
    """swebench_toolcall.yaml format_error_template must not show the old triple-backtick format."""
    config_path = Path("src/minisweagent/config/extra/swebench_toolcall.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    fmt_err = config["model"]["format_error_template"]
    # Old template used a code-block format; new template uses JSON tool-call syntax
    assert "mswea_bash_command" not in fmt_err, (
        "swebench_toolcall.yaml format_error_template must not reference old mswea_bash_command format"
    )
    assert "response_example" not in fmt_err, (
        "swebench_toolcall.yaml format_error_template must not reference old response_example block"
    )


# ---- Tests for the new swebench_toolcall_verbose.yaml file ----


def test_toolcall_verbose_file_exists():
    """swebench_toolcall_verbose.yaml must exist as a new config file."""
    config_path = Path("src/minisweagent/config/extra/swebench_toolcall_verbose.yaml")
    assert config_path.exists(), "swebench_toolcall_verbose.yaml does not exist"


def test_toolcall_verbose_is_valid_yaml():
    """swebench_toolcall_verbose.yaml must be valid YAML with required top-level keys."""
    config_path = Path("src/minisweagent/config/extra/swebench_toolcall_verbose.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    assert isinstance(config, dict), "swebench_toolcall_verbose.yaml must be a YAML mapping"
    assert "agent" in config, "swebench_toolcall_verbose.yaml must have 'agent' section"
    assert "model" in config, "swebench_toolcall_verbose.yaml must have 'model' section"
    assert "environment" in config, "swebench_toolcall_verbose.yaml must have 'environment' section"


def test_toolcall_verbose_system_template_instructs_tool_call():
    """swebench_toolcall_verbose.yaml system_template must reference the bash tool call."""
    config_path = Path("src/minisweagent/config/extra/swebench_toolcall_verbose.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    system_template = config["agent"]["system_template"]
    assert "bash" in system_template.lower(), "swebench_toolcall_verbose.yaml system_template must reference bash tool"
    assert "tool" in system_template.lower(), "swebench_toolcall_verbose.yaml system_template must reference tool calls"


def test_toolcall_verbose_format_error_references_bash_tool():
    """swebench_toolcall_verbose.yaml format_error_template must instruct using the 'bash' tool."""
    config_path = Path("src/minisweagent/config/extra/swebench_toolcall_verbose.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    fmt_err = config["model"]["format_error_template"]
    assert "bash" in fmt_err, (
        "swebench_toolcall_verbose.yaml format_error_template should instruct using the 'bash' tool"
    )
    assert "Tool call error" in fmt_err, (
        "swebench_toolcall_verbose.yaml format_error_template should start with 'Tool call error'"
    )


def test_toolcall_verbose_format_error_references_patch_txt_submission():
    """swebench_toolcall_verbose.yaml format_error_template must reference patch.txt submission."""
    config_path = Path("src/minisweagent/config/extra/swebench_toolcall_verbose.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    fmt_err = config["model"]["format_error_template"]
    assert "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt" in fmt_err, (
        "swebench_toolcall_verbose.yaml format_error_template must include patch.txt submission command"
    )


def test_toolcall_verbose_format_error_requires_single_tool_call():
    """swebench_toolcall_verbose.yaml format_error_template must emphasize exactly one tool call."""
    config_path = Path("src/minisweagent/config/extra/swebench_toolcall_verbose.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    fmt_err = config["model"]["format_error_template"]
    assert "ONE" in fmt_err or "one" in fmt_err.lower(), (
        "swebench_toolcall_verbose.yaml format_error_template must require exactly ONE tool call"
    )


def test_toolcall_verbose_step_limits_and_cost():
    """swebench_toolcall_verbose.yaml must have step_limit and cost_limit defined."""
    config_path = Path("src/minisweagent/config/extra/swebench_toolcall_verbose.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    agent = config["agent"]
    assert "step_limit" in agent, "swebench_toolcall_verbose.yaml must have agent.step_limit"
    assert "cost_limit" in agent, "swebench_toolcall_verbose.yaml must have agent.cost_limit"


def test_toolcall_verbose_observation_template_handles_long_output():
    """swebench_toolcall_verbose.yaml observation_template must handle long output with truncation."""
    config_path = Path("src/minisweagent/config/extra/swebench_toolcall_verbose.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    obs_template_str = config["model"]["observation_template"]
    template = Template(obs_template_str, undefined=StrictUndefined)

    long_output = "A" * 8000 + "Z" * 3000  # 11000 characters
    output = MockOutput(returncode=0, output=long_output)
    result = template.render(output=output)

    # JSON format uses output_head/output_tail keys
    assert "output_head" in result, "Long output should be truncated with output_head"
    assert "output_tail" in result, "Long output should be truncated with output_tail"
    assert "Output too long" in result or "elided_chars" in result


def test_toolcall_verbose_observation_template_handles_short_output():
    """swebench_toolcall_verbose.yaml observation_template must render short output in full."""
    config_path = Path("src/minisweagent/config/extra/swebench_toolcall_verbose.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    obs_template_str = config["model"]["observation_template"]
    template = Template(obs_template_str, undefined=StrictUndefined)

    output = MockOutput(returncode=0, output="hello world")
    result = template.render(output=output)

    assert "hello world" in result
    assert "output_head" not in result


def test_toolcall_verbose_observation_template_handles_exception_info():
    """swebench_toolcall_verbose.yaml observation_template must include exception_info when present."""
    config_path = Path("src/minisweagent/config/extra/swebench_toolcall_verbose.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    obs_template_str = config["model"]["observation_template"]
    template = Template(obs_template_str, undefined=StrictUndefined)

    output = MockOutput(returncode=1, output="crashed", exception_info="Segmentation fault")
    result = template.render(output=output)

    assert "Segmentation fault" in result, (
        "swebench_toolcall_verbose.yaml observation_template must include exception_info"
    )


def test_toolcall_verbose_environment_is_docker():
    """swebench_toolcall_verbose.yaml must set environment_class to docker."""
    config_path = Path("src/minisweagent/config/extra/swebench_toolcall_verbose.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    assert config["environment"]["environment_class"] == "docker", (
        "swebench_toolcall_verbose.yaml must use docker environment"
    )
