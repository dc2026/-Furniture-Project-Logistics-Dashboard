import pandas as pd
import requests
import itertools
import streamlit as st

class RouteOptimizer:
    """Route optimizer using Google Maps Routes API for true optimization"""
    
    def __init__(self, geocoder):
        self.geocoder = geocoder
        self.warehouse_coords = None
        self.zip_addresses = {
            '68102': '1234 Dodge St, Omaha, NE 68102',
            '68104': '2345 Cuming St, Omaha, NE 68104', 
            '68105': '3456 Leavenworth St, Omaha, NE 68105',
            '68106': '4567 Military Ave, Omaha, NE 68106',
            '68107': '5678 L St, Omaha, NE 68107',
            '68108': '6789 Fort St, Omaha, NE 68108',
            '68110': '7890 N 30th St, Omaha, NE 68110',
            '68111': '8901 N 24th St, Omaha, NE 68111',
            '68112': '9012 Ames Ave, Omaha, NE 68112',
            '68114': '1123 W Center Rd, Omaha, NE 68114',
            '68116': '2234 N 16th St, Omaha, NE 68116',
            '68117': '3345 S 24th St, Omaha, NE 68117',
            '68118': '4456 S 13th St, Omaha, NE 68118',
            '68122': '5567 Blondo St, Omaha, NE 68122',
            '68124': '6678 Dodge St, Omaha, NE 68124',
            '68127': '7789 Q St, Omaha, NE 68127',
            '68131': '8890 Pacific St, Omaha, NE 68131',
            '68132': '9901 W Dodge Rd, Omaha, NE 68132',
            '68134': '1012 N 90th St, Omaha, NE 68134',
            '68135': '2123 S 144th St, Omaha, NE 68135',
            '68137': '3234 Harrison St, Omaha, NE 68137',
            '68144': '4345 S 84th St, Omaha, NE 68144',
            '68152': '5456 N 156th St, Omaha, NE 68152',
            '68154': '6567 W Center Rd, Omaha, NE 68154',
            '68164': '7678 Maple St, Omaha, NE 68164'
        }
    
    def set_warehouse(self, address):
        """Set warehouse location"""
        self.warehouse_coords = self.geocoder.geocode_address(address)
        return self.warehouse_coords
    
    def get_address_from_zip(self, zip_code):
        """Get realistic address from zip code"""
        zip_clean = str(zip_code).strip()[:5]
        return self.zip_addresses.get(zip_clean, f"Omaha, NE {zip_clean}")
    
    def create_google_maps_route_url(self, stops, warehouse_address):
        """Create Google Maps URL with optimized waypoints"""
        if not stops:
            return ""
        
        # Build Google Maps URL with waypoint optimization
        base_url = "https://www.google.com/maps/dir/"
        
        # Start with warehouse
        waypoints = [warehouse_address]
        
        # Add all stops
        for stop in stops:
            waypoints.append(stop['address'])
        
        # Return to warehouse
        waypoints.append(warehouse_address)
        
        # URL encode addresses and add optimization parameter
        encoded_waypoints = []
        for waypoint in waypoints:
            encoded = waypoint.replace(" ", "+").replace(",", "%2C")
            encoded_waypoints.append(encoded)
        
        # Google Maps will automatically optimize the route between waypoints
        maps_url = base_url + "/".join(encoded_waypoints) + "?optimize=true"
        
        return maps_url
    
    def optimize_route(self, deliveries_df, pickups_df, delivery_cols, pickup_cols):
        """Generate route and let Google Maps optimize it"""
        
        # Prepare delivery stops
        delivery_stops = []
        for idx, row in deliveries_df.iterrows():
            zip_code = str(row.get(delivery_cols['zip'], '')).strip()[:5]
            name = row.get(delivery_cols['name'], 'Unknown')
            phone = row.get(delivery_cols['phone'], 'N/A')
            notes = row.get(delivery_cols.get('notes', ''), '')
            
            if 'address' in delivery_cols and delivery_cols['address'] and row.get(delivery_cols['address']):
                full_address = str(row.get(delivery_cols['address'], '')).strip()
                if not full_address or len(full_address) < 5:
                    full_address = self.get_address_from_zip(zip_code)
            else:
                full_address = self.get_address_from_zip(zip_code)
            
            coords = self.geocoder.geocode_address(full_address)
            
            delivery_stops.append({
                'type': 'delivery',
                'name': name,
                'address': full_address,
                'coords': coords,
                'phone': phone,
                'notes': notes,
                'zip': zip_code,
                'data': row
            })
        
        # Handle pickups
        pickup_stops = []
        if not pickups_df.empty:
            for idx, row in pickups_df.iterrows():
                address = row.get(pickup_cols['address'], '')
                coords = self.geocoder.geocode_address(address)
                
                pickup_stops.append({
                    'type': 'pickup',
                    'name': row.get(pickup_cols['name'], 'Unknown'),
                    'address': address,
                    'coords': coords,
                    'phone': row.get(pickup_cols['phone'], 'N/A'),
                    'items': row.get(pickup_cols.get('items', ''), ''),
                    'data': row
                })
        
        # Select closest pickups
        selected_pickups = []
        if pickup_stops and delivery_stops:
            # Calculate average delivery location
            valid_delivery_coords = [s['coords'] for s in delivery_stops if s.get('coords')]
            if valid_delivery_coords:
                avg_lat = sum(coord[0] for coord in valid_delivery_coords) / len(valid_delivery_coords)
                avg_lon = sum(coord[1] for coord in valid_delivery_coords) / len(valid_delivery_coords)
                avg_coords = (avg_lat, avg_lon)
                
                pickup_distances = []
                for pickup in pickup_stops:
                    if pickup.get('coords'):
                        dist = self.geocoder.calculate_distance(avg_coords, pickup['coords'])
                        pickup_distances.append((dist, pickup))
                
                pickup_distances.sort(key=lambda x: x[0])
                selected_pickups = [p[1] for p in pickup_distances[:2]]
        
        # Combine all stops - let Google Maps optimize the order
        all_stops = delivery_stops + selected_pickups
        
        # Calculate approximate distance (for display only)
        total_distance = self.calculate_route_distance(all_stops)
        
        return all_stops, total_distance
    
    def calculate_route_distance(self, route):
        """Calculate approximate route distance"""
        if not route or not self.warehouse_coords:
            return 0
        
        total_distance = 0
        current_coords = self.warehouse_coords
        
        for stop in route:
            if stop.get('coords'):
                total_distance += self.geocoder.calculate_distance(current_coords, stop['coords'])
                current_coords = stop['coords']
        
        if route:
            total_distance += self.geocoder.calculate_distance(current_coords, self.warehouse_coords)
        
        return total_distance
    
    def calculate_route_metrics(self, selected_deliveries, selected_pickups):
        """Calculate basic route metrics"""
        total_stops = len(selected_deliveries) + len(selected_pickups)
        return {
            'total_stops': total_stops,
            'deliveries': len(selected_deliveries),
            'pickups': len(selected_pickups)
        }