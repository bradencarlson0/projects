# 🏡 Redfin CMA Tool - Pro v4.0 (Optimized)

A professional-grade Comparative Market Analysis (CMA) tool for real estate land acquisition, built with Streamlit. This optimized version provides enhanced performance, better error handling, and improved user experience for analyzing property data.

## ✨ Key Improvements from v3.32

### 🚀 Performance Optimizations
- **Better Memory Management**: Intelligent garbage collection and memory monitoring
- **Enhanced Caching**: Improved data caching with TTL (Time To Live) controls
- **Optimized Data Processing**: Chunked processing for large datasets
- **Performance Timing**: Built-in operation timing for monitoring bottlenecks

### 🛡️ Enhanced Error Handling
- **Robust File Validation**: File size checks and format validation
- **Graceful Failures**: Better error messages and recovery mechanisms
- **Logging System**: Comprehensive logging for debugging and monitoring
- **Input Sanitization**: Improved data cleaning and validation

### 🎨 Improved User Experience
- **Modern UI Design**: Enhanced styling with custom CSS
- **Progress Indicators**: Loading spinners and progress feedback
- **Better Navigation**: Intuitive tab organization and flow
- **Responsive Design**: Optimized for different screen sizes

### 🏗️ Code Architecture Improvements
- **Type Hints**: Full type annotation for better code reliability
- **Class-Based Design**: Better separation of concerns with dedicated classes
- **Configuration Management**: Centralized configuration with dataclasses
- **Modular Structure**: Clean separation between data processing, UI, and analysis

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation

1. **Clone or download the files:**
   ```bash
   # If you have git
   git clone <repository-url>
   cd redfin-cma-tool

   # Or just download the files to your project directory
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   streamlit run redfinwebapp_optimized.py
   ```

4. **Open your browser:**
   - The app will automatically open at `http://localhost:8501`
   - If it doesn't open automatically, navigate to that URL

## 📊 Features

### 🗂️ Data Upload & Processing
- **CSV Support**: Upload multiple Redfin CSV files simultaneously
- **Spatial Layers**: Support for KML, KMZ, GeoJSON, GPKG, and CSV spatial files
- **Smart Column Mapping**: Automatically maps common column aliases to standard fields
- **Data Validation**: Robust validation and cleaning of uploaded data

### 🗺️ Interactive Mapping
- **Multiple Tile Layers**: Google Hybrid, Google Satellite, and CartoDB Positron
- **Property Markers**: Color-coded markers based on price ranges
- **Drawing Tools**: Draw custom areas for spatial filtering
- **Layer Management**: Toggle visibility of different spatial layers

### 🔍 Advanced Filtering
- **Range Filters**: Price, square footage, and lot size sliders
- **Spatial Filtering**: Filter properties within drawn boundaries
- **Dynamic Updates**: Real-time filtering with instant feedback

### 📈 Comprehensive Analysis
- **Community Analysis**: Group properties by geographic clusters
- **Market Overview**: Price distributions and trend analysis
- **Lot Analysis**: Size band categorization and analysis
- **School District Analysis**: Spatial join with district boundaries
- **Bedroom/Bathroom Analysis**: Property composition analysis

### 📥 Export Capabilities
- **CSV Export**: Download filtered and analyzed data
- **JSON Export**: Export data in JSON format for further processing
- **Data Preview**: Preview data before download

## 📋 Expected Data Format

### Required CSV Columns
- `LATITUDE` or `LAT` - Property latitude coordinates
- `LONGITUDE`, `LON`, or `LONG` - Property longitude coordinates  
- `PRICE` - Sale price of the property

### Optional but Recommended Columns
- `ADDRESS` - Property street address
- `SQUARE FEET`, `SQFT`, or `SQ.FT.` - Living area in square feet
- `LOT SIZE`, `LOT SF`, or `LOT SQFT` - Lot size in square feet
- `BEDS` or `BEDROOMS` - Number of bedrooms
- `BATHS` or `BATHROOMS` - Number of bathrooms
- `LOCATION` or `SUBDIVISION` - Community or subdivision name
- `DAYS ON MARKET` or `DOM` - Days the property was listed
- `URL` - Link to the property listing

## 🏗️ Architecture Overview

### Core Components

#### Configuration Classes
- `Config`: Application-wide configuration and constants
- `FieldNames`: Standardized field name mappings
- `AppState`: Session state management

#### Data Processing
- `DataLoader`: Handles CSV and spatial file loading
- `CommunityProcessor`: Geographic clustering and community detection
- `PropertyAnalyzer`: Property data enrichment and analysis

#### UI Components
- `FilterComponents`: Reusable filter widgets
- `MapComponents`: Map creation and marker management

### Key Design Patterns
- **Separation of Concerns**: Clear separation between data, logic, and presentation
- **Caching Strategy**: Intelligent caching with TTL for performance
- **Error Boundaries**: Graceful error handling at each layer
- **Modular UI**: Reusable components for consistent interface

## ⚡ Performance Features

### Memory Management
- **Garbage Collection**: Automatic memory cleanup
- **Memory Monitoring**: Real-time memory usage tracking
- **Data Chunking**: Process large datasets in manageable chunks

### Caching Strategy
- **Data Caching**: Cache loaded files with TTL
- **Operation Timing**: Monitor and log operation performance
- **Smart Invalidation**: Intelligent cache invalidation

### Optimization Techniques
- **Lazy Loading**: Load data only when needed
- **Vectorized Operations**: Use pandas/numpy optimized operations
- **Spatial Indexing**: Efficient spatial operations with GeoPandas

## 🐛 Troubleshooting

### Common Issues

**File Upload Errors:**
- Ensure files are under 100MB
- Check that CSV files have required latitude/longitude columns
- Verify coordinate values are valid (latitude: -90 to 90, longitude: -180 to 180)

**Memory Issues:**
- Use the "Clean Memory" button in performance metrics
- Process smaller files or use data filtering to reduce memory usage
- Close other applications to free up system memory

**Map Not Loading:**
- Check internet connection for map tiles
- Ensure coordinates are in the correct format
- Try refreshing the page

**Performance Issues:**
- Enable performance metrics to identify bottlenecks
- Consider reducing the number of properties or spatial layers
- Use filtering to work with smaller datasets

### Getting Help

1. **Check the Error Details**: Use the error details expander for specific error information
2. **Enable Logging**: Check the console for detailed logging information
3. **Performance Metrics**: Use the performance monitoring to identify issues

## 🔧 Configuration

### Environment Variables
You can set these environment variables to customize behavior:

```bash
# Maximum file size in MB (default: 100)
STREAMLIT_MAX_FILE_SIZE=100

# Cache TTL in seconds (default: 3600)
CACHE_TTL=3600

# Default map center (default: Dallas, TX)
DEFAULT_LAT=32.7767
DEFAULT_LON=-96.7970
```

### Customization
- **Colors**: Modify the `Config` class to change color schemes
- **Map Settings**: Adjust default center and zoom levels
- **Data Processing**: Modify clustering parameters in `Config`

## 📈 Version History

### v4.0 (Optimized) - Current
- Complete architecture overhaul
- Enhanced performance and memory management
- Improved error handling and logging
- Better user experience and modern UI
- Type hints and documentation
- Modular class-based design

### v3.32 (Original)
- Basic CMA functionality
- File upload and mapping
- Simple analysis and export

## 🤝 Contributing

To contribute to this project:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/) for the web framework
- Uses [Folium](https://folium.readthedocs.io/) for interactive mapping
- Powered by [GeoPandas](https://geopandas.org/) for spatial data processing
- Visualization with [Plotly](https://plotly.com/python/)

---

For more information or support, please open an issue in the repository.