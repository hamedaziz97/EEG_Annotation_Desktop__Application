# EEG Dashboard - Refactored Architecture

This is a refactored version of the EEG Dashboard application, split into multiple, more manageable modules for better maintainability and organization.

## Architecture Overview

The application has been refactored into the following modules:

### Core Modules

1. **`models.py`** - Data models and configuration classes
   - `EEGData`: Container for EEG data and metadata
   - `Annotation`: Single annotation entry
   - `AnnotationCollection`: Collection of annotations with metadata
   - `DisplaySettings`: Display and visualization settings
   - `SelectionState`: State for annotation selection

2. **`file_handlers.py`** - File I/O operations
   - `EEGFileHandler`: Handles loading EDF/BDF files
   - `AnnotationFileHandler`: Handles saving/loading annotations
   - `FilterHandler`: Applies filters to EEG data

3. **`plotting.py`** - Visualization and plotting
   - `EEGPlotter`: Handles EEG data plotting and visualization
   - Mouse event handling for annotation selection
   - Plot customization and styling

4. **`ui_components.py`** - User interface components
   - `ChannelSettingsDialog`: Channel selection dialog
   - `ControlPanel`: Display settings and navigation controls
   - `AnnotationPanel`: Annotation controls and display

5. **`annotation_system.py`** - Annotation management
   - `AnnotationManager`: Manages annotation selection and operations
   - `AnnotationValidator`: Validates annotation data
   - `AnnotationFormatter`: Formats annotation data for display

6. **`main_dashboard.py`** - Main application orchestration
   - `EEGDashboard`: Main dashboard class that coordinates all components
   - Event handling and component integration

7. **`main.py`** - Application entry point
   - Simple entry point to run the application

## Benefits of Refactoring

### Improved Maintainability
- **Separation of Concerns**: Each module has a single, well-defined responsibility
- **Modular Design**: Components can be modified independently
- **Clear Interfaces**: Well-defined APIs between modules

### Better Code Organization
- **Logical Grouping**: Related functionality is grouped together
- **Reduced Complexity**: Each file is much smaller and easier to understand
- **Clear Dependencies**: Import structure shows module relationships

### Enhanced Testability
- **Unit Testing**: Each module can be tested independently
- **Mocking**: Dependencies can be easily mocked for testing
- **Isolated Components**: Components can be tested in isolation

### Easier Development
- **Parallel Development**: Multiple developers can work on different modules
- **Focused Changes**: Changes are localized to specific modules
- **Code Reuse**: Components can be reused in other projects

## File Structure

```
exploringResults/
├── main.py                 # Application entry point
├── main_dashboard.py       # Main dashboard orchestration
├── models.py              # Data models and configuration
├── file_handlers.py       # File I/O operations
├── plotting.py            # Visualization and plotting
├── ui_components.py       # User interface components
├── annotation_system.py   # Annotation management
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── dashboard.py          # Original monolithic file (kept for reference)
```

## Usage

### Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Key Features

- **EEG File Loading**: Support for EDF and BDF formats
- **Interactive Visualization**: Click and drag to select time ranges
- **Annotation System**: Add, save, and load annotations
- **Channel Management**: Select which channels to display
- **Filtering**: Apply lowpass and highpass filters
- **Navigation**: Navigate through EEG data in time windows

## Module Dependencies

```
main.py
└── main_dashboard.py
    ├── models.py
    ├── file_handlers.py
    ├── plotting.py
    ├── ui_components.py
    └── annotation_system.py
```

## Migration from Original

The refactored version maintains full compatibility with the original functionality while providing:

- **Same User Interface**: Identical look and feel
- **Same Features**: All original features preserved
- **Better Performance**: More efficient code organization
- **Easier Maintenance**: Modular structure for easier updates

## Development Guidelines

When modifying the code:

1. **Keep modules focused**: Each module should have a single responsibility
2. **Maintain interfaces**: Don't break the APIs between modules
3. **Add tests**: Write unit tests for new functionality
4. **Document changes**: Update this README when adding new modules
5. **Follow naming conventions**: Use clear, descriptive names for classes and functions
