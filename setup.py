#!/usr/bin/env python3
"""
Setup script for Furniture Project Logistics Dashboard
"""

import subprocess
import sys
import os

def install_requirements():
    """Install required packages"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)

def run_app():
    """Run the Streamlit application"""
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "src/app.py"])
    except KeyboardInterrupt:
        print("\n👋 Application stopped")
    except Exception as e:
        print(f"❌ Error running application: {e}")

if __name__ == "__main__":
    print("🚚 Furniture Project Logistics Dashboard Setup")
    print("=" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        install_requirements()
    elif len(sys.argv) > 1 and sys.argv[1] == "run":
        run_app()
    else:
        print("Usage:")
        print("  python setup.py install  # Install dependencies")
        print("  python setup.py run      # Run the application")
        print("\nOr use directly:")
        print("  pip install -r requirements.txt")
        print("  streamlit run src/app.py")