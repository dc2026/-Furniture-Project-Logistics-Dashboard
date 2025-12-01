# Installation Guide

## Quick Start

### Option 1: Using Setup Script
```bash
python setup.py install  # Install dependencies
python setup.py run      # Run the application
```

### Option 2: Manual Installation
```bash
pip install -r requirements.txt
streamlit run src/app.py
```

## Requirements

- Python 3.7+
- Internet connection for Google Maps integration
- Web browser for Streamlit interface

## Dependencies

The application requires these Python packages:
- `streamlit` - Web application framework
- `pandas` - Data manipulation and analysis
- `geopy` - Geocoding library
- `folium` - Interactive mapping
- `streamlit-folium` - Folium integration for Streamlit
- `openpyxl` - Excel file support

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   streamlit run src/app.py --server.port 8502
   ```

2. **Module not found errors**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

3. **Permission errors on macOS/Linux**
   ```bash
   python3 -m pip install --user -r requirements.txt
   ```

### System-Specific Notes

#### Windows
- Use `python` instead of `python3`
- May need to install Visual C++ Build Tools for some packages

#### macOS
- Use `python3` and `pip3` if you have multiple Python versions
- May need to install Xcode Command Line Tools

#### Linux
- Install `python3-pip` if pip is not available
- May need `python3-dev` for some packages