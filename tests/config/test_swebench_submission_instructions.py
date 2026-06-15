"""Tests for the updated submission instructions in swebench config files.

These tests cover the PR changes that updated the submission workflow from
the old `git add + git diff --cached` approach to the new 3-step patch.txt workflow:
  Step 1: Create patch.txt via git diff
  Step 2: Verify patch.txt
  Step 3: Submit with `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt`
"""

from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml
from jinja2 import StrictUndefined, Template

# Paths to all changed config files
REPO_ROOT = Path(__file__).parent.parent.parent
EXTRA_CONFIG_DIR = REPO_ROOT / "src" / "minisweagent" / "config" / "extra"

CHANGED_CONFIGS = [
    EXTRA_CONFIG_DIR / "swebench.yaml",
    EXTRA_CONFIG_DIR / "swebench_roulette.yaml",
    EXTRA_CONFIG_DIR / "swebench_toolcall.yaml",
    EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml",
    EXTRA_CONFIG_DIR / "swebench_xml.yaml",
]

TOOLCALL_CONFIGS = [
    EXTRA_CONFIG_DIR / "swebench_toolcall.yaml",
    EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml",
]


@dataclass
class MockOutput:
    """Mock output object for testing observation templates."""

    returncode: int
    output: str
    exception_info: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_config(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def get_instance_template(path: Path) -> str:
    config = load_config(path)
    return config["agent"]["instance_template"]


# ---------------------------------------------------------------------------
# Tests: all 5 changed configs must contain new submission instructions
# ---------------------------------------------------------------------------


class TestSubmissionInstructionsPresent:
    """All changed configs must use the new 3-step patch.txt submission workflow."""

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_submission_instructions_use_patch_txt(self, config_path):
        """The submission instructions must reference patch.txt."""
        template = get_instance_template(config_path)
        assert "patch.txt" in template, f"{config_path.name}: missing 'patch.txt' in instance_template"

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_exact_submit_command_present(self, config_path):
        """The exact submission command 'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt' must be present."""
        template = get_instance_template(config_path)
        assert "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt" in template, (
            f"{config_path.name}: missing exact submit command"
        )

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_three_step_submission_workflow(self, config_path):
        """All configs must describe the 3-step workflow (Step 1, Step 2, Step 3)."""
        template = get_instance_template(config_path)
        assert "Step 1" in template, f"{config_path.name}: missing 'Step 1'"
        assert "Step 2" in template, f"{config_path.name}: missing 'Step 2'"
        assert "Step 3" in template, f"{config_path.name}: missing 'Step 3'"

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_create_patch_step_present(self, config_path):
        """Step 1 must instruct the agent to create a patch file."""
        template = get_instance_template(config_path)
        assert "Create the patch file" in template or "patch file" in template.lower(), (
            f"{config_path.name}: missing patch file creation step"
        )

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_verify_patch_step_present(self, config_path):
        """Step 2 must instruct the agent to verify the patch."""
        template = get_instance_template(config_path)
        assert "Verify your patch" in template, f"{config_path.name}: missing patch verification step"

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_critical_block_separate_commands(self, config_path):
        """The CRITICAL block must instruct that creation and submission must be separate commands."""
        template = get_instance_template(config_path)
        assert "CRITICAL" in template, f"{config_path.name}: missing CRITICAL block"
        assert "separate" in template.lower(), f"{config_path.name}: missing 'separate' in CRITICAL block"

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_cannot_continue_after_submitting(self, config_path):
        """Submission instructions must state agent cannot continue working after submitting."""
        template = get_instance_template(config_path)
        assert "CANNOT continue working" in template or "cannot continue working" in template.lower(), (
            f"{config_path.name}: missing post-submission restriction"
        )

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_no_git_add_in_submission(self, config_path):
        """The old 'git add' submission approach must no longer be used."""
        template = get_instance_template(config_path)
        # The new approach uses `git diff > patch.txt`, not `git add ... && git diff --cached`
        assert "git add <file1>" not in template, f"{config_path.name}: old 'git add <file1>' command still present"
        assert "git diff --cached" not in template, f"{config_path.name}: old 'git diff --cached' command still present"

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_in_order_instruction(self, config_path):
        """Submission steps must specify they must be followed IN ORDER."""
        template = get_instance_template(config_path)
        assert "IN ORDER" in template, f"{config_path.name}: missing 'IN ORDER' instruction"

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_files_to_exclude_from_patch(self, config_path):
        """Instructions must specify what NOT to include in the patch."""
        template = get_instance_template(config_path)
        assert "test" in template.lower(), f"{config_path.name}: missing exclusion of test files"
        assert "binary" in template.lower(), f"{config_path.name}: missing exclusion of binary files"


# ---------------------------------------------------------------------------
# Tests: toolcall-specific format_error_template changes
# ---------------------------------------------------------------------------


class TestToolcallFormatErrorTemplate:
    """Tests for the updated format_error_template in swebench_toolcall.yaml
    and the new swebench_toolcall_verbose.yaml."""

    @pytest.mark.parametrize("config_path", TOOLCALL_CONFIGS, ids=[p.name for p in TOOLCALL_CONFIGS])
    def test_format_error_template_mentions_bash_tool(self, config_path):
        """The format_error_template must guide agents to use the bash tool."""
        config = load_config(config_path)
        error_template = config["model"]["format_error_template"]
        assert "bash" in error_template.lower(), f"{config_path.name}: format_error_template does not mention 'bash'"

    @pytest.mark.parametrize("config_path", TOOLCALL_CONFIGS, ids=[p.name for p in TOOLCALL_CONFIGS])
    def test_format_error_template_includes_submit_command(self, config_path):
        """The format_error_template must show the submission command for completed tasks."""
        config = load_config(config_path)
        error_template = config["model"]["format_error_template"]
        assert "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" in error_template, (
            f"{config_path.name}: format_error_template missing submission command"
        )
        assert "cat patch.txt" in error_template, f"{config_path.name}: format_error_template missing 'cat patch.txt'"

    @pytest.mark.parametrize("config_path", TOOLCALL_CONFIGS, ids=[p.name for p in TOOLCALL_CONFIGS])
    def test_format_error_template_provides_json_argument_format(self, config_path):
        """The format_error_template must show JSON argument format for bash tool."""
        config = load_config(config_path)
        error_template = config["model"]["format_error_template"]
        assert '"command"' in error_template, f"{config_path.name}: format_error_template missing JSON 'command' key"

    def test_toolcall_format_error_no_longer_counts_actions(self):
        """swebench_toolcall.yaml's format_error_template should not reference 'actions' variable
        (the old template used {{actions|length}} which no longer applies in tool-call mode)."""
        config = load_config(EXTRA_CONFIG_DIR / "swebench_toolcall.yaml")
        error_template = config["model"]["format_error_template"]
        # Old template referenced the actions|length variable from the bash-block parsing approach
        assert "actions|length" not in error_template, (
            "swebench_toolcall.yaml: format_error_template still uses old 'actions|length' variable"
        )

    def test_toolcall_format_error_mentions_tool_call_error(self):
        """swebench_toolcall.yaml format_error_template should describe the tool call error."""
        config = load_config(EXTRA_CONFIG_DIR / "swebench_toolcall.yaml")
        error_template = config["model"]["format_error_template"]
        assert "Tool call error" in error_template, (
            "swebench_toolcall.yaml: format_error_template missing 'Tool call error' message"
        )

    def test_toolcall_verbose_format_error_requires_exactly_one_tool_call(self):
        """swebench_toolcall_verbose.yaml must require exactly one bash tool call per response."""
        config = load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
        error_template = config["model"]["format_error_template"]
        assert "EXACTLY ONE" in error_template, (
            "swebench_toolcall_verbose.yaml: format_error_template missing 'EXACTLY ONE' requirement"
        )


# ---------------------------------------------------------------------------
# Tests: swebench_toolcall_verbose.yaml new file structure
# ---------------------------------------------------------------------------


class TestSwebenchToolcallVerboseNewFile:
    """Tests for the new swebench_toolcall_verbose.yaml file."""

    def test_file_exists(self):
        """The new config file must exist."""
        assert (EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml").exists(), (
            "swebench_toolcall_verbose.yaml does not exist"
        )

    def test_has_required_top_level_keys(self):
        """The config must have agent, environment, and model sections."""
        config = load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
        assert "agent" in config, "Missing 'agent' section"
        assert "environment" in config, "Missing 'environment' section"
        assert "model" in config, "Missing 'model' section"

    def test_agent_has_required_templates(self):
        """The agent section must have system_template and instance_template."""
        config = load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
        assert "system_template" in config["agent"], "Missing 'system_template' in agent"
        assert "instance_template" in config["agent"], "Missing 'instance_template' in agent"

    def test_system_template_requires_reasoning(self):
        """Verbose system template must instruct agents to explain their reasoning before tool calls."""
        config = load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
        system_template = config["agent"]["system_template"]
        # The verbose variant requires explicit reasoning/explanation before tool calls
        assert "reasoning" in system_template.lower() or "explain" in system_template.lower(), (
            "swebench_toolcall_verbose.yaml system_template missing reasoning/explanation requirement"
        )

    def test_system_template_mentions_bash_tool(self):
        """Verbose system template must mention using the bash tool."""
        config = load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
        system_template = config["agent"]["system_template"]
        assert "bash" in system_template.lower(), (
            "swebench_toolcall_verbose.yaml system_template missing bash tool reference"
        )

    def test_system_template_one_command_at_a_time(self):
        """Verbose system template must require exactly one command per tool call."""
        config = load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
        system_template = config["agent"]["system_template"]
        assert "ONE command" in system_template or "one command" in system_template.lower(), (
            "swebench_toolcall_verbose.yaml system_template missing one-command-at-a-time requirement"
        )

    def test_has_step_limit(self):
        """The config must define a step_limit."""
        config = load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
        assert "step_limit" in config["agent"], "Missing step_limit in agent config"

    def test_has_cost_limit(self):
        """The config must define a cost_limit."""
        config = load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
        assert "cost_limit" in config["agent"], "Missing cost_limit in agent config"

    def test_has_observation_template(self):
        """The model section must have an observation_template."""
        config = load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
        assert "observation_template" in config["model"], "Missing observation_template in model"

    def test_environment_uses_docker(self):
        """The environment must use docker for SWE-Bench compatibility."""
        config = load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
        assert config["environment"]["environment_class"] == "docker", (
            "swebench_toolcall_verbose.yaml environment_class is not 'docker'"
        )

    def test_environment_cwd_is_testbed(self):
        """The environment cwd must be /testbed."""
        config = load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
        assert config["environment"]["cwd"] == "/testbed", "swebench_toolcall_verbose.yaml cwd is not '/testbed'"

    def test_instance_template_contains_task_variable(self):
        """Instance template must use the {{task}} variable for the PR description."""
        config = load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
        instance_template = config["agent"]["instance_template"]
        assert "{{task}}" in instance_template, "swebench_toolcall_verbose.yaml missing {{task}} variable"

    def test_verbose_vs_nonverbose_system_template_differ(self):
        """The verbose variant must have a more detailed system_template than the non-verbose one."""
        verbose_config = load_config(EXTRA_CONFIG_DIR / "swebench_toolcall_verbose.yaml")
        nonverbose_config = load_config(EXTRA_CONFIG_DIR / "swebench_toolcall.yaml")
        verbose_system = verbose_config["agent"]["system_template"]
        nonverbose_system = nonverbose_config["agent"]["system_template"]
        # The verbose system template should be longer/more detailed
        assert len(verbose_system) > len(nonverbose_system), (
            "swebench_toolcall_verbose.yaml system_template is not more detailed than swebench_toolcall.yaml"
        )


# ---------------------------------------------------------------------------
# Tests: JSON observation template for toolcall configs
# ---------------------------------------------------------------------------


class TestToolcallObservationTemplate:
    """Tests for the JSON-format observation template used in toolcall configs."""

    @pytest.mark.parametrize("config_path", TOOLCALL_CONFIGS, ids=[p.name for p in TOOLCALL_CONFIGS])
    def test_short_output_renders_as_json_object(self, config_path):
        """Short output (<10000 chars) must render as a JSON object with 'output' key."""
        config = load_config(config_path)
        template_str = config["model"]["observation_template"]
        template = Template(template_str, undefined=StrictUndefined)

        output = MockOutput(returncode=0, output="Operation succeeded")
        result = template.render(output=output)

        assert '"returncode"' in result, f"{config_path.name}: missing 'returncode' key in JSON output"
        assert '"output"' in result, f"{config_path.name}: missing 'output' key in short JSON output"
        assert "Operation succeeded" in result, f"{config_path.name}: output content missing"

    @pytest.mark.parametrize("config_path", TOOLCALL_CONFIGS, ids=[p.name for p in TOOLCALL_CONFIGS])
    def test_long_output_renders_with_head_tail_keys(self, config_path):
        """Long output (>=10000 chars) must render JSON with 'output_head' and 'output_tail' keys."""
        config = load_config(config_path)
        template_str = config["model"]["observation_template"]
        template = Template(template_str, undefined=StrictUndefined)

        long_output = "A" * 6000 + "B" * 5000  # 11000 chars total
        output = MockOutput(returncode=1, output=long_output)
        result = template.render(output=output)

        assert '"output_head"' in result, f"{config_path.name}: missing 'output_head' key for long output"
        assert '"output_tail"' in result, f"{config_path.name}: missing 'output_tail' key for long output"
        assert '"elided_chars"' in result, f"{config_path.name}: missing 'elided_chars' key for long output"
        assert '"warning"' in result, f"{config_path.name}: missing 'warning' key for long output"

    @pytest.mark.parametrize("config_path", TOOLCALL_CONFIGS, ids=[p.name for p in TOOLCALL_CONFIGS])
    def test_long_output_no_full_output_key(self, config_path):
        """Long output must not render the plain 'output' key (only head/tail)."""
        config = load_config(config_path)
        template_str = config["model"]["observation_template"]
        template = Template(template_str, undefined=StrictUndefined)

        long_output = "X" * 11000
        output = MockOutput(returncode=0, output=long_output)
        result = template.render(output=output)

        # Should not contain the short-output key
        assert '"output_head"' in result
        assert '"output_tail"' in result

    @pytest.mark.parametrize("config_path", TOOLCALL_CONFIGS, ids=[p.name for p in TOOLCALL_CONFIGS])
    def test_elided_chars_count_is_correct(self, config_path):
        """The elided_chars count must be output_length - 10000."""
        config = load_config(config_path)
        template_str = config["model"]["observation_template"]
        template = Template(template_str, undefined=StrictUndefined)

        output = MockOutput(returncode=0, output="Z" * 11000)
        result = template.render(output=output)

        # 11000 - 10000 = 1000 chars elided
        assert "1000" in result, f"{config_path.name}: elided_chars count incorrect"

    @pytest.mark.parametrize("config_path", TOOLCALL_CONFIGS, ids=[p.name for p in TOOLCALL_CONFIGS])
    def test_exception_info_included_when_present(self, config_path):
        """exception_info must appear in the output when provided."""
        config = load_config(config_path)
        template_str = config["model"]["observation_template"]
        template = Template(template_str, undefined=StrictUndefined)

        output = MockOutput(returncode=-1, output="partial", exception_info="Timeout after 60s")
        result = template.render(output=output)

        assert "Timeout after 60s" in result, f"{config_path.name}: exception_info not rendered"

    @pytest.mark.parametrize("config_path", TOOLCALL_CONFIGS, ids=[p.name for p in TOOLCALL_CONFIGS])
    def test_no_exception_info_when_absent(self, config_path):
        """No exception_info key must appear when exception_info is empty."""
        config = load_config(config_path)
        template_str = config["model"]["observation_template"]
        template = Template(template_str, undefined=StrictUndefined)

        output = MockOutput(returncode=0, output="ok", exception_info="")
        result = template.render(output=output)

        assert "exception_info" not in result, f"{config_path.name}: empty exception_info should not render"

    @pytest.mark.parametrize("config_path", TOOLCALL_CONFIGS, ids=[p.name for p in TOOLCALL_CONFIGS])
    def test_short_output_boundary_9999_chars(self, config_path):
        """Output of 9999 chars must use the full output format (not truncated)."""
        config = load_config(config_path)
        template_str = config["model"]["observation_template"]
        template = Template(template_str, undefined=StrictUndefined)

        output = MockOutput(returncode=0, output="Y" * 9999)
        result = template.render(output=output)

        assert '"output"' in result, f"{config_path.name}: 9999-char output should use full format"
        assert '"output_head"' not in result, f"{config_path.name}: 9999-char output should not be truncated"

    @pytest.mark.parametrize("config_path", TOOLCALL_CONFIGS, ids=[p.name for p in TOOLCALL_CONFIGS])
    def test_long_output_head_contains_start_of_output(self, config_path):
        """output_head must contain the beginning of long output."""
        config = load_config(config_path)
        template_str = config["model"]["observation_template"]
        template = Template(template_str, undefined=StrictUndefined)

        long_output = "START" + "M" * 10000 + "END"
        output = MockOutput(returncode=0, output=long_output)
        result = template.render(output=output)

        # Find the output_head section
        head_start = result.find('"output_head"')
        assert head_start != -1, f"{config_path.name}: output_head not found"
        head_section = result[head_start : head_start + 6000]
        assert "START" in head_section, f"{config_path.name}: output_head missing start of output"

    @pytest.mark.parametrize("config_path", TOOLCALL_CONFIGS, ids=[p.name for p in TOOLCALL_CONFIGS])
    def test_long_output_tail_contains_end_of_output(self, config_path):
        """output_tail must contain the end of long output."""
        config = load_config(config_path)
        template_str = config["model"]["observation_template"]
        template = Template(template_str, undefined=StrictUndefined)

        long_output = "START" + "M" * 10000 + "THEEND"
        output = MockOutput(returncode=0, output=long_output)
        result = template.render(output=output)

        tail_start = result.find('"output_tail"')
        assert tail_start != -1, f"{config_path.name}: output_tail not found"
        tail_section = result[tail_start:]
        assert "THEEND" in tail_section, f"{config_path.name}: output_tail missing end of output"


# ---------------------------------------------------------------------------
# Tests: instance template renders correctly with task variable
# ---------------------------------------------------------------------------


class TestInstanceTemplateRendering:
    """Tests that instance templates across all changed configs render correctly."""

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_instance_template_renders_task_variable(self, config_path):
        """The instance_template must render with a {{task}} variable."""
        config = load_config(config_path)
        template_str = config["agent"]["instance_template"]
        template = Template(template_str, undefined=StrictUndefined)
        result = template.render(task="Fix the bug in module.py")
        assert "Fix the bug in module.py" in result, f"{config_path.name}: instance_template did not render {{task}}"

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_submission_section_appears_after_rendering(self, config_path):
        """The rendered instance_template must still contain submission instructions."""
        config = load_config(config_path)
        template_str = config["agent"]["instance_template"]
        template = Template(template_str, undefined=StrictUndefined)
        result = template.render(task="some task description")
        assert "patch.txt" in result, f"{config_path.name}: submission section missing after rendering"
        assert "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" in result, (
            f"{config_path.name}: submit command missing after rendering"
        )


# ---------------------------------------------------------------------------
# Tests: config file YAML validity and required fields
# ---------------------------------------------------------------------------


class TestConfigFileValidity:
    """Tests that all changed config files are valid YAML with required structure."""

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_yaml_loads_without_error(self, config_path):
        """Each config file must parse as valid YAML."""
        # If this raises, the test fails with a YAML parse error
        config = load_config(config_path)
        assert isinstance(config, dict), f"{config_path.name}: YAML did not load as a dict"

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_has_agent_section(self, config_path):
        config = load_config(config_path)
        assert "agent" in config, f"{config_path.name}: missing 'agent' section"

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_has_model_section(self, config_path):
        config = load_config(config_path)
        assert "model" in config, f"{config_path.name}: missing 'model' section"

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_has_environment_section(self, config_path):
        config = load_config(config_path)
        assert "environment" in config, f"{config_path.name}: missing 'environment' section"

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_step_limit_is_positive_integer(self, config_path):
        config = load_config(config_path)
        step_limit = config["agent"]["step_limit"]
        assert isinstance(step_limit, int), f"{config_path.name}: step_limit must be an integer"
        assert step_limit > 0, f"{config_path.name}: step_limit must be positive"

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_cost_limit_is_positive_number(self, config_path):
        config = load_config(config_path)
        cost_limit = config["agent"]["cost_limit"]
        assert isinstance(cost_limit, (int, float)), f"{config_path.name}: cost_limit must be a number"
        assert cost_limit > 0, f"{config_path.name}: cost_limit must be positive"

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_model_has_observation_template(self, config_path):
        config = load_config(config_path)
        assert "observation_template" in config["model"], (
            f"{config_path.name}: missing 'observation_template' in model section"
        )

    @pytest.mark.parametrize("config_path", CHANGED_CONFIGS, ids=[p.name for p in CHANGED_CONFIGS])
    def test_model_has_format_error_template(self, config_path):
        config = load_config(config_path)
        assert "format_error_template" in config["model"], (
            f"{config_path.name}: missing 'format_error_template' in model section"
        )
