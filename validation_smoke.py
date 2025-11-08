# validation_smoke.py

import sys
from PIL import Image, ImageFilter
import tempfile # <--- IMPORT THIS
import os       # <--- IMPORT THIS

def run_pillow_smoke_test():
    """
    Performs a simple but representative workflow with Pillow to validate its core functionality.
    This acts as a fast "smoke test" to catch catastrophic failures.
    """
    print("--- Starting Pillow Smoke Test ---")
    
    # --- START OF FIX: Use a temporary file ---
    # This creates a temporary file path that is guaranteed to be unique.
    output_filename = os.path.join(tempfile.gettempdir(), "smoke_test_output.png")
    # --- END OF FIX ---

    try:
        print("Running Basic Test: Create, inspect, save...")
        img_basic = Image.new("RGB", (100, 50), "black")
        assert img_basic.size == (100, 50), f"Basic Test Failed: Incorrect size. Expected (100, 50), got {img_basic.size}"
        
        # --- START OF FIX: Save to the unique temporary file ---
        img_basic.save(output_filename, "PNG")
        # --- END OF FIX ---
        
        print("Basic Test PASSED.")

        print("\nRunning Complex Test: Open, filter, inspect pixels...")
        img_complex = Image.new("L", (3, 3), "white")
        img_complex.putpixel((1, 1), 0)
        filtered_img = img_complex.filter(ImageFilter.GaussianBlur(radius=1))
        center_pixel = filtered_img.getpixel((1, 1))
        corner_pixel = filtered_img.getpixel((0, 0))
        assert 0 < center_pixel < 255, f"Complex Test Failed: Center pixel value is {center_pixel}, expected it to be blurred."
        assert 0 < corner_pixel < 255, f"Complex Test Failed: Corner pixel value is {corner_pixel}, expected it to be blurred."
        
        print("Complex Test PASSED.")
        
        print("\n--- Pillow Smoke Test: ALL TESTS PASSED ---")
        sys.exit(0)

    except Exception as e:
        print(f"\n--- Pillow Smoke Test: FAILED ---", file=sys.stderr)
        print(f"Error during smoke test: {type(e).__name__} - {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # --- START OF FIX: Clean up the temporary file ---
        # This ensures that no matter what happens, we don't leave stray files behind.
        if os.path.exists(output_filename):
            os.remove(output_filename)
        # --- END OF FIX ---


if __name__ == "__main__":
    run_pillow_smoke_test()