"""
Simple test script to verify the refactored EEG Dashboard works correctly.
"""

import sys
import os

def test_imports():
    """Test that all modules can be imported without errors."""
    try:
        # Test core imports
        from models import EEGData, DisplaySettings, AnnotationCollection, Annotation, SelectionState
        print("✓ Models imported successfully")
        
        from file_handlers import EEGFileHandler, AnnotationFileHandler, FilterHandler
        print("✓ File handlers imported successfully")
        
        from plotting import EEGPlotter
        print("✓ Plotting module imported successfully")
        
        from ui_components import ControlPanel, AnnotationPanel, ChannelSettingsDialog
        print("✓ UI components imported successfully")
        
        from annotation_system import AnnotationManager, AnnotationValidator, AnnotationFormatter
        print("✓ Annotation system imported successfully")
        
        from main_dashboard import EEGDashboard
        print("✓ Main dashboard imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_data_models():
    """Test data model creation and functionality."""
    try:
        from models import EEGData, DisplaySettings, Annotation, AnnotationCollection, SelectionState
        
        # Test DisplaySettings
        settings = DisplaySettings(time_scale=10.0, amplitude_scale=2.0)
        assert settings.time_scale == 10.0
        assert settings.amplitude_scale == 2.0
        print("✓ DisplaySettings works correctly")
        
        # Test Annotation
        annotation = Annotation.create("Test annotation", 1.0, 2.0)
        assert annotation.text == "Test annotation"
        assert annotation.start_time == 1.0
        assert annotation.end_time == 2.0
        assert annotation.duration == 1.0
        print("✓ Annotation creation works correctly")
        
        # Test SelectionState
        selection = SelectionState()
        assert not selection.has_selection
        selection.start_time = 1.0
        selection.end_time = 2.0
        assert selection.has_selection
        print("✓ SelectionState works correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Data model test failed: {e}")
        return False

def test_annotation_manager():
    """Test annotation manager functionality."""
    try:
        from annotation_system import AnnotationManager
        from models import AnnotationCollection
        
        # Create annotation manager
        manager = AnnotationManager()
        
        # Test selection state
        assert not manager.has_selection()
        start_time, end_time = manager.get_selection_info()
        assert start_time is None
        assert end_time is None
        
        # Test clear selection
        manager.clear_selection()
        assert not manager.has_selection()
        
        print("✓ AnnotationManager works correctly")
        return True
        
    except Exception as e:
        print(f"✗ Annotation manager test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing refactored EEG Dashboard...")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Data Models Test", test_data_models),
        ("Annotation Manager Test", test_annotation_manager),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name}...")
        if test_func():
            passed += 1
            print(f"✓ {test_name} PASSED")
        else:
            print(f"✗ {test_name} FAILED")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The refactored code is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
