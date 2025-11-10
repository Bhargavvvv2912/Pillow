# reconcile.py (The Final, Correct, and Simple Version)

import subprocess
from pathlib import Path
import toml
import re
import sys
import argparse
import filecmp

def main():
    parser = argparse.ArgumentParser(description="Reconcile a requirements.txt with a pyproject.toml.")
    parser.add_argument("project_dir", type=str, help="The path to the project directory (e.g., ./Pillow).")
    args = parser.parse_args()

    project_path = Path(args.project_dir)
    pyproject_path = project_path / "pyproject.toml"
    golden_record_path = Path("generated-requirements.txt")
    ideal_state_path = Path("temp-ideal-state.txt")
    requirements_in_path = Path("requirements.in")

    if not pyproject_path.exists():
        sys.exit(f"ERROR: pyproject.toml not found at {pyproject_path}")

    # --- Step 1: Always generate the "ideal state" based on pyproject.toml ---
    print("Generating ideal state from pyproject.toml...")
    with open(pyproject_path, "r") as f:
        data = toml.load(f)
    build_deps = data.get('build-system', {}).get('requires', [])
    test_deps = data.get('project', {}).get('optional-dependencies', {}).get('tests', [])

    with open(requirements_in_path, 'w') as f:
        f.write(f'-e ./{project_path.name}\n')
        for dep in build_deps + test_deps:
            f.write(f'{dep}\n')
            
    compile_cmd = [
        "pip-compile", "--resolver=backtracking", "--output-file", str(ideal_state_path), str(requirements_in_path)
    ]
    result = subprocess.run(compile_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ERROR: pip-compile failed to generate ideal state.", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    
    # --- Step 2: Compare and Reconcile ---
    if not golden_record_path.exists():
        print(f"Golden Record ({golden_record_path}) not found. Creating it from the ideal state.")
        shutil.copy(ideal_state_path, golden_record_path)
        return

    # Compare the file contents. filecmp is robust to small whitespace/comment differences if desired,
    # but for our purpose, a direct comparison is fine after cleaning.
    # To be fully robust, we read and compare the significant lines.
    with open(ideal_state_path, "r") as f:
        ideal_lines = {line.strip() for line in f if line.strip() and not line.startswith('#')}
    with open(golden_record_path, "r") as f:
        golden_lines = {line.strip() for line in f if line.strip() and not line.startswith('#')}

    if ideal_lines == golden_lines:
        print("Golden Record is already in sync with pyproject.toml. No changes needed.")
    else:
        print("Change detected between ideal state and Golden Record. Updating Golden Record.")
        # If a developer added a new dependency to pyproject.toml, this will update the golden record.
        # If our agent updated a dependency, this will be a no-op as the agent already changed the file.
        # (This logic can be refined, but for now, "latest ideal state wins" is safe)
        shutil.copy(ideal_state_path, golden_record_path)
        print("Golden Record has been updated.")

if __name__ == "__main__":
    import shutil
    main()