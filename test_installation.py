#!/usr/bin/env python3
"""
Installation Test Script for Redfin CMA Tool
============================================
Run this script to verify all dependencies are installed correctly.

Usage:
    python test_installation.py
"""

import sys
import importlib
import traceback
from typing import List, Tuple

def test_import(module_name: str, package_name: str = None) -> Tuple[bool, str]:
    """Test if a module can be imported."""
    try:
        importlib.import_module(module_name)
        return True, f"✅ {package_name or module_name}"
    except ImportError as e:
        return False, f"❌ {package_name or module_name}: {str(e)}"
    except Exception as e:
        return False, f"⚠️  {package_name or module_name}: {str(e)}"

def check_python_version() -> Tuple[bool, str]:
    """Check if Python version meets requirements."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        return True, f"✅ Python {version.major}.{version.minor}.{version.micro}"
    else:
        return False, f"❌ Python {version.major}.{version.minor}.{version.micro} (requires 3.8+)"

def main():
    """Run all installation tests."""
    print("🏡 Redfin CMA Tool - Installation Test")
    print("=" * 50)
    
    # Test Python version
    version_ok, version_msg = check_python_version()
    print(f"Python Version: {version_msg}")
    
    if not version_ok:
        print("\n❌ Python version check failed. Please upgrade to Python 3.8 or higher.")
        return False
    
    print("\nTesting Dependencies:")
    print("-" * 30)
    
    # Core dependencies
    required_modules = [
        ("streamlit", "Streamlit"),
        ("pandas", "Pandas"),
        ("numpy", "NumPy"),
        ("geopandas", "GeoPandas"),
        ("shapely", "Shapely"),
        ("sklearn", "Scikit-learn"),
        ("plotly", "Plotly"),
        ("folium", "Folium"),
        ("streamlit_folium", "Streamlit-Folium"),
    ]
    
    # Optional dependencies
    optional_modules = [
        ("pyarrow", "PyArrow"),
        ("fastparquet", "FastParquet"),
        ("openpyxl", "OpenPyXL"),
        ("xlsxwriter", "XlsxWriter"),
    ]
    
    all_passed = True
    failed_modules = []
    
    # Test required modules
    print("\nRequired Dependencies:")
    for module, name in required_modules:
        success, message = test_import(module, name)
        print(f"  {message}")
        if not success:
            all_passed = False
            failed_modules.append(name)
    
    # Test optional modules
    print("\nOptional Dependencies:")
    for module, name in optional_modules:
        success, message = test_import(module, name)
        print(f"  {message}")
    
    # Test app imports
    print("\nApplication Modules:")
    try:
        # Test if we can import key parts of the app
        import tempfile
        import zipfile
        import logging
        import time
        import json
        import gc
        from pathlib import Path
        from contextlib import contextmanager
        from dataclasses import dataclass
        print("  ✅ Standard library modules")
        
        # Test GeoPandas functionality
        import geopandas as gpd
        test_gdf = gpd.GeoDataFrame()
        print("  ✅ GeoPandas functionality")
        
        # Test Plotly functionality
        import plotly.express as px
        print("  ✅ Plotly functionality")
        
        # Test Folium functionality
        import folium
        test_map = folium.Map()
        print("  ✅ Folium functionality")
        
    except Exception as e:
        print(f"  ❌ Application modules: {str(e)}")
        all_passed = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! The application should work correctly.")
        print("\nTo start the application, run:")
        print("    streamlit run redfinwebapp_optimized.py")
    else:
        print("❌ Some tests failed. Please install missing dependencies:")
        print("    pip install -r requirements.txt")
        if failed_modules:
            print(f"\nFailed modules: {', '.join(failed_modules)}")
    
    print("\nFor more information, see README.md")
    return all_passed

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Test script failed with error: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        sys.exit(1)