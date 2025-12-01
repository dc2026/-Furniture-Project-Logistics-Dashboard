import streamlit as st
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
import pandas as pd
import hashlib
import json
import os

class AddressGeocoder:
    """Handles geocoding with caching to avoid repeated API calls"""
    
    def __init__(self, cache_file='geocoding_cache.json'):
        self.geolocator = Nominatim(user_agent="tfp_furniture_scheduler")
        self.cache_file = cache_file
        self.cache = self._load_cache()
        
    def _load_cache(self):
        """Load geocoding cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        """Save geocoding cache to file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except:
            pass
    
    def _get_cache_key(self, address):
        """Generate cache key from address"""
        return hashlib.md5(address.lower().encode()).hexdigest()
    
    def geocode_address(self, address, retry_count=3):
        """Geocode address with caching and retry logic"""
        cache_key = self._get_cache_key(address)
        
        # Check cache first
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            return (cached['lat'], cached['lon'])
        
        # Try geocoding
        for attempt in range(retry_count):
            try:
                location = self.geolocator.geocode(address, timeout=10)
                if location:
                    coords = (location.latitude, location.longitude)
                    # Cache result
                    self.cache[cache_key] = {
                        'lat': coords[0],
                        'lon': coords[1],
                        'address': address
                    }
                    self._save_cache()
                    return coords
                time.sleep(1)
            except (GeocoderTimedOut, GeocoderServiceError):
                if attempt < retry_count - 1:
                    time.sleep(2)
                else:
                    return None
        
        return None
    
    def batch_geocode(self, addresses_df, address_col, zip_col=None):
        """Geocode multiple addresses with progress tracking"""
        results = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, row in addresses_df.iterrows():
            address = row.get(address_col, '')
            
            # Build full address
            if zip_col and row.get(zip_col):
                full_address = f"{address}, Omaha, NE {row[zip_col]}"
            else:
                full_address = f"{address}, Omaha, NE"
            
            coords = self.geocode_address(full_address)
            
            results.append({
                'index': idx,
                'address': address,
                'lat': coords[0] if coords else None,
                'lon': coords[1] if coords else None,
                'geocoded': coords is not None
            })
            
            progress = len(results) / len(addresses_df)
            progress_bar.progress(progress)
            status_text.text(f"Geocoding: {len(results)}/{len(addresses_df)} addresses...")
            
            time.sleep(0.5)
        
        progress_bar.empty()
        status_text.empty()
        
        return pd.DataFrame(results)
    
    def calculate_distance(self, coord1, coord2):
        """Calculate distance between two coordinates in miles"""
        if coord1 and coord2:
            return geodesic(coord1, coord2).miles
        return float('inf')
    
    def get_route_distance(self, coordinates_list):
        """Calculate total distance for a route"""
        total_distance = 0
        for i in range(len(coordinates_list) - 1):
            total_distance += self.calculate_distance(
                coordinates_list[i], 
                coordinates_list[i + 1]
            )
        return total_distance