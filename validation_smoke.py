# validation_smoke.py

import sys
import os
import platform
from PIL import Image, ImageFilter
import tempfile

def run_pillow_smoke_test():
    """
    Performs a simple but representative workflow with Pillow to validate its core functionality.
    Includes a detailed debugging section to diagnose environmental issues.
    """
    
    # --- START OF NEW DEBUGGING SECTION ---
    print("--- Smoke Test Forensic Analysis ---")
    print(f"Python Executable: {sys.executable}")
    print(f"Python Version: {platform.python_version()}")
    print(f"Current Working Directory: {os.getcwd()}")
    print("\n--- sys.path ---")
    # Print the system path to see the order Python will search for modules
    for i, path in enumerate(sys.path):
        print(f"  {i}: {path}")
    print("--- End of sys.path ---\n")
    try:
        import PIL
        print(f"Successfully imported PIL. Module location: {PIL.__file__}")
    except Exception as e:
        print(f"CRITICAL: Failed to import PIL. Error: {e}", file=sys.stderr)
        # We exit here because if the import fails, none of the other tests can run.
        sys.exit(1)
    print("--- End of Forensic Analysis ---\n")
    # --- END OF NEW DEBUGGING SECTION ---

    print("--- Starting Pillow Smoke Test ---")
    output_filename = os.path.join(tempfile.gettempdir(), "smoke_test_output.png")

    try:
        print("Running Basic Test: Create, inspect, save...")
        img_basic = Image.new("RGB", (100, 50), "black")
        assert img_basic.size == (100, 50), f"Basic Test Failed: Incorrect size."
        img_basic.save(output_filename, "PNG")
        print("Basic Test PASSED.")

        print("\nRunning Complex Test: Open, filter, inspect pixels...")
        img_complex = Image.new("L", (3, 3), "white")
        img_complex.putpixel((1, 1), 0)
        filtered_img = img_complex.filter(ImageFilter.GaussianBlur(radius=1))
        center_pixel = filtered_img.getpixel((1, 1))
        corner_pixel = filtered_img.getpixel((0, 0))
        assert 0 < center_pixel < 255, f"Complex Test Failed: Center pixel value incorrect."
        assert 0 < corner_pixel < 255, f"Complex Test Failed: Corner pixel value incorrect."
        print("Complex Test PASSED.")
        
        print("\n--- Pillow Smoke Test: ALL TESTS PASSED ---")
        sys.exit(0)

    except Exception as e:
        print(f"\n--- Pillow Smoke Test: FAILED ---", file=sys.stderr)
        print(f"Error during smoke test: {type(e).__name__} - {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if os.path.exists(output_filename):
            os.remove(output_filename)

if __name__ == "__main__":
    run_pillow_smoke_test()