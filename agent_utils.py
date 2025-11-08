# agent_utils.py (The new, universal version)

import subprocess
import re
import sys
from pathlib import Path

def start_group(title):
    print(f"\n::group::{title}")

def end_group():
    print("::endgroup::")

def run_command(command, cwd=None, display_command=True):
    if display_command:
        display_str = ' '.join(command)
        print(f"--> Running command: '{display_str}' in CWD: '{cwd or '.'}'")
    result = subprocess.run(command, capture_output=True, text=True, cwd=cwd)
    return result.stdout, result.stderr, result.returncode

def _parse_pytest_summary(full_output: str) -> dict:
    summary = {"passed": "0", "failed": "0", "errors": "0", "skipped": "0"}
    summary_line = ""
    for line in reversed(full_output.splitlines()):
        if "=" in line and ("passed" in line or "failed" in line or "skipped" in line):
            summary_line = line.strip()
            break
    if not summary_line: return summary
    matches = re.findall(r"(\d+)\s+(passed|failed|skipped|errors)", summary_line)
    for count, status in matches:
        if status in summary: summary[status] = count
    return summary


def _run_smoke_test(python_executable: str, config: dict) -> tuple[bool, str, str]:
    print("\n--- Running Smoke Test ---")
    validation_config = config.get("VALIDATION_CONFIG", {})
    script_path = validation_config.get("smoke_test_script")
    project_dir = validation_config.get("project_dir") 
    
    if not script_path:
        return False, "Smoke test failed: 'smoke_test_script' not defined in AGENT_CONFIG.", ""
    
    command = [python_executable, str(Path(script_path).resolve())]
    stdout, stderr, returncode = run_command(command, cwd=project_dir)

    # --- START OF NEW DEBUGGING LOGIC ---
    # Combine stdout and stderr to make sure we see everything.
    full_output = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
    if returncode != 0:
        print("CRITICAL VALIDATION FAILURE: Smoke test failed.", file=sys.stderr)
        # Always print the full output, which now contains our forensic data.
        print(f"--- Smoke Test Full Output ---\n{full_output}\n--- End of Full Output ---")
        return False, f"Smoke test failed with exit code {returncode}", stdout + stderr
    # --- END OF NEW DEBUGGING LOGIC ---
    
    print("Smoke test PASSED.")
    return True, "Smoke test passed.", stdout + stderr

def _run_pytest_suite(python_executable: str, config: dict) -> tuple[bool, str, str]:
    """Runs a full pytest suite and provides a detailed result."""
    print("\n--- Running Full Pytest Suite ---")
    validation_config = config.get("VALIDATION_CONFIG", {})
    target = validation_config.get("pytest_target")
    project_dir = validation_config.get("project_dir")

    if not target:
        return False, "Pytest failed: 'pytest_target' not defined in AGENT_CONFIG.", ""
    
    command = [python_executable, "-m", "pytest", str(target)]
    stdout, stderr, returncode = run_command(command, cwd=project_dir)
    full_output = stdout + stderr

    # --- START OF NEW, MORE ROBUST CHECK ---
    # First, check if any tests were collected. This is the most important check.
    collection_match = re.search(r"(\d+)\s+tests? collected", full_output)
    if collection_match and int(collection_match.group(1)) == 0:
        error_message = f"Pytest failed: Zero tests were collected. Check the 'pytest_target' in AGENT_CONFIG. Searched for '{target}' in '{project_dir}'."
        print(f"VALIDATION FAILED: {error_message}", file=sys.stderr)
        return False, "Pytest collected 0 tests", full_output
    # --- END OF NEW, MORE ROBUST CHECK ---

    summary = _parse_pytest_summary(full_output)
    total_failures = int(summary["failed"]) + int(summary["errors"])
    threshold = config.get("ACCEPTABLE_FAILURE_THRESHOLD", 0)

    if total_failures > threshold:
        reason = f"{total_failures} failures/errors, which exceeds the threshold of {threshold}."
        print(f"VALIDATION FAILED: {reason}", file=sys.stderr)
        return False, reason, full_output
    
    metrics_body = f"Pytest Run Summary:\n- Passed: {summary['passed']}\n- Failed: {summary['failed']}\n- Skipped: {summary['skipped']}"
    if total_failures > 0:
        print(f"VALIDATION PASSED (soft): {total_failures} failures/errors are within the threshold.")
    else:
        print("Full pytest suite PASSED.")
    
    return True, metrics_body, full_output

def validate_changes(python_executable: str, config: dict, group_title: str="Running Validation") -> tuple[bool, str, str]:
    start_group(group_title)
    
    validation_config = config.get("VALIDATION_CONFIG", {})
    validation_type = validation_config.get("type")
    
    success, metrics_body, full_output = False, "No validation performed.", ""

    if validation_type == "script":
        success, metrics_body, full_output = _run_smoke_test(python_executable, config)
    elif validation_type == "pytest":
        success, metrics_body, full_output = _run_pytest_suite(python_executable, config)
    elif validation_type == "smoke_test_with_pytest_report":
        smoke_success, smoke_reason, smoke_output = _run_smoke_test(python_executable, config)
        full_output += smoke_output
        if not smoke_success:
            end_group()
            return False, smoke_reason, full_output
        
        print("\n--- Smoke test passed. Proceeding to full pytest suite. ---")
        pytest_success, pytest_metrics, pytest_output = _run_pytest_suite(python_executable, config)
        full_output += "\n\n" + pytest_output
        
        success = pytest_success
        metrics_body = f"Smoke Test: {smoke_reason}\n\n{pytest_metrics}"
    else:
        print(f"ERROR: Unknown or undefined validation type in AGENT_CONFIG: '{validation_type}'.", file=sys.stderr)
        success, metrics_body, full_output = False, f"Unknown validation type: {validation_type}", ""

    end_group()
    return success, metrics_body, full_output