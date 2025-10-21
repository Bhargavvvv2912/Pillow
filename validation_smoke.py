# validation_smoke.py

import sys
from PIL import Image, ImageFilter

def run_pillow_smoke_test():
    """
    Performs a simple but representative workflow with Pillow to validate its core functionality.
    This acts as a fast "smoke test" to catch catastrophic failures.
    """
    print("--- Starting Pillow Smoke Test ---")
    
    try:
        # --- Test 1: The "Basic" Test ---
        # Goal: Can we create an image, get its size, and save it in a different format?
        # This tests core object creation, property access, and saving logic.
        print("Running Basic Test: Create, inspect, save...")
        
        # Create a new, small black image
        img_basic = Image.new("RGB", (100, 50), "black")
        
        # Verify a basic property
        assert img_basic.size == (100, 50), f"Basic Test Failed: Incorrect size. Expected (100, 50), got {img_basic.size}"
        
        # Save it to a temporary file in a different format (PNG)
        img_basic.save("smoke_test_output.png", "PNG")
        
        print("Basic Test PASSED.")

        # --- Test 2: The "Complex" Test ---
        # Goal: Can we open an image, apply a transformation (a filter), and verify the change?
        # This tests file opening, C-extension-based filtering, and pixel manipulation.
        print("\nRunning Complex Test: Open, filter, inspect pixels...")
        
        # Create a simple white image with a single black pixel in the center
        img_complex = Image.new("L", (3, 3), "white")
        img_complex.putpixel((1, 1), 0) # Black pixel in the center

        # Apply a GaussianBlur filter. This is a classic C-powered operation.
        filtered_img = img_complex.filter(ImageFilter.GaussianBlur(radius=1))

        # Verify the complex operation: The center pixel should no longer be pure black,
        # and the corner pixel should no longer be pure white.
        center_pixel = filtered_img.getpixel((1, 1))
        corner_pixel = filtered_img.getpixel((0, 0))
        
        assert 0 < center_pixel < 255, f"Complex Test Failed: Center pixel value is {center_pixel}, expected it to be blurred (not pure black or white)."
        assert 0 < corner_pixel < 255, f"Complex Test Failed: Corner pixel value is {corner_pixel}, expected it to be blurred (not pure white)."
        
        print("Complex Test PASSED.")
        
        # --- If all tests pass ---
        print("\n--- Pillow Smoke Test: ALL TESTS PASSED ---")
        sys.exit(0) # Exit with a success code

    except Exception as e:
        # If any part of the workflow fails, print the error to stderr and exit with a failure code.
        print(f"\n--- Pillow Smoke Test: FAILED ---", file=sys.stderr)
        print(f"Error during smoke test: {type(e).__name__} - {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run_pillow_smoke_test()