import folium
from streamlit_folium import st_folium
import streamlit as st

class RouteMapVisualizer:
    """Create interactive maps for routes"""
    
    def __init__(self):
        self.omaha_center = (41.2565, -95.9345)
    
    def create_route_map(self, coordinates, labels=None):
        """Create Folium map with route visualization
        
        Args:
            coordinates: List of (lat, lon) tuples
            labels: Optional list of labels for each coordinate
        """
        
        m = folium.Map(
            location=self.omaha_center,
            zoom_start=11,
            tiles='OpenStreetMap'
        )
        
        if not coordinates:
            return m
        
        # Use labels if provided, otherwise create generic ones
        if not labels:
            labels = [f"Stop {i+1}" for i in range(len(coordinates))]
        
        # Add markers for each coordinate
        for idx, (coord, label) in enumerate(zip(coordinates, labels)):
            if not coord or len(coord) != 2:
                continue
                
            # Determine marker style based on label
            if 'warehouse' in label.lower():
                icon_color = 'green'
                icon_symbol = 'home'
            elif 'delivery' in label.lower():
                icon_color = 'blue' 
                icon_symbol = 'truck'
            elif 'pickup' in label.lower():
                icon_color = 'orange'
                icon_symbol = 'box'
            else:
                icon_color = 'gray'
                icon_symbol = 'info-sign'
            
            folium.Marker(
                coord,
                popup=label,
                icon=folium.Icon(color=icon_color, icon=icon_symbol, prefix='fa'),
                tooltip=label
            ).add_to(m)
        
        # Draw route line if we have multiple valid coordinates
        valid_coords = [coord for coord in coordinates if coord and len(coord) == 2]
        if len(valid_coords) > 1:
            folium.PolyLine(
                valid_coords,
                color='red',
                weight=3,
                opacity=0.7,
                popup='Route'
            ).add_to(m)
        
        return m
    
    def create_coverage_map(self, all_requests_df, zip_col, geocoder):
        """Create heatmap of request density"""
        m = folium.Map(
            location=self.omaha_center,
            zoom_start=11
        )
        
        if zip_col not in all_requests_df.columns:
            return m
        
        # Count requests by zip
        zip_counts = all_requests_df[zip_col].astype(str).str[:5].value_counts()
        
        # Add circle markers sized by request count
        for zip_code, count in zip_counts.head(20).items():
            if zip_code == 'nan' or not zip_code:
                continue
                
            # Geocode zip code center
            coords = geocoder.geocode_address(f"{zip_code}, Omaha, NE")
            
            if coords and len(coords) == 2:
                folium.CircleMarker(
                    location=coords,
                    radius=min(count * 2, 30),
                    popup=f"Zip {zip_code}: {count} requests",
                    color='blue',
                    fill=True,
                    fillOpacity=0.6
                ).add_to(m)
        
        return m
    
    def display_map(self, folium_map):
        """Display folium map in Streamlit"""
        return st_folium(folium_map, width=700, height=500)