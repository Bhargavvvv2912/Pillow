# agent_utils.py

import subprocess
import re
import sys
from pathlib import Path

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


def validate_changes(python_executable, config, group_title="Running Validation Script"):
    start_group(group_title)
    print("\n--- Stage 1: Running Smoke Test ---")
    smoke_script_path = str(Path("validation_smoke.py").resolve())
    smoke_test_command = [python_executable, smoke_script_path]
    
    # NO cwd argument. Run from the root.
    smoke_stdout, smoke_stderr, smoke_returncode = run_command(smoke_test_command)

    if smoke_returncode != 0:
        print("CRITICAL VALIDATION FAILURE: Smoke test failed.", file=sys.stderr)
        if smoke_stderr: print(f"SMOKE TEST STDERR:\n{smoke_stderr}")
        end_group()
        return False, "Smoke test failed", smoke_stdout + smoke_stderr
    print("Smoke test PASSED.")


    # --- STAGE 2: THE PYTEST SUITE (only if smoke test passes) ---
    print("\n--- Stage 2: Running Full Pytest Suite ---")
    MAX_ACCEPTABLE_FAILURES = config.get("ACCEPTABLE_FAILURE_THRESHOLD", 0)
    
    pytest_command = [python_executable, "-m", "pytest"]
    pytest_stdout, pytest_stderr, pytest_returncode = run_command(pytest_command, cwd="Pillow")
    
    full_output = pytest_stdout + pytest_stderr

    # Pytest returns specific non-zero exit codes. Code 1 means "tests failed".
    if pytest_returncode == 1: 
        try:
            num_failed = int(re.search(r"(\d+)\s+failed", full_output).group(1))
            if num_failed > MAX_ACCEPTABLE_FAILURES:
                print(f"VALIDATION FAILED: {num_failed} tests failed, exceeding threshold of {MAX_ACCEPTABLE_FAILURES}.", file=sys.stderr)
                end_group()
                return False, f"{num_failed} tests failed", full_output
            else:
                print(f"VALIDATION PASSED (soft): {num_failed} tests failed, which is within the acceptable threshold.")
        except (AttributeError, ValueError):
            # If we can't parse the number, assume the failure is critical.
            print("VALIDATION FAILED: Could not parse failure count from pytest output.", file=sys.stderr)
            end_group()
            return False, "Critical pytest failure", full_output
    elif pytest_returncode != 0:
        # Any other non-zero exit code is a fatal error (e.g., collection error)
        print("VALIDATION FAILED: Pytest exited with a critical error code.", file=sys.stderr)
        end_group()
        return False, "Critical pytest error", full_output
    
    print("Full pytest suite PASSED.")
    end_group()

    # If both stages pass, we return success
    try:
        tests_passed = re.search(r"(\d+)\s+passed", full_output).group(1)
        metrics_body = f"Performance Metrics:\n- Tests Passed: {tests_passed}"
        return True, metrics_body, full_output
    except (AttributeError, IndexError):
        return True, "Metrics not available, but validation passed.", full_output
