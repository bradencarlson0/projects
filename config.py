"""
Configuration file for Redfin CMA Tool
=====================================
Customize these settings to modify app behavior without changing the main code.
"""

import os
from dataclasses import dataclass
from typing import List, Tuple

@dataclass(frozen=True)
class AppConfig:
    """Main application configuration."""
    
    # App Information
    TITLE: str = "🏡 Land-Acquisition CMA Tool - Pro v4.0"
    PAGE_ICON: str = "🏡"
    LAYOUT: str = "wide"
    
    # Colors and Styling
    PRIMARY_COLOR: str = "#007acc"
    ACCENT_COLOR: str = "#ff9800"
    SUCCESS_COLOR: str = "#28a745"
    WARNING_COLOR: str = "#ffc107"
    ERROR_COLOR: str = "#dc3545"
    
    # Performance Settings
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
    CHUNK_SIZE: int = 10000
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour default
    
    # Map Configuration
    DEFAULT_CENTER: List[float] = [
        float(os.getenv("DEFAULT_LAT", "32.7767")),  # Dallas, TX
        float(os.getenv("DEFAULT_LON", "-96.7970"))
    ]
    DEFAULT_ZOOM: int = 11
    
    # Clustering Parameters
    DBSCAN_EPS: float = 0.009
    DBSCAN_MIN_SAMPLES: int = 2
    
    # Data Processing
    OUTLIER_THRESHOLD: float = 0.99  # 99th percentile for outlier removal
    
    # Map Tile Layers
    TILE_LAYERS: List[dict] = None
    
    def __post_init__(self):
        if self.TILE_LAYERS is None:
            object.__setattr__(self, 'TILE_LAYERS', [
                {
                    "name": "CartoDB Positron",
                    "tiles": "cartodbpositron",
                    "attr": "CartoDB",
                    "default": True
                },
                {
                    "name": "Google Hybrid",
                    "tiles": "https://mt1.google.com/vt/lyrs=y,h&x={x}&y={y}&z={z}",
                    "attr": "Google",
                    "default": False
                },
                {
                    "name": "Google Satellite",
                    "tiles": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
                    "attr": "Google",
                    "default": False
                },
                {
                    "name": "OpenStreetMap",
                    "tiles": "OpenStreetMap",
                    "attr": "OpenStreetMap",
                    "default": False
                }
            ])

@dataclass(frozen=True)
class LotBandConfig:
    """Configuration for lot size bands."""
    
    # Lot size bands in square feet
    BANDS: List[Tuple[float, float, str]] = None
    
    def __post_init__(self):
        if self.BANDS is None:
            object.__setattr__(self, 'BANDS', [
                (0, 3300, "Sub-30'"),
                (3300, 4500, "30'-35'"),
                (4500, 5700, "40'-45'"),
                (5700, 6800, "50'-55'"),
                (6800, 8000, "60'-65'"),
                (8000, 12000, "70'-100'"),
                (12000, float('inf'), "100'+")
            ])
    
    @property
    def bins(self) -> List[float]:
        """Get bin edges for pandas.cut()."""
        bins = [band[0] for band in self.BANDS]
        bins.append(float('inf'))  # Add upper bound
        return bins
    
    @property
    def labels(self) -> List[str]:
        """Get labels for pandas.cut()."""
        return [band[2] for band in self.BANDS]

@dataclass(frozen=True)
class PriceColorConfig:
    """Configuration for price-based marker colors."""
    
    RANGES: List[Tuple[float, str]] = None
    
    def __post_init__(self):
        if self.RANGES is None:
            object.__setattr__(self, 'RANGES', [
                (200000, "green"),    # Under $200k
                (400000, "blue"),     # $200k - $400k
                (600000, "orange"),   # $400k - $600k
                (float('inf'), "red") # Over $600k
            ])
    
    def get_color(self, price: float) -> str:
        """Get color for a given price."""
        for threshold, color in self.RANGES:
            if price < threshold:
                return color
        return "red"  # Fallback

@dataclass(frozen=True)
class ColumnMappingConfig:
    """Configuration for column name mappings."""
    
    # Standard field names
    LAT: str = "LATITUDE"
    LON: str = "LONGITUDE"
    PRICE: str = "PRICE"
    SQFT: str = "SQUARE_FEET"
    BEDS: str = "BEDS"
    BATHS: str = "BATHS"
    LOT: str = "LOT_SIZE"
    ADDRESS: str = "ADDRESS"
    DOM: str = "DAYS_ON_MARKET"
    URL: str = "URL"
    UID: str = "UID"
    LOCATION: str = "LOCATION"
    COMMUNITY: str = "COMMUNITY"
    PRICE_PER_SQFT: str = "PRICE_PER_SQFT"
    LOT_BAND: str = "LOT_BAND"
    SCHOOL_DISTRICT: str = "SCHOOL_DISTRICT"
    
    # Column aliases mapping
    ALIASES: dict = None
    
    def __post_init__(self):
        if self.ALIASES is None:
            object.__setattr__(self, 'ALIASES', {
                # Coordinates
                "LATITUDE": self.LAT, "LAT": self.LAT, "LAT.": self.LAT,
                "LONGITUDE": self.LON, "LON": self.LON, "LONG": self.LON, "LONG.": self.LON,
                
                # Property details
                "PRICE": self.PRICE,
                "SQFT": self.SQFT, "SQ.FT.": self.SQFT, "SQUARE FEET": self.SQFT,
                "BEDS": self.BEDS, "BEDROOMS": self.BEDS,
                "BATHS": self.BATHS, "BATHROOMS": self.BATHS,
                "LOT SIZE": self.LOT, "LOT SF": self.LOT, "LOT SQFT": self.LOT,
                "LOT SQ FT": self.LOT, "LOT_SIZE": self.LOT,
                
                # Other fields
                "ADDRESS": self.ADDRESS, "ADDR": self.ADDRESS,
                "DOM": self.DOM, "DAYS ON MARKET": self.DOM,
                "URL": self.URL, "LINK": self.URL,
                "LOCATION": self.LOCATION, "SUBDIVISION": self.LOCATION,
            })

@dataclass(frozen=True)
class UIConfig:
    """UI-specific configuration."""
    
    # Sidebar settings
    SIDEBAR_INITIAL_STATE: str = "expanded"
    
    # Filter settings
    PRICE_STEP: int = 1000
    SQFT_STEP: int = 50
    LOT_STEP: int = 100
    
    # Chart settings
    HISTOGRAM_BINS: int = 30
    SCATTER_SIZE_MAX: int = 40
    MAP_HEIGHT: int = 600
    CHART_HEIGHT: int = 500
    
    # Data editor settings
    MAX_ROWS_DISPLAY: int = 1000
    PREVIEW_ROWS: int = 10
    
    # Performance monitoring
    SHOW_PERFORMANCE_BY_DEFAULT: bool = False
    
    # Export settings
    DEFAULT_CSV_FILENAME: str = "property_analysis.csv"
    DEFAULT_JSON_FILENAME: str = "property_analysis.json"

# Create global config instances
app_config = AppConfig()
lot_config = LotBandConfig()
price_color_config = PriceColorConfig()
column_config = ColumnMappingConfig()
ui_config = UIConfig()

# Environment-specific overrides
def load_env_config():
    """Load configuration from environment variables."""
    # This function can be extended to load from config files,
    # environment variables, or other sources
    pass

# Load any environment-specific configuration
load_env_config()