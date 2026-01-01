
import sys
import os
import traceback

# Add /app to path (Docker container path)
sys.path.insert(0, "/app")

print("Attempting to import main...")
try:
    from main import app
    print("Successfully imported main!")
except Exception as e:
    print(f"Failed to import main: {e}")
    traceback.print_exc()

print("\nAttempting to import shared.models...")
try:
    import shared.models
    print("Successfully imported shared.models!")
except Exception as e:
    print(f"Failed to import shared.models: {e}")
    traceback.print_exc()
