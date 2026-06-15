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
# Tests for the PR changes: updated submission section + new toolcall configs
# ---------------------------------------------------------------------------

EXTRA_CONFIG_DIR = Path(__file__).parent.parent.parent / "src" / "minisweagent" / "config" / "extra"

ALL_CHANGED_CONFIG_FILES = [
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


class TestAllChangedConfigsParseAndHaveRequiredSections:
    """Verify all 5 changed YAML files load correctly and have required top-level sections."""

    def test_all_extra_configs_parse_as_valid_yaml(self):
        """All changed YAML files must parse without errors."""
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            assert config is not None, f"{config_path.name} returned None after yaml.safe_load"

    def test_all_extra_configs_have_agent_section(self):
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            assert "agent" in config, f"{config_path.name} missing 'agent' section"

    def test_all_extra_configs_have_environment_section(self):
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            assert "environment" in config, f"{config_path.name} missing 'environment' section"

    def test_all_extra_configs_have_model_section(self):
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            assert "model" in config, f"{config_path.name} missing 'model' section"

    def test_all_extra_configs_have_system_template(self):
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            assert config["agent"].get("system_template"), f"{config_path.name} missing agent.system_template"

    def test_all_extra_configs_have_instance_template(self):
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            assert config["agent"].get("instance_template"), f"{config_path.name} missing agent.instance_template"

    def test_all_extra_configs_have_observation_template(self):
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            assert config["model"].get("observation_template"), (
                f"{config_path.name} missing model.observation_template"
            )

    def test_all_extra_configs_have_step_limit(self):
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            assert "step_limit" in config["agent"], f"{config_path.name} missing agent.step_limit"

    def test_all_extra_configs_have_cost_limit(self):
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            assert "cost_limit" in config["agent"], f"{config_path.name} missing agent.cost_limit"


class TestSubmissionSectionChanges:
    """Verify the updated submission section content in all 5 changed configs."""

    def test_submission_section_uses_cat_patch_txt(self):
        """All configs must use 'cat patch.txt' in the submit command (new workflow)."""
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            instance_template = _get_instance_template(config)
            assert "cat patch.txt" in instance_template, (
                f"{config_path.name} missing 'cat patch.txt' in instance_template"
            )

    def test_submission_section_has_complete_submit_command(self):
        """All configs must include the exact submit command."""
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            instance_template = _get_instance_template(config)
            assert "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" in instance_template, (
                f"{config_path.name} missing COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"
            )
            assert "cat patch.txt" in instance_template, (
                f"{config_path.name} missing 'cat patch.txt'"
            )

    def test_submission_section_has_three_step_structure(self):
        """All configs must describe a 3-step submission process."""
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            instance_template = _get_instance_template(config)
            assert "Step 1" in instance_template, f"{config_path.name} missing 'Step 1'"
            assert "Step 2" in instance_template, f"{config_path.name} missing 'Step 2'"
            assert "Step 3" in instance_template, f"{config_path.name} missing 'Step 3'"

    def test_submission_section_has_critical_block(self):
        """All configs must contain a CRITICAL warning block."""
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            instance_template = _get_instance_template(config)
            assert "CRITICAL" in instance_template, (
                f"{config_path.name} missing CRITICAL block in instance_template"
            )

    def test_submission_section_has_important_block(self):
        """All configs must contain an IMPORTANT block describing excluded file types."""
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            instance_template = _get_instance_template(config)
            assert "IMPORTANT" in instance_template, (
                f"{config_path.name} missing IMPORTANT block in instance_template"
            )

    def test_submission_section_mentions_patch_txt_verification(self):
        """All configs must instruct to verify patch.txt before submitting."""
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            instance_template = _get_instance_template(config)
            assert "patch.txt" in instance_template, (
                f"{config_path.name} missing patch.txt reference"
            )
            assert "Verify" in instance_template or "verify" in instance_template, (
                f"{config_path.name} missing verification step"
            )

    def test_submission_section_mentions_separate_commands(self):
        """All configs must indicate that create/verify/submit must be separate steps."""
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            instance_template = _get_instance_template(config)
            # The CRITICAL section should mention that create/view and submit must be separate
            assert "separate" in instance_template.lower() or "SEPARATE" in instance_template, (
                f"{config_path.name} missing guidance about separate commands/tool calls"
            )

    def test_submission_section_does_not_contain_old_git_add_cached_pattern(self):
        """The old submission pattern using 'git add' and 'git diff --cached' must be gone."""
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            instance_template = _get_instance_template(config)
            # Old command was: git add <files> && git diff --cached
            assert "git diff --cached" not in instance_template, (
                f"{config_path.name} still contains old 'git diff --cached' pattern"
            )

    def test_submission_section_does_not_contain_git_add_minus_a(self):
        """The warning 'Do NOT use git add -A' from the old instructions must be gone."""
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            instance_template = _get_instance_template(config)
            # Old text said: "Do NOT use `git add -A` or `git add .`"
            assert "git add -A" not in instance_template, (
                f"{config_path.name} still contains old 'git add -A' warning"
            )

    def test_submission_excluded_files_list_updated(self):
        """The updated IMPORTANT block should describe excluded file types without bullet dashes."""
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            instance_template = _get_instance_template(config)
            # New format omits "- test files" bulleted list style, uses plain paragraphs
            assert "binary or compiled files" in instance_template, (
                f"{config_path.name} missing 'binary or compiled files' in IMPORTANT block"
            )
            assert "test and reproduction files" in instance_template, (
                f"{config_path.name} missing 'test and reproduction files' in IMPORTANT block"
            )


class TestSwebenchToolcallFormatErrorTemplate:
    """Verify the updated format_error_template in swebench_toolcall.yaml."""

    def setup_method(self):
        self.config_path = EXTRA_CONFIG_DIR / "swebench_toolcall.yaml"
        self.config = _load_config(self.config_path)
        self.format_error = self.config["model"]["format_error_template"]

    def test_format_error_template_exists(self):
        assert self.format_error, "swebench_toolcall.yaml missing model.format_error_template"

    def test_format_error_references_bash_tool(self):
        """New format_error_template should reference the 'bash' tool."""
        assert "bash" in self.format_error, (
            "swebench_toolcall.yaml format_error_template should reference 'bash' tool"
        )

    def test_format_error_shows_json_argument_format(self):
        """New format_error_template should show JSON argument format for tool call."""
        assert '{"command":' in self.format_error or '"command"' in self.format_error, (
            "swebench_toolcall.yaml format_error_template should show JSON command format"
        )

    def test_format_error_includes_submit_command_hint(self):
        """format_error_template should hint at the submit command."""
        assert "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" in self.format_error, (
            "swebench_toolcall.yaml format_error_template should include submit command hint"
        )
        assert "cat patch.txt" in self.format_error, (
            "swebench_toolcall.yaml format_error_template should reference cat patch.txt"
        )

    def test_format_error_does_not_contain_old_xml_response_example(self):
        """Old format_error_template had an XML <response_example> block; new one should not."""
        assert "<response_example>" not in self.format_error, (
            "swebench_toolcall.yaml format_error_template should not contain old <response_example> XML block"
        )

    def test_format_error_does_not_reference_git_add(self):
        """Old format_error_template referenced git add; new one should not."""
        assert "git add" not in self.format_error, (
            "swebench_toolcall.yaml format_error_template should not reference git add"
        )


class TestSwebenchToolcallVerboseNewFile:
    """Verify the structure and content of the newly added swebench_toolcall_verbose.yaml."""

    def setup_method(self):
        self.config_path = EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml"
        self.config = _load_config(self.config_path)

    def test_file_is_valid_yaml(self):
        assert self.config is not None

    def test_has_all_required_top_level_sections(self):
        assert "agent" in self.config
        assert "environment" in self.config
        assert "model" in self.config

    def test_system_template_contains_workflow_example(self):
        """Verbose config has a workflow_example in the system template."""
        system_template = self.config["agent"]["system_template"]
        assert "workflow_example" in system_template, (
            "swebench_toolcall_verbose.yaml system_template missing workflow_example"
        )

    def test_system_template_requires_exactly_one_tool_call(self):
        """Verbose system template should require exactly ONE bash tool call."""
        system_template = self.config["agent"]["system_template"]
        assert "ONE command" in system_template or "one command" in system_template.lower(), (
            "swebench_toolcall_verbose.yaml system_template should require ONE command at a time"
        )

    def test_instance_template_has_task_variable(self):
        """instance_template must use the {{task}} Jinja2 variable."""
        instance_template = self.config["agent"]["instance_template"]
        assert "{{task}}" in instance_template, (
            "swebench_toolcall_verbose.yaml instance_template missing {{task}} variable"
        )

    def test_step_limit_is_250(self):
        assert self.config["agent"]["step_limit"] == 250

    def test_cost_limit_is_3(self):
        assert self.config["agent"]["cost_limit"] == 3.0

    def test_environment_cwd_is_testbed(self):
        assert self.config["environment"]["cwd"] == "/testbed"

    def test_environment_class_is_docker(self):
        assert self.config["environment"]["environment_class"] == "docker"

    def test_observation_template_uses_json_format(self):
        """The verbose toolcall config uses JSON observation format (not XML)."""
        obs_template = self.config["model"]["observation_template"]
        assert '"returncode"' in obs_template, (
            "swebench_toolcall_verbose.yaml observation_template should use JSON format"
        )
        # Should NOT use XML-style tags
        assert "<returncode>" not in obs_template, (
            "swebench_toolcall_verbose.yaml observation_template should not use XML tags"
        )

    def test_observation_template_handles_long_output(self):
        """Observation template must truncate output over 10000 chars."""
        obs_template_str = self.config["model"]["observation_template"]
        template = Template(obs_template_str, undefined=StrictUndefined)

        long_output = "Z" * 11000
        output = MockOutput(returncode=0, output=long_output)
        result = template.render(output=output)
        assert "Output too long" in result or "output_head" in result or "output_tail" in result, (
            "swebench_toolcall_verbose.yaml observation_template should truncate long output"
        )

    def test_observation_template_handles_short_output(self):
        """Short output must be rendered in full."""
        obs_template_str = self.config["model"]["observation_template"]
        template = Template(obs_template_str, undefined=StrictUndefined)

        output = MockOutput(returncode=0, output="hello world")
        result = template.render(output=output)
        assert "hello world" in result

    def test_format_error_template_references_bash_tool(self):
        """format_error_template must reference the bash tool."""
        format_error = self.config["model"]["format_error_template"]
        assert "bash" in format_error, (
            "swebench_toolcall_verbose.yaml format_error_template should reference bash tool"
        )

    def test_format_error_template_requires_exactly_one_call(self):
        """format_error_template must state exactly one tool call is required."""
        format_error = self.config["model"]["format_error_template"]
        assert "EXACTLY ONE" in format_error or "exactly one" in format_error.lower(), (
            "swebench_toolcall_verbose.yaml format_error_template should require exactly one tool call"
        )

    def test_format_error_template_includes_submit_command_hint(self):
        """format_error_template must hint at the submit command."""
        format_error = self.config["model"]["format_error_template"]
        assert "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" in format_error
        assert "cat patch.txt" in format_error

    def test_model_name_is_set(self):
        assert self.config["model"].get("model_name"), (
            "swebench_toolcall_verbose.yaml missing model.model_name"
        )

    def test_instance_template_critical_warning_mentions_no_working_after_submit(self):
        """CRITICAL block must state that work cannot continue after submitting."""
        instance_template = self.config["agent"]["instance_template"]
        assert "CANNOT continue working" in instance_template or "cannot continue" in instance_template.lower(), (
            "swebench_toolcall_verbose.yaml CRITICAL block should warn against continuing after submit"
        )

    def test_instance_template_has_correct_workflow_recommendation(self):
        """instance_template should describe the recommended workflow."""
        instance_template = self.config["agent"]["instance_template"]
        assert "Analyze" in instance_template or "analyze" in instance_template.lower(), (
            "swebench_toolcall_verbose.yaml instance_template should describe recommended workflow"
        )

    def test_instance_template_verbose_tool_call_rules(self):
        """Verbose config must explain CRITICAL tool call requirements."""
        instance_template = self.config["agent"]["instance_template"]
        assert "CRITICAL REQUIREMENTS" in instance_template, (
            "swebench_toolcall_verbose.yaml instance_template should contain CRITICAL REQUIREMENTS section"
        )


class TestToolcallConfigsObservationTemplateJsonFormat:
    """Both toolcall configs (toolcall and toolcall_verbose) use JSON observation format."""

    def test_swebench_toolcall_observation_template_json_returncode(self):
        config = _load_config(EXTRA_CONFIG_DIR / "swebench_toolcall.yaml")
        obs_template = config["model"]["observation_template"]
        assert '"returncode"' in obs_template

    def test_swebench_toolcall_verbose_observation_template_json_returncode(self):
        config = _load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
        obs_template = config["model"]["observation_template"]
        assert '"returncode"' in obs_template

    def test_swebench_toolcall_observation_template_no_xml_tags(self):
        config = _load_config(EXTRA_CONFIG_DIR / "swebench_toolcall.yaml")
        obs_template = config["model"]["observation_template"]
        assert "<returncode>" not in obs_template

    def test_swebench_toolcall_verbose_observation_template_no_xml_tags(self):
        config = _load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
        obs_template = config["model"]["observation_template"]
        assert "<returncode>" not in obs_template

    def test_swebench_toolcall_observation_template_renders_short_output(self):
        config = _load_config(EXTRA_CONFIG_DIR / "swebench_toolcall.yaml")
        obs_template_str = config["model"]["observation_template"]
        template = Template(obs_template_str, undefined=StrictUndefined)
        output = MockOutput(returncode=0, output="test output")
        result = template.render(output=output)
        assert "test output" in result
        assert "0" in result

    def test_swebench_toolcall_verbose_observation_template_renders_short_output(self):
        config = _load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
        obs_template_str = config["model"]["observation_template"]
        template = Template(obs_template_str, undefined=StrictUndefined)
        output = MockOutput(returncode=0, output="test output")
        result = template.render(output=output)
        assert "test output" in result
        assert "0" in result


class TestSubmissionRegressionNoBrokenInstruction:
    """Regression tests ensuring the old broken instructions are fully removed."""

    def test_no_config_instructs_git_diff_cached(self):
        """No config should tell the agent to use 'git diff --cached' for submission."""
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            instance_template = _get_instance_template(config)
            assert "git diff --cached" not in instance_template, (
                f"{config_path.name}: old 'git diff --cached' instruction must be removed"
            )

    def test_no_config_instructs_git_add_dot(self):
        """No config should reference 'git add .' for submission."""
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            instance_template = _get_instance_template(config)
            assert "git add ." not in instance_template, (
                f"{config_path.name}: old 'git add .' instruction must be removed"
            )

    def test_submit_command_uses_cat_not_git_diff(self):
        """The actual submit command should use 'cat patch.txt', not 'git diff --cached'."""
        for config_path in ALL_CHANGED_CONFIG_FILES:
            config = _load_config(config_path)
            instance_template = _get_instance_template(config)
            # Find the submit command line
            assert "cat patch.txt" in instance_template, (
                f"{config_path.name}: submit command should use 'cat patch.txt'"
            )

    def test_toolcall_format_error_no_old_mswea_bash_command_block(self):
        """The old toolcall format_error used a mswea_bash_command code block; the new one should not."""
        config = _load_config(EXTRA_CONFIG_DIR / "swebench_toolcall.yaml")
        format_error = config["model"]["format_error_template"]
        # Old format_error had: ```mswea_bash_command\n<action>\n```
        assert "mswea_bash_command" not in format_error, (
            "swebench_toolcall.yaml format_error_template should not reference mswea_bash_command"
        )

    def test_toolcall_format_error_no_old_response_example_tag(self):
        """The old toolcall format_error had a <response_example> XML tag; new one should not."""
        config = _load_config(EXTRA_CONFIG_DIR / "swebench_toolcall.yaml")
        format_error = config["model"]["format_error_template"]
        assert "<response_example>" not in format_error
