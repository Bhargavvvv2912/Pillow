# reconcile.py (The Final, Generic, and Correct Version)

import subprocess
from pathlib import Path
import toml
import re
import sys
import argparse # Use argparse for clean command-line arguments

def get_package_name_from_line(line: str) -> str | None:
    """Robustly extracts the package name from a requirements line."""
    match = re.match(r'^(-e\s+)?([a-zA-Z0-9\-_]+)', line.strip())
    return match.group(2) if match else None

def main():
    # --- START OF GENERIC IMPLEMENTATION ---
    parser = argparse.ArgumentParser(description="Reconcile a requirements.txt with a pyproject.toml.")
    parser.add_argument("project_dir", type=str, help="The path to the project directory (e.g., ./Pillow).")
    args = parser.parse_args()

    project_path = Path(args.project_dir)
    pyproject_path = project_path / "pyproject.toml"
    project_name = project_path.name
    # --- END OF GENERIC IMPLEMENTATION ---

    golden_record_path = Path("generated-requirements.txt")

    if not pyproject_path.exists():
        sys.exit(f"ERROR: pyproject.toml not found at {pyproject_path}")

    # --- Step 1: Get the list of intended dependencies from pyproject.toml ---
    with open(pyproject_path, "r") as f:
        data = toml.load(f)
    build_deps = data.get('build-system', {}).get('requires', [])
    test_deps = data.get('project', {}).get('optional-dependencies', {}).get('tests', [])
    
    # --- THIS LINE IS NOW GENERIC ---
    intended_deps_list = [project_name] + [get_package_name_from_line(dep) for dep in build_deps + test_deps]
    intended_deps_set = {name.lower() for name in intended_deps_list if name}

    # --- Step 2: Create Golden Record if it doesn't exist ---
    if not golden_record_path.exists():
        print(f"Golden Record ({golden_record_path}) not found. Generating a new one from scratch...")
        with open('requirements.in', 'w') as f:
            f.write(f'-e ./{project_name}\n') # Use the generic project name
            for dep in build_deps + test_deps: f.write(f'{dep}\n')
            
        return_code = subprocess.run(
            ["pip-compile", "--resolver=backtracking", "--output-file", str(golden_record_path), "requirements.in"],
            capture_output=True, text=True
        )
        if return_code.returncode != 0:
            print("ERROR: pip-compile failed during initial generation.", file=sys.stderr)
            print(return_code.stderr, file=sys.stderr)
            sys.exit(1)
        print("Successfully generated a new Golden Record.")
        return

    # --- Step 3: Reconcile existing Golden Record ---
    print("Golden Record found. Reconciling with pyproject.toml...")
    with open(golden_record_path, "r") as f:
        existing_package_names = {get_package_name_from_line(line).lower() for line in f if line.strip() and get_package_name_from_line(line)}

    missing_packages = intended_deps_set - existing_package_names
    
    if not missing_packages:
        print("Golden Record is in sync with pyproject.toml. No new dependencies to add.")
        return

    print(f"Found {len(missing_packages)} new dependencies in pyproject.toml to add: {missing_packages}")
    
    with open('requirements.in', 'w') as f:
        with open(golden_record_path, 'r') as grf:
            f.write(grf.read())
        for new_pkg in missing_packages:
            f.write(f'\n{new_pkg}')

    print("Re-compiling to add new packages and their dependencies...")
    return_code = subprocess.run(
        ["pip-compile", "--resolver=backtracking", "--output-file", str(golden_record_path), "requirements.in"],
        capture_output=True, text=True
    )
    if return_code.returncode != 0:
        print("ERROR: pip-compile failed during reconciliation.", file=sys.stderr)
        print(return_code.stderr, file=sys.stderr)
        sys.exit(1)
    
    print("Golden Record has been successfully updated with new dependencies.")

if __name__ == "__main__":
    main()