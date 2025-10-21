# agent_utils.py

import subprocess
import re
import sys

def start_group(title):
    print(f"\n::group::{title}")

def end_group():
    print("::endgroup::")

def run_command(command, cwd=None):
    # Added more verbose logging to help with debugging
    display_command = ' '.join(command)
    print(f"--> Running command: '{display_command}' in CWD: '{cwd or '.'}'")
    result = subprocess.run(command, capture_output=True, text=True, cwd=cwd)
    return result.stdout, result.stderr, result.returncode

def validate_changes(python_executable, group_title="Running Validation Script"):
    """
    Runs the Pillow library's own test suite as the validation oracle.
    """
    start_group(group_title)
    
    # Pillow's tests are run with pytest from the root of their repo.
    validation_command = [python_executable, "-m", "pytest"]
    
    print("\n--- Running Pillow Test Suite (pytest) ---")
    
    # The command MUST be run from inside the 'Pillow' directory.
    stdout, stderr, returncode = run_command(validation_command, cwd="Pillow")

    # ... The rest of the function (log printing and metric parsing)
    # can remain IDENTICAL to the requests version. It is already general-purpose.
    if stdout:
        print(f"STDOUT:\n---\n{stdout[:2000]}...\n---")
    if stderr:
        print(f"STDERR:\n---\n{stderr}\n---")

    if returncode != 0:
        print("Validation Failed: Pytest returned a non-zero exit code.", file=sys.stderr)
        end_group()
        return False, None, stdout + stderr
    
    print("Validation script (pytest) completed successfully.")
    end_group()

    try:
        match = re.search(r"(\d+)\s+passed", stdout + stderr)
        tests_passed = match.group(1)
        metrics_body = f"Performance Metrics:\n- Tests Passed: {tests_passed}"
        return True, metrics_body, stdout + stderr
    except (AttributeError, IndexError):
        return True, "Metrics not available, but validation passed.", stdout + stderr 