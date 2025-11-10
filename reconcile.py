# reconcile.py (The Final, Correct, and Robust Version)

import subprocess
from pathlib import Path
import toml
import re
import sys
import argparse

def get_package_name_from_line(line: str) -> str | None:
    """Robustly extracts the package name from a requirements line, handling editable installs."""
    line = line.strip()
    if line.startswith('-e'):
        # For editable installs like '-e ./Pillow', the package name is the directory name.
        # This is a robust way to handle it.
        return Path(line.split(' ')[-1]).name
    
    # For regular lines like 'pytest==9.0.0', use a regex.
    match = re.match(r'([a-zA-Z0-9\-_]+)', line)
    return match.group(1) if match else None

def main():
    parser = argparse.ArgumentParser(description="Reconcile a requirements.txt with a pyproject.toml.")
    parser.add_argument("project_dir", type=str, help="The path to the project directory (e.g., ./Pillow).")
    args = parser.parse_args()

    project_path = Path(args.project_dir)
    pyproject_path = project_path / "pyproject.toml"
    project_name = project_path.name
    golden_record_path = Path("generated-requirements.txt")

    if not pyproject_path.exists():
        sys.exit(f"ERROR: pyproject.toml not found at {pyproject_path}")

    # --- Step 1: Get the list of intended high-level dependencies ---
    with open(pyproject_path, "r") as f:
        data = toml.load(f)
    build_deps = data.get('build-system', {}).get('requires', [])
    test_deps = data.get('project', {}).get('optional-dependencies', {}).get('tests', [])
    
    # Create the text for a "perfect" requirements.in
    # This includes the project itself in editable mode, plus all build/test deps.
    requirements_in_content = [f"-e ./{project_name}"] + build_deps + test_deps
    
    # --- Step 2: Generate the "ideal state" lock file ---
    ideal_state_path = Path("temp-ideal-state.txt")
    with open("requirements.in", "w") as f:
        f.write("\n".join(requirements_in_content))
    
    print("Compiling ideal state from pyproject.toml...")
    compile_cmd = [
        "pip-compile", "--resolver=backtracking", "--output-file", str(ideal_state_path), "requirements.in"
    ]
    result = subprocess.run(compile_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ERROR: pip-compile failed to generate ideal state.", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    # --- Step 3: Create or reconcile the Golden Record ---
    if not golden_record_path.exists():
        print(f"Golden Record ({golden_record_path}) not found. Creating a clean copy from ideal state.")
        # If it's the first run, the ideal state IS the golden record.
        shutil.copy(ideal_state_path, golden_record_path)
        return

    print("Golden Record found. Reconciling...")
    
    with open(ideal_state_path, "r") as f:
        ideal_packages = {get_package_name_from_line(line).lower() for line in f if line.strip() and not line.startswith('#') and get_package_name_from_line(line)}
    
    with open(golden_record_path, "r") as f:
        golden_packages = {get_package_name_from_line(line).lower() for line in f if line.strip() and not line.startswith('#') and get_package_name_from_line(line)}

    newly_discovered_packages = ideal_packages - golden_packages

    if not newly_discovered_packages:
        print("Golden Record is in sync with pyproject.toml. No changes needed.")
        return

    print(f"Found {len(newly_discovered_packages)} new dependencies to add: {newly_discovered_packages}")
    
    # To add them correctly while respecting existing pins, we re-compile.
    # The new requirements.in will be the current golden record + the new unpinned packages.
    with open("requirements.in", "w") as f:
        with open(golden_record_path, "r") as grf:
            f.write(grf.read())
        f.write("\n") # Ensure a newline
        for pkg_name in newly_discovered_packages:
            # We add the name only; pip-compile will find the version.
            f.write(f"{pkg_name}\n")
            
    print("Re-compiling Golden Record to include new packages...")
    recompile_cmd = [
        "pip-compile", "--resolver=backtracking", "--output-file", str(golden_record_path), "requirements.in"
    ]
    result = subprocess.run(recompile_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ERROR: pip-compile failed during reconciliation.", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
        
    print("Golden Record successfully updated.")


if __name__ == "__main__":
    import shutil
    main()