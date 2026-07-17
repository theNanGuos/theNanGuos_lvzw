import os
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
START_SCRIPT = ROOT_DIR / "start.sh"


def run_sourced_script(expression: str, **environment: str) -> subprocess.CompletedProcess[str]:
    merged_environment = os.environ.copy()
    merged_environment.update(environment)
    return subprocess.run(
        ["bash", "-c", 'source "$1"; eval "$2"', "test-start-script", str(START_SCRIPT), expression],
        cwd=ROOT_DIR,
        env=merged_environment,
        check=False,
        capture_output=True,
        text=True,
    )


def test_start_script_has_valid_bash_syntax():
    result = subprocess.run(
        ["bash", "-n", str(START_SCRIPT)],
        cwd=ROOT_DIR,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_start_script_accepts_supported_node_versions():
    for version in ("20.19.0", "20.20.1", "22.12.0", "24.0.0"):
        result = run_sourced_script(f"node_version_supported {version}")
        assert result.returncode == 0, version


def test_start_script_rejects_unsupported_node_versions():
    for version in ("20.18.9", "21.7.3", "22.11.0", "invalid"):
        result = run_sourced_script(f"node_version_supported {version}")
        assert result.returncode != 0, version


def test_start_script_rejects_placeholder_environment_values():
    placeholder_key = run_sourced_script(
        "env_key_is_configured OPENAI_API_KEY",
        OPENAI_API_KEY="your-api-key",
    )
    placeholder_url = run_sourced_script(
        "env_key_is_configured OPENAI_BASE_URL",
        OPENAI_BASE_URL="https://your-openai-compatible-endpoint/v1",
    )
    configured_key = run_sourced_script(
        "env_key_is_configured OPENAI_API_KEY",
        OPENAI_API_KEY="test-key",
    )

    assert placeholder_key.returncode != 0
    assert placeholder_url.returncode != 0
    assert configured_key.returncode == 0
