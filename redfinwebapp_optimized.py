"""
Redfin Web App - Land-Acquisition CMA Tool (Optimized v4.0)
===========================================================
Enhanced version with improved performance, error handling, and user experience.

Features:
- Better caching and memory management
- Enhanced error handling and validation
- Improved UI/UX with progress indicators
- Optimized data processing pipeline
- Better separation of concerns
- Type hints and documentation
- Performance monitoring
- Advanced filtering and analysis

Usage: streamlit run redfinwebapp_optimized.py
"""

from __future__ import annotations

import gc
import json
import logging
import os
import re
import tempfile
import time
import traceback
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from folium import Map, LayerControl, TileLayer
from folium.features import GeoJsonTooltip
from folium.plugins import Draw, MarkerCluster, HeatMap
from shapely.geometry import Point, shape
from sklearn.cluster import DBSCAN
from streamlit_folium import st_folium

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========================================================================
# CONFIGURATION AND CONSTANTS
# ========================================================================

@dataclass(frozen=True)
class Config:
    """Application configuration constants."""
    APP_TITLE = "🏡 Land-Acquisition CMA Tool - Pro v4.0"
    PAGE_ICON = "🏡"
    LAYOUT = "wide"
    PRIMARY_COLOR = "#007acc"
    ACCENT_COLOR = "#ff9800"
    SUCCESS_COLOR = "#28a745"
    WARNING_COLOR = "#ffc107"
    ERROR_COLOR = "#dc3545"
    
    # Data processing
    MAX_FILE_SIZE_MB = 100
    CHUNK_SIZE = 10000
    CACHE_TTL = 3600  # 1 hour
    
    # Clustering parameters
    DBSCAN_EPS = 0.009
    DBSCAN_MIN_SAMPLES = 2
    
    # Map settings
    DEFAULT_CENTER = [32.7767, -96.7970]  # Dallas, TX
    DEFAULT_ZOOM = 11

@dataclass(frozen=True)
class FieldNames:
    """Standardized field names for property data."""
    LOCATION = "LOCATION"
    COMMUNITY = "COMMUNITY"
    PRICE = "PRICE"
    SQFT = "SQUARE_FEET"
    BEDS = "BEDS"
    BATHS = "BATHS"
    LOT = "LOT_SIZE"
    LAT = "LATITUDE"
    LON = "LONGITUDE"
    ADDRESS = "ADDRESS"
    DOM = "DAYS_ON_MARKET"
    URL = "URL"
    UID = "UID"
    PRICE_PER_SQFT = "PRICE_PER_SQFT"
    LOT_BAND = "LOT_BAND"
    SCHOOL_DISTRICT = "SCHOOL_DISTRICT"

@dataclass
class AppState:
    """Application state management."""
    sales_layers: List[Dict[str, Any]] = field(default_factory=list)
    isd_layers: List[Dict[str, Any]] = field(default_factory=list)
    spec_layers: List[Dict[str, Any]] = field(default_factory=list)
    misc_layers: List[Dict[str, Any]] = field(default_factory=list)
    processed_files: set = field(default_factory=set)
    excluded_uids: set = field(default_factory=set)
    active_geojson: Optional[Dict] = None
    drawn_geojson: Optional[Dict] = None
    filter_cache: Dict[str, Any] = field(default_factory=dict)

# Initialize global instances
config = Config()
fields = FieldNames()

# ========================================================================
# UTILITY FUNCTIONS
# ========================================================================

def safe_rerun() -> None:
    """Version-safe Streamlit rerun with error handling."""
    try:
        if hasattr(st, "rerun"):
            st.rerun()
        elif hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
        else:
            # Fallback for older versions
            raise st.script_runner.RerunException(st.script_request_queue.RerunData())
    except Exception as e:
        logger.warning(f"Rerun failed: {e}")

@contextmanager
def performance_timer(operation_name: str):
    """Context manager for timing operations."""
    start_time = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start_time
        logger.info(f"{operation_name} completed in {elapsed:.2f} seconds")

def format_currency(value: Union[int, float]) -> str:
    """Format currency values with proper handling of NaN."""
    if pd.isna(value):
        return "N/A"
    return f"${value:,.0f}"

def format_currency_precise(value: Union[int, float]) -> str:
    """Format currency values with 2 decimal places."""
    if pd.isna(value):
        return "N/A"
    return f"${value:,.2f}"

def validate_file_size(file_obj) -> bool:
    """Validate uploaded file size."""
    if hasattr(file_obj, 'size'):
        size_mb = file_obj.size / (1024 * 1024)
        if size_mb > config.MAX_FILE_SIZE_MB:
            st.error(f"File too large: {size_mb:.1f}MB (max: {config.MAX_FILE_SIZE_MB}MB)")
            return False
    return True

def clean_memory():
    """Force garbage collection to free memory."""
    gc.collect()

# ========================================================================
# DATA PROCESSING CLASSES
# ========================================================================

class CommunityProcessor:
    """Handles community name cleaning and clustering."""
    
    @staticmethod
    def clean_community_name(raw_name: Optional[str]) -> str:
        """Clean and standardize community names."""
        if not isinstance(raw_name, str) or not raw_name.strip():
            return "UNKNOWN"
        
        # Convert to uppercase and remove special characters
        cleaned = re.sub(r"[^A-Z0-9 ]+", " ", raw_name.upper())
        
        # Remove common suffixes and prefixes
        patterns_to_remove = [
            r"\b(PHASE|PH|ESTATES?|VILLAGE|ADDITION|ADD|SEC|SECTION)\b",
            r"\b(CROSSING|PARK|MEADOWS?|CREEK|RANCH|EST|AT|THE)\b",
            r"\b(SUBDIVISION|SUB|COMMUNITY|COMM)\b",
            r"\s+[A-Z0-9]{1,3}$"  # Remove short suffixes
        ]
        
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, "", cleaned)
        
        # Clean up whitespace
        cleaned = " ".join(cleaned.split())
        
        return cleaned if cleaned else "UNKNOWN"
    
    @staticmethod
    def cluster_communities(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Group properties by geographic clusters and assign community names."""
        if gdf.empty:
            return gdf
        
        gdf = gdf.copy()
        
        # Ensure location column exists
        if fields.LOCATION not in gdf.columns:
            gdf[fields.LOCATION] = "UNKNOWN"
        
        # Clean community names
        gdf["_clean_community"] = gdf[fields.LOCATION].apply(
            CommunityProcessor.clean_community_name
        )
        
        # Perform geographic clustering
        if len(gdf) > 1:
            coords = gdf[[fields.LAT, fields.LON]].values
            
            try:
                clustering = DBSCAN(
                    eps=config.DBSCAN_EPS,
                    min_samples=config.DBSCAN_MIN_SAMPLES
                ).fit(coords)
                
                gdf["_cluster"] = clustering.labels_
                
                # Assign most common name to each cluster
                clustered_names = gdf[gdf._cluster != -1].groupby("_cluster")["_clean_community"].agg(
                    lambda x: x.mode()[0] if not x.mode().empty else "UNKNOWN"
                )
                
                gdf[fields.COMMUNITY] = gdf._cluster.map(clustered_names).fillna(
                    gdf._clean_community
                )
            except Exception as e:
                logger.warning(f"Clustering failed: {e}")
                gdf[fields.COMMUNITY] = gdf._clean_community
        else:
            gdf[fields.COMMUNITY] = gdf._clean_community
        
        # Clean up temporary columns
        gdf = gdf.drop(columns=["_clean_community", "_cluster"], errors="ignore")
        
        return gdf

class DataLoader:
    """Handles loading and processing of various data formats."""
    
    @staticmethod
    @st.cache_data(show_spinner="Loading CSV data...", ttl=config.CACHE_TTL)
    def load_csv(file_content: bytes, filename: str) -> gpd.GeoDataFrame:
        """Load and process CSV files with property data."""
        try:
            with performance_timer(f"Loading CSV: {filename}"):
                # Read CSV with error handling
                df = pd.read_csv(
                    pd.io.common.BytesIO(file_content),
                    on_bad_lines="warn",
                    encoding="utf-8"
                ).reset_index()
                
                if df.empty:
                    st.warning(f"Empty file: {filename}")
                    return gpd.GeoDataFrame()
                
                # Add unique identifier
                df = df.rename(columns={"index": fields.UID})
                df[fields.UID] = f"{filename}_" + df[fields.UID].astype(str)
                
                # Standardize column names
                df.columns = df.columns.str.strip().str.upper()
                
                # Map common column aliases to standard names
                column_mapping = DataLoader._get_column_mapping()
                df = df.rename(columns=column_mapping)
                
                # Validate required columns
                if not DataLoader._validate_required_columns(df, filename):
                    return gpd.GeoDataFrame()
                
                # Convert numeric columns
                df = DataLoader._convert_numeric_columns(df)
                
                # Remove invalid rows
                df = DataLoader._clean_data(df, filename)
                
                if df.empty:
                    return gpd.GeoDataFrame()
                
                # Create GeoDataFrame
                gdf = gpd.GeoDataFrame(
                    df,
                    geometry=gpd.points_from_xy(df[fields.LON], df[fields.LAT]),
                    crs="EPSG:4326"
                )
                
                # Process communities
                gdf = CommunityProcessor.cluster_communities(gdf)
                
                logger.info(f"Successfully loaded {len(gdf)} properties from {filename}")
                return gdf
                
        except Exception as e:
            st.error(f"Error loading {filename}: {str(e)}")
            logger.error(f"CSV loading error: {e}", exc_info=True)
            return gpd.GeoDataFrame()
    
    @staticmethod
    def _get_column_mapping() -> Dict[str, str]:
        """Get mapping of common column aliases to standard field names."""
        return {
            # Coordinates
            "LATITUDE": fields.LAT, "LAT": fields.LAT, "LAT.": fields.LAT,
            "LONGITUDE": fields.LON, "LON": fields.LON, "LONG": fields.LON, "LONG.": fields.LON,
            
            # Property details
            "PRICE": fields.PRICE,
            "SQFT": fields.SQFT, "SQ.FT.": fields.SQFT, "SQUARE FEET": fields.SQFT,
            "BEDS": fields.BEDS, "BEDROOMS": fields.BEDS,
            "BATHS": fields.BATHS, "BATHROOMS": fields.BATHS,
            "LOT SIZE": fields.LOT, "LOT SF": fields.LOT, "LOT SQFT": fields.LOT,
            "LOT SQ FT": fields.LOT, "LOT_SIZE": fields.LOT,
            
            # Other fields
            "ADDRESS": fields.ADDRESS, "ADDR": fields.ADDRESS,
            "DOM": fields.DOM, "DAYS ON MARKET": fields.DOM,
            "URL": fields.URL, "LINK": fields.URL,
            "LOCATION": fields.LOCATION, "SUBDIVISION": fields.LOCATION,
        }
    
    @staticmethod
    def _validate_required_columns(df: pd.DataFrame, filename: str) -> bool:
        """Validate that required columns are present."""
        required = [fields.LAT, fields.LON]
        missing = [col for col in required if col not in df.columns]
        
        if missing:
            st.error(f"❌ {filename}: Missing required columns: {missing}")
            return False
        return True
    
    @staticmethod
    def _convert_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Convert specified columns to numeric types."""
        numeric_columns = [
            fields.PRICE, fields.SQFT, fields.BEDS, fields.BATHS,
            fields.LAT, fields.LON, fields.DOM, fields.LOT
        ]
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        return df
    
    @staticmethod
    def _clean_data(df: pd.DataFrame, filename: str) -> pd.DataFrame:
        """Remove invalid data rows."""
        initial_count = len(df)
        
        # Remove rows with missing critical data
        df = df.dropna(subset=[fields.PRICE, fields.LAT, fields.LON])
        
        # Remove invalid coordinates
        df = df[
            (df[fields.LAT].between(-90, 90)) &
            (df[fields.LON].between(-180, 180))
        ]
        
        # Remove invalid prices
        df = df[df[fields.PRICE] > 0]
        
        final_count = len(df)
        removed = initial_count - final_count
        
        if removed > 0:
            st.info(f"Removed {removed} invalid rows from {filename}")
        
        return df
    
    @staticmethod
    @st.cache_data(show_spinner="Loading spatial data...", ttl=config.CACHE_TTL)
    def load_spatial_file(file_content: bytes, filename: str) -> gpd.GeoDataFrame:
        """Load spatial files (KML, KMZ, GeoJSON, etc.)."""
        try:
            with performance_timer(f"Loading spatial file: {filename}"):
                file_ext = Path(filename).suffix.lower()
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                    tmp_file.write(file_content)
                    tmp_path = tmp_file.name
                
                try:
                    if file_ext in {".kml", ".kmz"}:
                        gdf = DataLoader._load_kml_kmz(tmp_path, file_ext == ".kmz")
                    elif file_ext in {".geojson", ".json"}:
                        gdf = gpd.read_file(tmp_path)
                    elif file_ext == ".gpkg":
                        gdf = gpd.read_file(tmp_path)
                    elif file_ext == ".csv":
                        gdf = DataLoader._load_csv_spatial(tmp_path)
                    else:
                        st.error(f"Unsupported file format: {file_ext}")
                        return gpd.GeoDataFrame()
                    
                    # Ensure proper CRS
                    if not gdf.empty and gdf.crs:
                        if gdf.crs.to_epsg() != 4326:
                            gdf = gdf.to_crs(epsg=4326)
                    
                    logger.info(f"Loaded spatial file {filename} with {len(gdf)} features")
                    return gdf
                    
                finally:
                    os.unlink(tmp_path)
                    
        except Exception as e:
            st.error(f"Error loading spatial file {filename}: {str(e)}")
            logger.error(f"Spatial file loading error: {e}", exc_info=True)
            return gpd.GeoDataFrame()
    
    @staticmethod
    def _load_kml_kmz(file_path: str, is_kmz: bool) -> gpd.GeoDataFrame:
        """Load KML or KMZ files."""
        if is_kmz:
            with zipfile.ZipFile(file_path) as z:
                kml_files = [name for name in z.namelist() if name.lower().endswith(".kml")]
                if not kml_files:
                    raise ValueError("No KML file found in KMZ archive")
                
                with z.open(kml_files[0]) as kml_file:
                    return gpd.read_file(kml_file, driver="KML")
        else:
            return gpd.read_file(file_path, driver="KML")
    
    @staticmethod
    def _load_csv_spatial(file_path: str) -> gpd.GeoDataFrame:
        """Load CSV file with coordinate columns."""
        df = pd.read_csv(file_path)
        
        # Find coordinate columns
        lat_cols = [col for col in df.columns if re.search(r"lat|y$", col, re.I)]
        lon_cols = [col for col in df.columns if re.search(r"lon|lng|x$", col, re.I)]
        
        if not (lat_cols and lon_cols):
            raise ValueError("No coordinate columns found in CSV")
        
        lat_col, lon_col = lat_cols[0], lon_cols[0]
        
        # Convert to numeric
        df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
        df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
        
        # Remove invalid coordinates
        df = df.dropna(subset=[lat_col, lon_col])
        
        return gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
            crs="EPSG:4326"
        )

class PropertyAnalyzer:
    """Handles property analysis and enrichment."""
    
    @staticmethod
    def assign_lot_bands(df: pd.DataFrame) -> pd.DataFrame:
        """Assign lot size bands to properties."""
        if df.empty or fields.LOT not in df.columns:
            return df.assign(**{fields.LOT_BAND: "N/A"})
        
        # Define lot size bands (in square feet)
        bins = [0, 3300, 4500, 5700, 6800, 8000, 12000, np.inf]
        labels = ["Sub-30'", "30'-35'", "40'-45'", "50'-55'", "60'-65'", "70'-100'", "100'+"]
        
        df[fields.LOT_BAND] = pd.cut(
            df[fields.LOT],
            bins=bins,
            labels=labels,
            right=False
        ).astype(str).replace("nan", "N/A")
        
        return df
    
    @staticmethod
    def calculate_price_per_sqft(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate price per square foot."""
        if df.empty or fields.PRICE not in df.columns or fields.SQFT not in df.columns:
            return df
        
        df[fields.PRICE_PER_SQFT] = df[fields.PRICE] / df[fields.SQFT].replace(0, np.nan)
        return df
    
    @staticmethod
    def assign_school_districts(properties_gdf: gpd.GeoDataFrame, 
                              district_layers: List[Dict]) -> gpd.GeoDataFrame:
        """Assign school districts to properties using spatial joins."""
        if properties_gdf.empty:
            return properties_gdf
        
        gdf = properties_gdf.copy()
        gdf[fields.SCHOOL_DISTRICT] = "N/A"
        
        for layer in district_layers:
            if not layer.get("visible", True):
                continue
            
            try:
                district_gdf = layer["gdf"]
                field_name = layer["field"]
                
                if district_gdf.empty or field_name not in district_gdf.columns:
                    continue
                
                # Perform spatial join
                joined = gpd.sjoin(
                    gdf[[fields.UID, "geometry"]],
                    district_gdf[[field_name, "geometry"]],
                    how="left",
                    predicate="within"
                ).drop_duplicates(subset=[fields.UID])
                
                # Update school district information
                district_map = joined.set_index(fields.UID)[field_name]
                gdf[fields.SCHOOL_DISTRICT] = gdf[fields.UID].map(district_map).fillna(
                    gdf[fields.SCHOOL_DISTRICT]
                )
                
            except Exception as e:
                logger.warning(f"Error in school district assignment: {e}")
                continue
        
        return gdf

# ========================================================================
# UI COMPONENTS
# ========================================================================

class FilterComponents:
    """UI components for filtering data."""
    
    @staticmethod
    def create_range_filter(label: str, key: str, series: pd.Series, 
                          step: Union[int, float], fmt: str) -> None:
        """Create a range filter with slider and display."""
        if series.empty or series.isna().all():
            series = pd.Series([0, 1])
        
        min_val, max_val = float(series.min()), float(series.max())
        if min_val >= max_val:
            max_val = min_val + 1
        
        current_range = st.session_state.get(key, (min_val, max_val))
        
        st.markdown(f"**{label}**")
        new_range = st.slider(
            "",
            min_val, max_val, current_range,
            step=float(step),
            format=fmt,
            key=key,
            label_visibility="collapsed"
        )
        
        st.caption(f"{new_range[0]:,.0f} → {new_range[1]:,.0f}")

class MapComponents:
    """Components for map visualization."""
    
    @staticmethod
    def create_base_map(center: List[float], zoom: int = config.DEFAULT_ZOOM) -> Map:
        """Create base map with multiple tile layers."""
        m = Map(location=center, zoom_start=zoom, tiles="cartodbpositron")
        
        # Add additional tile layers
        TileLayer(
            tiles="https://mt1.google.com/vt/lyrs=y,h&x={x}&y={y}&z={z}",
            name="Google Hybrid",
            attr="Google"
        ).add_to(m)
        
        TileLayer(
            tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
            name="Google Satellite",
            attr="Google"
        ).add_to(m)
        
        return m
    
    @staticmethod
    def add_property_markers(m: Map, gdf: gpd.GeoDataFrame) -> None:
        """Add property markers to map with clustering."""
        if gdf.empty:
            return
        
        marker_cluster = MarkerCluster(name="Properties").add_to(m)
        
        for _, row in gdf.iterrows():
            popup_html = MapComponents._create_property_popup(row)
            
            # Create marker with color based on price
            color = MapComponents._get_price_color(row.get(fields.PRICE, 0))
            
            folium.Marker(
                location=[row.geometry.y, row.geometry.x],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"${row.get(fields.PRICE, 0):,.0f}",
                icon=folium.Icon(color=color, icon="home")
            ).add_to(marker_cluster)
    
    @staticmethod
    def _create_property_popup(row: pd.Series) -> str:
        """Create HTML popup for property marker."""
        price = format_currency(row.get(fields.PRICE, 0))
        address = row.get(fields.ADDRESS, "Address not available")
        sqft = row.get(fields.SQFT, "N/A")
        lot_size = row.get(fields.LOT, "N/A")
        url = row.get(fields.URL, "#")
        
        return f"""
        <div style="font-family: Arial, sans-serif; width: 250px;">
            <h4 style="color: {config.PRIMARY_COLOR}; margin: 0 0 10px 0;">
                {price}
            </h4>
            <p style="margin: 5px 0;"><strong>Address:</strong> {address}</p>
            <p style="margin: 5px 0;"><strong>Living Area:</strong> {sqft} sq ft</p>
            <p style="margin: 5px 0;"><strong>Lot Size:</strong> {lot_size} sq ft</p>
            <a href="{url}" target="_blank" style="color: {config.PRIMARY_COLOR};">
                View Details
            </a>
        </div>
        """
    
    @staticmethod
    def _get_price_color(price: float) -> str:
        """Get marker color based on price range."""
        if price < 200000:
            return "green"
        elif price < 400000:
            return "blue"
        elif price < 600000:
            return "orange"
        else:
            return "red"

# ========================================================================
# MAIN APPLICATION
# ========================================================================

def initialize_session_state():
    """Initialize Streamlit session state."""
    defaults = {
        "app_state": AppState(),
        "performance_metrics": {},
        "last_update": time.time()
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def create_sidebar():
    """Create and manage the sidebar interface."""
    with st.sidebar:
        st.header("📁 Data Upload")
        
        # CSV Upload Section
        st.subheader("Property Data (CSV)")
        csv_files = st.file_uploader(
            "Upload Redfin CSV files",
            type=["csv"],
            accept_multiple_files=True,
            help="Upload one or more CSV files containing property data"
        )
        
        if csv_files:
            process_csv_uploads(csv_files)
        
        st.divider()
        
        # Spatial Data Upload Section
        st.subheader("Spatial Layers")
        
        create_spatial_upload_section("🏫 School Districts", "isd_layers", "ISD: ")
        create_spatial_upload_section("🏗️ Special Districts", "spec_layers", "Special District: ")
        create_spatial_upload_section("✨ Other Layers", "misc_layers", "", require_title=True)
        
        st.divider()
        
        # Data Summary
        create_data_summary()
        
        # Global Filters
        create_global_filters()

def process_csv_uploads(uploaded_files):
    """Process uploaded CSV files."""
    app_state = st.session_state.app_state
    
    for uploaded_file in uploaded_files:
        if uploaded_file.name in {layer["name"] for layer in app_state.sales_layers}:
            continue
        
        if not validate_file_size(uploaded_file):
            continue
        
        try:
            file_content = uploaded_file.read()
            uploaded_file.seek(0)  # Reset file pointer
            
            with st.spinner(f"Processing {uploaded_file.name}..."):
                gdf = DataLoader.load_csv(file_content, uploaded_file.name)
                
                if not gdf.empty:
                    app_state.sales_layers.append({
                        "gdf": gdf,
                        "name": uploaded_file.name,
                        "visible": True,
                        "upload_time": time.time()
                    })
                    st.success(f"✅ Loaded {len(gdf)} properties from {uploaded_file.name}")
                else:
                    st.error(f"❌ Failed to load {uploaded_file.name}")
        
        except Exception as e:
            st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")
            logger.error(f"CSV processing error: {e}", exc_info=True)

def create_spatial_upload_section(title: str, layer_key: str, prefix: str, require_title: bool = False):
    """Create spatial file upload section."""
    st.write(f"**{title}**")
    
    spatial_files = st.file_uploader(
        f"{title} files",
        type=["gpkg", "geojson", "json", "kml", "kmz", "csv"],
        accept_multiple_files=True,
        key=f"{layer_key}_uploader"
    )
    
    if spatial_files:
        app_state = st.session_state.app_state
        
        for uploaded_file in spatial_files:
            if uploaded_file.name in app_state.processed_files:
                continue
            
            if not validate_file_size(uploaded_file):
                continue
            
            try:
                file_content = uploaded_file.read()
                uploaded_file.seek(0)
                
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    gdf = DataLoader.load_spatial_file(file_content, uploaded_file.name)
                    
                    if gdf.empty:
                        st.warning(f"⚠️ Could not read {uploaded_file.name}")
                        continue
                    
                    # Create form for layer configuration
                    with st.form(f"form_{layer_key}_{uploaded_file.name}"):
                        st.write(f"Configure **{uploaded_file.name}**")
                        
                        # Select field for labels
                        text_columns = [col for col in gdf.columns if col != 'geometry']
                        if not text_columns:
                            st.error("No text columns found for labeling")
                            continue
                        
                        field = st.selectbox("Label field:", text_columns)
                        
                        # Optional title for misc layers
                        layer_title = prefix
                        if require_title:
                            layer_title = st.text_input("Layer title:", value="Layer: ")
                        
                        if st.form_submit_button("➕ Add Layer"):
                            layer_list = getattr(app_state, layer_key)
                            layer_list.append({
                                "gdf": gdf,
                                "name": uploaded_file.name,
                                "field": field,
                                "label": layer_title,
                                "visible": True,
                                "upload_time": time.time()
                            })
                            
                            app_state.processed_files.add(uploaded_file.name)
                            st.success(f"✅ Added layer: {uploaded_file.name}")
                            safe_rerun()
            
            except Exception as e:
                st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")
                logger.error(f"Spatial file processing error: {e}", exc_info=True)

def create_data_summary():
    """Create data summary section."""
    app_state = st.session_state.app_state
    
    total_properties = sum(
        len(layer["gdf"]) for layer in app_state.sales_layers if layer["visible"]
    )
    
    total_layers = len(app_state.isd_layers) + len(app_state.spec_layers) + len(app_state.misc_layers)
    
    st.info(f"""
    **Data Summary**
    - 📊 {total_properties:,} properties
    - 🗂️ {len(app_state.sales_layers)} CSV files
    - 🗺️ {total_layers} spatial layers
    """)

def create_global_filters():
    """Create global filter controls."""
    app_state = st.session_state.app_state
    
    if not app_state.sales_layers:
        return
    
    # Combine all visible sales data
    master_df = pd.concat(
        [layer["gdf"] for layer in app_state.sales_layers if layer["visible"]],
        ignore_index=True
    )
    
    if master_df.empty:
        return
    
    with st.expander("🔍 Global Filters", expanded=True):
        if fields.PRICE in master_df.columns:
            FilterComponents.create_range_filter(
                "Price Range ($)", "price_range", 
                master_df[fields.PRICE], 1000, "$%.0f"
            )
        
        if fields.SQFT in master_df.columns:
            FilterComponents.create_range_filter(
                "Living Area (sq ft)", "sqft_range",
                master_df[fields.SQFT], 50, "%.0f"
            )
        
        if fields.LOT in master_df.columns:
            FilterComponents.create_range_filter(
                "Lot Size (sq ft)", "lot_range",
                master_df[fields.LOT], 100, "%.0f"
            )

def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all active filters to the data."""
    if df.empty:
        return df
    
    filtered_df = df.copy()
    
    # Apply range filters
    filter_configs = [
        ("price_range", fields.PRICE),
        ("sqft_range", fields.SQFT),
        ("lot_range", fields.LOT)
    ]
    
    for filter_key, column in filter_configs:
        if filter_key in st.session_state and column in filtered_df.columns:
            min_val, max_val = st.session_state[filter_key]
            filtered_df = filtered_df[
                filtered_df[column].between(min_val, max_val, inclusive="both")
            ]
    
    # Apply spatial filter
    if st.session_state.app_state.active_geojson:
        try:
            geometry = shape(st.session_state.app_state.active_geojson)
            filtered_df = filtered_df[filtered_df.geometry.within(geometry)]
        except Exception as e:
            logger.warning(f"Spatial filter error: {e}")
    
    return filtered_df

def create_map_tab(filtered_gdf: gpd.GeoDataFrame):
    """Create the map and comps analysis tab."""
    st.header("🗺️ Interactive Map & Comparable Analysis")
    
    # Map controls
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Apply Drawn Area", use_container_width=True):
            if st.session_state.app_state.drawn_geojson:
                st.session_state.app_state.active_geojson = st.session_state.app_state.drawn_geojson
                safe_rerun()
    
    with col2:
        if st.button("🗑️ Clear Area", use_container_width=True):
            st.session_state.app_state.active_geojson = None
            st.session_state.app_state.drawn_geojson = None
            safe_rerun()
    
    # Create map
    center = config.DEFAULT_CENTER
    if not filtered_gdf.empty:
        center = [
            filtered_gdf.geometry.y.mean(),
            filtered_gdf.geometry.x.mean()
        ]
    
    with st.spinner("Generating map..."):
        m = MapComponents.create_base_map(center)
        
        # Add spatial layers
        add_spatial_layers_to_map(m)
        
        # Add property markers
        MapComponents.add_property_markers(m, filtered_gdf)
        
        # Add drawing tools
        Draw(export=False).add_to(m)
        LayerControl().add_to(m)
        
        # Display map
        map_data = st_folium(m, height=600, use_container_width=True, key="main_map")
        
        # Handle drawn geometry
        if map_data and map_data.get("last_active_drawing"):
            st.session_state.app_state.drawn_geojson = map_data["last_active_drawing"]["geometry"]
    
    # Comparable analysis
    create_comparable_analysis(filtered_gdf)

def add_spatial_layers_to_map(m: Map):
    """Add spatial layers to the map."""
    app_state = st.session_state.app_state
    
    style_function = lambda x: {
        "weight": 2,
        "color": "#444",
        "fillColor": "#3388ff",
        "fillOpacity": 0.15
    }
    
    # Add all spatial layers
    for layer_group in [app_state.isd_layers, app_state.spec_layers, app_state.misc_layers]:
        for layer in layer_group:
            if not layer.get("visible", True):
                continue
            
            try:
                folium.GeoJson(
                    layer["gdf"],
                    name=layer["name"],
                    style_function=style_function,
                    tooltip=GeoJsonTooltip(
                        fields=[layer["field"]],
                        aliases=[layer["label"]],
                        sticky=False,
                        labels=True
                    )
                ).add_to(m)
            except Exception as e:
                logger.warning(f"Error adding layer {layer['name']}: {e}")

def create_comparable_analysis(gdf: gpd.GeoDataFrame):
    """Create comparable properties analysis section."""
    st.markdown("---")
    st.subheader("📊 Comparable Properties Analysis")
    
    if gdf.empty:
        st.info("No properties match the current filters.")
        return
    
    # Property selection interface
    display_df = gdf.copy()
    display_df["Include"] = ~display_df[fields.UID].isin(
        st.session_state.app_state.excluded_uids
    )
    
    # Summary metrics
    included_count = display_df["Include"].sum()
    st.metric("Properties Selected", f"{included_count:,} of {len(display_df):,}")
    
    # Interactive data editor
    columns_to_show = [fields.UID, "Include"]
    column_config = {"Include": st.column_config.CheckboxColumn("Use")}
    
    # Add available columns
    display_columns = {
        fields.ADDRESS: "Address",
        fields.PRICE: "Price",
        fields.PRICE_PER_SQFT: "$/SqFt",
        fields.LOT_BAND: "Lot Band",
        fields.SCHOOL_DISTRICT: "School District"
    }
    
    for field, label in display_columns.items():
        if field in display_df.columns:
            columns_to_show.append(field)
            if field == fields.PRICE:
                column_config[field] = st.column_config.NumberColumn(
                    label, format="$%d"
                )
            elif field == fields.PRICE_PER_SQFT:
                column_config[field] = st.column_config.NumberColumn(
                    label, format="$%.2f"
                )
    
    edited_df = st.data_editor(
        display_df[columns_to_show].rename(columns=display_columns),
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        key="property_editor"
    )
    
    # Handle selection changes
    if len(edited_df) == len(display_df):
        changes = edited_df["Use"] != display_df["Include"]
        if changes.any():
            for idx in changes[changes].index:
                uid = display_df.iloc[idx][fields.UID]
                if uid in st.session_state.app_state.excluded_uids:
                    st.session_state.app_state.excluded_uids.remove(uid)
                else:
                    st.session_state.app_state.excluded_uids.add(uid)
            safe_rerun()
    
    # Calculate and display statistics
    selected_properties = display_df[display_df["Include"]]
    
    if not selected_properties.empty:
        create_summary_statistics(selected_properties)
        create_price_analysis_chart(selected_properties)

def create_summary_statistics(df: pd.DataFrame):
    """Create summary statistics display."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Properties", f"{len(df):,}")
    
    with col2:
        if fields.PRICE in df.columns:
            avg_price = df[fields.PRICE].mean()
            st.metric("Avg Price", format_currency(avg_price))
    
    with col3:
        if fields.PRICE in df.columns:
            med_price = df[fields.PRICE].median()
            st.metric("Median Price", format_currency(med_price))
    
    with col4:
        if fields.PRICE_PER_SQFT in df.columns:
            avg_psf = df[fields.PRICE_PER_SQFT].mean()
            st.metric("Avg $/SqFt", format_currency_precise(avg_psf))

def create_price_analysis_chart(df: pd.DataFrame):
    """Create price analysis scatter plot."""
    if fields.PRICE_PER_SQFT not in df.columns or fields.PRICE not in df.columns:
        return
    
    # Remove outliers for better visualization
    psf_q99 = df[fields.PRICE_PER_SQFT].quantile(0.99)
    price_q99 = df[fields.PRICE].quantile(0.99)
    
    chart_df = df[
        (df[fields.PRICE_PER_SQFT] <= psf_q99) &
        (df[fields.PRICE] <= price_q99)
    ].copy()
    
    if chart_df.empty:
        return
    
    fig = px.scatter(
        chart_df,
        x=fields.PRICE_PER_SQFT,
        y=fields.PRICE,
        color=fields.LOT_BAND if fields.LOT_BAND in chart_df.columns else None,
        hover_data=[fields.ADDRESS, fields.LOT] if fields.ADDRESS in chart_df.columns else None,
        title="Price vs. Price per Square Foot",
        labels={
            fields.PRICE_PER_SQFT: "Price per Square Foot ($)",
            fields.PRICE: "Total Price ($)"
        }
    )
    
    fig.update_layout(
        height=500,
        hovermode="closest"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_analysis_tabs(filtered_gdf: gpd.GeoDataFrame):
    """Create additional analysis tabs."""
    # Get selected properties
    selected_df = filtered_gdf[
        ~filtered_gdf[fields.UID].isin(st.session_state.app_state.excluded_uids)
    ] if not filtered_gdf.empty else pd.DataFrame()
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏘️ Community", "📈 Overview", "🌳 Lot Analysis", 
        "🏫 Districts", "🛏️ Beds/Baths", "📊 Export"
    ])
    
    with tab1:
        create_community_analysis(selected_df)
    
    with tab2:
        create_overview_analysis(selected_df)
    
    with tab3:
        create_lot_analysis(selected_df)
    
    with tab4:
        create_district_analysis(selected_df)
    
    with tab5:
        create_beds_baths_analysis(selected_df)
    
    with tab6:
        create_export_section(selected_df)

def create_community_analysis(df: pd.DataFrame):
    """Create community analysis tab."""
    st.header("🏘️ Community Analysis")
    
    if df.empty:
        st.info("No properties selected for analysis.")
        return
    
    if fields.COMMUNITY not in df.columns:
        st.warning("Community information not available.")
        return
    
    # Community summary statistics
    community_stats = df.groupby(fields.COMMUNITY).agg({
        fields.UID: "count",
        fields.PRICE: ["mean", "median"] if fields.PRICE in df.columns else fields.UID,
        fields.PRICE_PER_SQFT: "mean" if fields.PRICE_PER_SQFT in df.columns else fields.UID
    }).round(2)
    
    community_stats.columns = ["Properties Sold", "Avg Price", "Median Price", "Avg $/SqFt"]
    community_stats = community_stats.reset_index()
    
    # Format currency columns
    for col in ["Avg Price", "Median Price"]:
        if col in community_stats.columns:
            community_stats[col] = community_stats[col].apply(format_currency)
    
    if "Avg $/SqFt" in community_stats.columns:
        community_stats["Avg $/SqFt"] = community_stats["Avg $/SqFt"].apply(format_currency_precise)
    
    st.dataframe(community_stats, use_container_width=True, hide_index=True)
    
    # Community price distribution
    if fields.PRICE in df.columns and len(df[fields.COMMUNITY].unique()) > 1:
        fig = px.box(
            df,
            x=fields.COMMUNITY,
            y=fields.PRICE,
            title="Price Distribution by Community"
        )
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

def create_overview_analysis(df: pd.DataFrame):
    """Create overview analysis tab."""
    st.header("📈 Market Overview")
    
    if df.empty:
        st.info("No properties selected for analysis.")
        return
    
    # Price distribution
    if fields.PRICE in df.columns:
        fig1 = px.histogram(
            df,
            x=fields.PRICE,
            nbins=30,
            title="Price Distribution",
            labels={fields.PRICE: "Price ($)"}
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    # Price vs Square Footage
    if fields.PRICE in df.columns and fields.SQFT in df.columns:
        fig2 = px.scatter(
            df,
            x=fields.SQFT,
            y=fields.PRICE,
            trendline="ols",
            title="Price vs. Living Area",
            labels={
                fields.SQFT: "Living Area (sq ft)",
                fields.PRICE: "Price ($)"
            }
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # Market metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if fields.PRICE in df.columns:
            price_stats = df[fields.PRICE].describe()
            st.metric("Median Price", format_currency(price_stats['50%']))
            st.metric("Price Range", f"{format_currency(price_stats['min'])} - {format_currency(price_stats['max'])}")
    
    with col2:
        if fields.SQFT in df.columns:
            sqft_stats = df[fields.SQFT].describe()
            st.metric("Median Size", f"{sqft_stats['50%']:,.0f} sq ft")
            st.metric("Size Range", f"{sqft_stats['min']:,.0f} - {sqft_stats['max']:,.0f} sq ft")
    
    with col3:
        if fields.PRICE_PER_SQFT in df.columns:
            psf_stats = df[fields.PRICE_PER_SQFT].describe()
            st.metric("Median $/SqFt", format_currency_precise(psf_stats['50%']))

def create_lot_analysis(df: pd.DataFrame):
    """Create lot analysis tab."""
    st.header("🌳 Lot Size Analysis")
    
    if df.empty or fields.LOT not in df.columns:
        st.info("No lot size data available for analysis.")
        return
    
    # Lot band distribution
    if fields.LOT_BAND in df.columns:
        lot_counts = df[fields.LOT_BAND].value_counts()
        fig1 = px.bar(
            x=lot_counts.index,
            y=lot_counts.values,
            title="Properties by Lot Size Band",
            labels={"x": "Lot Size Band", "y": "Number of Properties"}
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    # Price vs Lot Size
    if fields.PRICE in df.columns:
        fig2 = px.scatter(
            df,
            x=fields.LOT,
            y=fields.PRICE,
            color=fields.LOT_BAND if fields.LOT_BAND in df.columns else None,
            title="Price vs. Lot Size",
            labels={
                fields.LOT: "Lot Size (sq ft)",
                fields.PRICE: "Price ($)"
            }
        )
        st.plotly_chart(fig2, use_container_width=True)

def create_district_analysis(df: pd.DataFrame):
    """Create school district analysis tab."""
    st.header("🏫 School District Analysis")
    
    if df.empty or fields.SCHOOL_DISTRICT not in df.columns:
        st.info("No school district data available.")
        return
    
    if df[fields.SCHOOL_DISTRICT].nunique() <= 1:
        st.info("Insufficient district data for comparison.")
        return
    
    # District price comparison
    if fields.PRICE_PER_SQFT in df.columns:
        fig = px.box(
            df[df[fields.SCHOOL_DISTRICT] != "N/A"],
            x=fields.SCHOOL_DISTRICT,
            y=fields.PRICE_PER_SQFT,
            title="Price per Square Foot by School District"
        )
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)
    
    # District summary table
    district_stats = df[df[fields.SCHOOL_DISTRICT] != "N/A"].groupby(fields.SCHOOL_DISTRICT).agg({
        fields.UID: "count",
        fields.PRICE: "mean" if fields.PRICE in df.columns else fields.UID,
        fields.PRICE_PER_SQFT: "mean" if fields.PRICE_PER_SQFT in df.columns else fields.UID
    }).round(2)
    
    district_stats.columns = ["Properties", "Avg Price", "Avg $/SqFt"]
    district_stats = district_stats.reset_index()
    
    st.dataframe(district_stats, use_container_width=True, hide_index=True)

def create_beds_baths_analysis(df: pd.DataFrame):
    """Create beds and baths analysis tab."""
    st.header("🛏️ Bedroom & Bathroom Analysis")
    
    if df.empty or fields.BEDS not in df.columns or fields.BATHS not in df.columns:
        st.info("No bedroom/bathroom data available.")
        return
    
    # Bed/Bath combination frequency
    bed_bath_counts = df.groupby([fields.BEDS, fields.BATHS]).size().reset_index(name="Count")
    
    fig = px.scatter(
        bed_bath_counts,
        x=fields.BEDS,
        y=fields.BATHS,
        size="Count",
        size_max=40,
        title="Property Count by Bedroom/Bathroom Combination",
        labels={
            fields.BEDS: "Bedrooms",
            fields.BATHS: "Bathrooms"
        }
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Price by bedroom count
    if fields.PRICE in df.columns:
        fig2 = px.box(
            df,
            x=fields.BEDS,
            y=fields.PRICE,
            title="Price Distribution by Bedroom Count"
        )
        st.plotly_chart(fig2, use_container_width=True)

def create_export_section(df: pd.DataFrame):
    """Create data export section."""
    st.header("📊 Data Export")
    
    if df.empty:
        st.warning("No data available for export.")
        return
    
    # Prepare export data
    export_df = df.copy()
    if "geometry" in export_df.columns:
        export_df = export_df.drop(columns=["geometry"])
    
    # Data preview
    st.subheader("Data Preview")
    st.dataframe(export_df.head(10), use_container_width=True)
    
    # Export statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Records", len(export_df))
    with col2:
        st.metric("Total Columns", len(export_df.columns))
    with col3:
        if fields.PRICE in export_df.columns:
            total_value = export_df[fields.PRICE].sum()
            st.metric("Total Value", format_currency(total_value))
    
    # Download options
    st.subheader("Download Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv_data = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download as CSV",
            csv_data,
            "property_analysis.csv",
            "text/csv",
            use_container_width=True
        )
    
    with col2:
        json_data = export_df.to_json(orient="records", indent=2).encode("utf-8")
        st.download_button(
            "📥 Download as JSON",
            json_data,
            "property_analysis.json",
            "application/json",
            use_container_width=True
        )

def main():
    """Main application function."""
    # Configure page
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon=config.PAGE_ICON,
        layout=config.LAYOUT,
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown(f"""
    <style>
    .main .block-container {{
        padding-top: 1rem;
    }}
    .stMetric {{
        background-color: #f0f2f6;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        padding: 1rem;
    }}
    .stButton > button {{
        background-color: {config.PRIMARY_COLOR};
        color: white;
        border: none;
        border-radius: 5px;
    }}
    .stButton > button:hover {{
        background-color: {config.ACCENT_COLOR};
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    initialize_session_state()
    
    # App header
    st.title(config.APP_TITLE)
    st.markdown("*Advanced property analysis and comparable market analysis tool*")
    
    # Create sidebar
    create_sidebar()
    
    # Main content area
    app_state = st.session_state.app_state
    
    # Combine and process data
    if app_state.sales_layers:
        with performance_timer("Data processing"):
            # Combine all visible sales layers
            combined_gdf = pd.concat(
                [layer["gdf"] for layer in app_state.sales_layers if layer["visible"]],
                ignore_index=True
            )
            
            if not combined_gdf.empty:
                # Apply filters
                filtered_gdf = apply_filters(combined_gdf)
                
                # Enrich data
                filtered_gdf = PropertyAnalyzer.calculate_price_per_sqft(filtered_gdf)
                filtered_gdf = PropertyAnalyzer.assign_lot_bands(filtered_gdf)
                filtered_gdf = PropertyAnalyzer.assign_school_districts(
                    filtered_gdf, app_state.isd_layers
                )
                
                # Create main tabs
                tab1, tab2 = st.tabs(["🗺️ Map & Analysis", "📊 Detailed Analytics"])
                
                with tab1:
                    create_map_tab(filtered_gdf)
                
                with tab2:
                    create_analysis_tabs(filtered_gdf)
            else:
                st.info("No properties match the current filters. Try adjusting your filter criteria.")
    else:
        st.info("👆 Upload CSV files containing property data to get started.")
        
        # Show example data format
        with st.expander("📋 Expected CSV Format", expanded=False):
            st.markdown("""
            Your CSV files should contain these columns (case-insensitive):
            
            **Required:**
            - `LATITUDE` or `LAT` - Property latitude
            - `LONGITUDE`, `LON`, or `LONG` - Property longitude  
            - `PRICE` - Sale price
            
            **Optional but recommended:**
            - `ADDRESS` - Property address
            - `SQUARE FEET`, `SQFT`, or `SQ.FT.` - Living area
            - `LOT SIZE`, `LOT SF`, or `LOT SQFT` - Lot size
            - `BEDS` or `BEDROOMS` - Number of bedrooms
            - `BATHS` or `BATHROOMS` - Number of bathrooms
            - `LOCATION` or `SUBDIVISION` - Community name
            - `DAYS ON MARKET` or `DOM` - Marketing time
            - `URL` - Link to property listing
            """)
    
    # Performance monitoring
    if st.sidebar.checkbox("Show Performance Metrics", value=False):
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚡ Performance")
        
        memory_usage = sum(
            layer["gdf"].memory_usage(deep=True).sum()
            for layer_list in [app_state.sales_layers, app_state.isd_layers, 
                             app_state.spec_layers, app_state.misc_layers]
            for layer in layer_list
        ) / 1024 / 1024  # Convert to MB
        
        st.sidebar.metric("Memory Usage", f"{memory_usage:.1f} MB")
        
        if st.sidebar.button("🧹 Clean Memory"):
            clean_memory()
            st.sidebar.success("Memory cleaned!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"❌ Application Error: {str(e)}")
        logger.error(f"Application error: {e}", exc_info=True)
        
        with st.expander("🔍 Error Details"):
            st.code(traceback.format_exc())