# reconcile.py (The Final, Correct Version That Excludes the Project Itself)

import subprocess
from pathlib import Path
import toml
import re
import sys
import argparse

def get_package_name_from_line(line: str) -> str | None:
    """Robustly extracts the package name from a requirements line."""
    line = line.strip()
    if line.startswith('-e'):
        # Exclude editable installs from our dependency logic.
        return None
    
    match = re.match(r'([a-zA-Z0-9\-_]+)', line)
    return match.group(1) if match else None

def main():
    parser = argparse.ArgumentParser(description="Reconcile a requirements.txt with a pyproject.toml.")
    parser.add_argument("project_dir", type=str, help="The path to the project directory (e.g., ./Pillow).")
    args = parser.parse_args()

    project_path = Path(args.project_dir)
    pyproject_path = project_path / "pyproject.toml"
    golden_record_path = Path("generated-requirements.txt")
    requirements_in_path = Path("requirements.in")

    if not pyproject_path.exists():
        sys.exit(f"ERROR: pyproject.toml not found at {pyproject_path}")

    # --- Step 1: Get the set of intended top-level dependencies from pyproject.toml ---
    with open(pyproject_path, "r") as f:
        data = toml.load(f)
    build_deps = data.get('build-system', {}).get('requires', [])
    test_deps = data.get('project', {}).get('optional-dependencies', {}).get('tests', [])
    
    # This is the set of required TOOLS, not the project itself.
    intended_dep_names = {get_package_name_from_line(dep).lower() for dep in build_deps + test_deps if get_package_name_from_line(dep)}

    # --- Step 2: Handle the "first run" case ---
    if not golden_record_path.exists():
        print(f"Golden Record ({golden_record_path}) not found. Generating a new one from scratch...")
        with open(requirements_in_path, 'w') as f:
            # The .in file contains ONLY the dependencies, not the project.
            for dep in build_deps + test_deps: f.write(f'{dep}\n')
            
        compile_cmd = ["pip-compile", "--resolver=backtracking", "--output-file", str(golden_record_path), str(requirements_in_path)]
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("ERROR: pip-compile failed during initial generation.", file=sys.stderr); print(result.stderr, file=sys.stderr); sys.exit(1)
        print("Successfully generated a new Golden Record of dependencies.")
        return

    # --- Step 3: The Definitive Reconciliation Logic ---
    print("Golden Record found. Checking for missing dependencies from pyproject.toml...")
    with open(golden_record_path, "r") as f:
        existing_package_names = {get_package_name_from_line(line).lower() for line in f if line.strip() and get_package_name_from_line(line)}

    # We only care if a TOP-LEVEL dependency from pyproject.toml is completely missing.
    missing_top_level_deps = intended_dep_names - existing_package_names
    
    if not missing_top_level_deps:
        print("Golden Record is in sync with pyproject.toml. No new top-level dependencies found.")
        return

    print(f"Found {len(missing_top_level_deps)} new top-level dependencies to add: {missing_top_level_deps}")
    
    # To add them while respecting all existing pins, we re-compile.
    with open(requirements_in_path, 'w') as f:
        with open(golden_record_path, 'r') as grf:
            f.write(grf.read())
        f.write("\n")
        for new_pkg_name in missing_top_level_deps:
            f.write(f"{new_pkg_name}\n")
            
    print("Re-compiling Golden Record to add new packages...")
    recompile_cmd = ["pip-compile", "--resolver=backtracking", "--output-file", str(golden_record_path), str(requirements_in_path)]
    result = subprocess.run(recompile_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ERROR: pip-compile failed during reconciliation.", file=sys.stderr); print(result.stderr, file=sys.stderr); sys.exit(1)
        
    print("Golden Record successfully updated.")

if __name__ == "__main__":
    main()