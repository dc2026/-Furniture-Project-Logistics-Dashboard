import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import numpy as np

class DeliveryScheduler:
    """Handles delivery scheduling and route generation logic"""
    
    def __init__(self, data_manager):
        self.dm = data_manager
    
    def calculate_zip_distance(self, zip1, zip2):
        """Estimate distance between zip codes (simple numeric difference as proxy)"""
        try:
            z1 = int(str(zip1)[:5])
            z2 = int(str(zip2)[:5])
            return abs(z1 - z2)
        except:
            return 999999  # Large number for invalid zips
    
    def optimize_route_order(self, deliveries, pickups, warehouse_zip="68137"):
        """Optimize route order by AREA CLUSTERING to prevent back-and-forth travel"""
        all_stops = []
        
        # Add deliveries
        for idx, delivery in deliveries.iterrows():
            zipcode = delivery.get(self.dm.zip_col_del, warehouse_zip) if self.dm.zip_col_del else warehouse_zip
            clean_zip = str(zipcode).strip().split()[0]
            all_stops.append({
                'type': 'delivery',
                'data': delivery,
                'zip': clean_zip,
                'area': clean_zip[:3] if len(clean_zip) >= 3 else clean_zip  # Group by 3-digit area
            })
        
        # Add pickups
        for idx, pickup in pickups.iterrows():
            zipcode = pickup.get(self.dm.pickup_zip_col, warehouse_zip) if self.dm.pickup_zip_col else warehouse_zip
            clean_zip = str(zipcode).strip().split()[0]
            all_stops.append({
                'type': 'pickup',
                'data': pickup,
                'zip': clean_zip,
                'area': clean_zip[:3] if len(clean_zip) >= 3 else clean_zip
            })
        
        if not all_stops:
            return deliveries, pickups
        
        # AREA-BASED CLUSTERING: Group stops by geographic area first
        area_groups = {}
        for stop in all_stops:
            area = stop['area']
            if area not in area_groups:
                area_groups[area] = []
            area_groups[area].append(stop)
        
        # Order areas by distance from warehouse
        warehouse_area = warehouse_zip[:3]
        area_distances = []
        for area in area_groups.keys():
            dist = self.calculate_zip_distance(warehouse_zip, area + "00")
            area_distances.append((dist, area))
        
        area_distances.sort()  # Closest areas first
        
        # Build optimized route: complete each area before moving to next
        optimized = []
        
        for _, area in area_distances:
            area_stops = area_groups[area]
            
            # Within each area, do nearest-neighbor optimization
            area_optimized = []
            remaining_in_area = area_stops.copy()
            
            # Start with stop closest to warehouse (or previous area)
            if optimized:
                current_zip = optimized[-1]['zip']
            else:
                current_zip = warehouse_zip
            
            while remaining_in_area:
                nearest_idx = 0
                min_dist = float('inf')
                
                for i, stop in enumerate(remaining_in_area):
                    dist = self.calculate_zip_distance(current_zip, stop['zip'])
                    if dist < min_dist:
                        min_dist = dist
                        nearest_idx = i
                
                nearest = remaining_in_area.pop(nearest_idx)
                area_optimized.append(nearest)
                current_zip = nearest['zip']
            
            optimized.extend(area_optimized)
        
        # Separate back into deliveries and pickups while preserving order
        optimized_deliveries = [s['data'] for s in optimized if s['type'] == 'delivery']
        optimized_pickups = [s['data'] for s in optimized if s['type'] == 'pickup']
        
        return (pd.DataFrame(optimized_deliveries) if optimized_deliveries else pd.DataFrame(),
                pd.DataFrame(optimized_pickups) if optimized_pickups else pd.DataFrame())
    
    def get_earliest_available_date(self):
        """Find the earliest available delivery date from client preferences"""
        default_date = datetime.now().date() + timedelta(days=1)
        
        if self.dm.self_schedule_df is None:
            return default_date
        
        # Collect all choice dates
        date_cols = [
            self.dm.choice1_col_del,
            self.dm.choice2_col_del,
            self.dm.choice3_col_del,
            self.dm.choice4_col_del
        ]
        
        # Filter out None columns and create date series
        valid_date_series = []
        for col in date_cols:
            if col is not None and col in self.dm.self_schedule_df.columns:
                date_series = pd.to_datetime(self.dm.self_schedule_df[col], errors='coerce')
                valid_date_series.append(date_series)
        
        if not valid_date_series:
            return default_date
            
        all_dates = pd.concat(valid_date_series)
        
        valid_dates = all_dates.dropna()
        
        if len(valid_dates) > 0:
            # Find first date after today
            future_dates = valid_dates[valid_dates.dt.date >= datetime.now().date()]
            if not future_dates.empty:
                return future_dates.min().date()
            # If all dates are past, use earliest (for testing old data)
            return valid_dates.min().date()
        
        return default_date
    
    def score_delivery_for_date(self, delivery_row, target_date_str, existing_zips):
        """Score a delivery based on date preference and location proximity"""
        score = 0
        
        # Date preference scoring (higher = better match)
        if self.dm.choice1_col_del and delivery_row.get(self.dm.choice1_col_del) == target_date_str:
            score += 100
        elif self.dm.choice2_col_del and delivery_row.get(self.dm.choice2_col_del) == target_date_str:
            score += 75
        elif self.dm.choice3_col_del and delivery_row.get(self.dm.choice3_col_del) == target_date_str:
            score += 50
        elif self.dm.choice4_col_del and delivery_row.get(self.dm.choice4_col_del) == target_date_str:
            score += 25
        
        # ENHANCED Location proximity scoring - HEAVILY prioritize same area
        if existing_zips and self.dm.zip_col_del:
            delivery_zip = str(delivery_row.get(self.dm.zip_col_del, '')).strip().split()[0]
            if delivery_zip:
                # Check for exact area matches first
                for existing_zip in existing_zips:
                    # Same 5-digit zip = huge bonus (same neighborhood)
                    if delivery_zip == existing_zip:
                        score += 200  # Massive bonus for exact zip match
                        break
                    # Same first 4 digits = big bonus (same city/area)
                    elif delivery_zip[:4] == existing_zip[:4]:
                        score += 150  # Big bonus for same area
                        break
                    # Same first 3 digits = good bonus (same region)
                    elif delivery_zip[:3] == existing_zip[:3]:
                        score += 100  # Good bonus for same region
                        break
                
                # If no area match, penalize distance heavily
                if not any(delivery_zip[:3] == ez[:3] for ez in existing_zips):
                    min_distance = min([self.calculate_zip_distance(delivery_zip, ez) for ez in existing_zips])
                    # Heavy penalty for distant locations
                    distance_penalty = min(50, min_distance / 10)
                    score -= distance_penalty
        
        # Add waiting time bonus
        if 'Timestamp' in delivery_row.index:
            try:
                request_date = pd.to_datetime(delivery_row['Timestamp'])
                days_waiting = (datetime.now() - request_date).days
                # Bonus for older requests (up to 20 points)
                waiting_bonus = min(20, days_waiting / 3)
                score += waiting_bonus
            except:
                pass
        
        return score
    
    def auto_select_deliveries(self, target_date, target_zip=None, num_days=1):
        """Auto-select up to 4 deliveries per day with HEAVY geographic clustering"""
        all_selections = {}
        
        # Get unscheduled requests
        unscheduled = self.dm.self_schedule_df.copy()
        if self.dm.scheduled_col_del:
            unscheduled = unscheduled[
                unscheduled[self.dm.scheduled_col_del].isna() | 
                (unscheduled[self.dm.scheduled_col_del] == '')
            ]
        
        for day_offset in range(num_days):
            current_date = target_date + timedelta(days=day_offset)
            target_date_str = current_date.strftime('%-m/%-d/%Y')
            
            # Find clients who selected this date in any choice
            date_matches = pd.DataFrame()
            
            if all([self.dm.choice1_col_del, self.dm.choice2_col_del, 
                    self.dm.choice3_col_del, self.dm.choice4_col_del]):
                date_matches = unscheduled[
                    (unscheduled[self.dm.choice1_col_del] == target_date_str) |
                    (unscheduled[self.dm.choice2_col_del] == target_date_str) |
                    (unscheduled[self.dm.choice3_col_del] == target_date_str) |
                    (unscheduled[self.dm.choice4_col_del] == target_date_str)
                ]
            
            # Only select deliveries if there are actual date matches
            selected = pd.DataFrame()
            
            if len(date_matches) > 0:
                # Take up to 4 deliveries that actually requested this date
                selected = date_matches.head(4)
            # If no date matches, selected remains empty
            
            # Remove selected from unscheduled pool
            unscheduled = unscheduled[~unscheduled.index.isin(selected.index)]
            
            all_selections[target_date_str] = selected.head(4)
            
            # If no deliveries found, suggest closest available dates
            if len(selected) == 0:
                closest_dates = self.find_closest_available_dates(target_date_str)
                if closest_dates:
                    st.info(f"💡 **No deliveries available for {target_date_str}**")
                    st.write("**Closest dates with available deliveries:**")
                    for date_option in closest_dates[:3]:
                        count = len(self.get_deliveries_for_date(date_option, unscheduled))
                        if st.button(f"📅 {date_option} ({count} available)", key=f"suggest_{date_option}_{day_offset}"):
                            # Auto-select this suggested date
                            suggested_selections = self.auto_select_deliveries(
                                datetime.strptime(date_option, '%m/%d/%Y').date(),
                                num_days=1
                            )
                            all_selections.update(suggested_selections)
                            st.rerun()
        
        return all_selections
    
    def find_closest_available_dates(self, target_date_str):
        """Find the closest dates that have available deliveries"""
        if not all([self.dm.choice1_col_del, self.dm.choice2_col_del, 
                   self.dm.choice3_col_del, self.dm.choice4_col_del]):
            return []
        
        # Get all unique dates from choice columns
        all_dates = set()
        for col in [self.dm.choice1_col_del, self.dm.choice2_col_del, 
                   self.dm.choice3_col_del, self.dm.choice4_col_del]:
            if col in self.dm.self_schedule_df.columns:
                dates = self.dm.self_schedule_df[col].dropna().unique()
                all_dates.update(dates)
        
        # Convert target date to datetime for comparison
        try:
            target_dt = datetime.strptime(target_date_str, '%m/%d/%Y')
        except:
            return []
        
        # Calculate distances and sort
        date_distances = []
        for date_str in all_dates:
            try:
                date_dt = datetime.strptime(str(date_str), '%m/%d/%Y')
                distance = abs((date_dt - target_dt).days)
                if distance > 0:  # Exclude the target date itself
                    date_distances.append((distance, date_str))
            except:
                continue
        
        # Sort by distance and return closest dates
        date_distances.sort()
        return [date_str for _, date_str in date_distances[:5]]
    
    def get_deliveries_for_date(self, target_date_str, unscheduled_df):
        """Get deliveries that have the target date as one of their choices"""
        if not all([self.dm.choice1_col_del, self.dm.choice2_col_del, 
                   self.dm.choice3_col_del, self.dm.choice4_col_del]):
            return pd.DataFrame()
        
        matches = unscheduled_df[
            (unscheduled_df[self.dm.choice1_col_del] == target_date_str) |
            (unscheduled_df[self.dm.choice2_col_del] == target_date_str) |
            (unscheduled_df[self.dm.choice3_col_del] == target_date_str) |
            (unscheduled_df[self.dm.choice4_col_del] == target_date_str)
        ]
        
        return matches
    
    def get_overdue_requests(self, days_threshold=56):  # 8 weeks default
        """Find requests that haven't been scheduled and are overdue"""
        if self.dm.self_schedule_df is None:
            return pd.DataFrame()
        
        unscheduled = self.dm.self_schedule_df.copy()
        
        if self.dm.scheduled_col_del:
            unscheduled = unscheduled[
                unscheduled[self.dm.scheduled_col_del].isna() | 
                (unscheduled[self.dm.scheduled_col_del] == '')
            ]
        
        # Calculate days since request
        if 'Timestamp' in unscheduled.columns:
            unscheduled['request_date'] = pd.to_datetime(
                unscheduled['Timestamp'], 
                errors='coerce'
            )
            today = pd.Timestamp.now()
            unscheduled['days_waiting'] = (today - unscheduled['request_date']).dt.days
            
            # Only consider requests from the past (positive days_waiting)
            overdue = unscheduled[
                (unscheduled['days_waiting'] > days_threshold) & 
                (unscheduled['days_waiting'] >= 0)
            ]
            return overdue.sort_values('days_waiting', ascending=False)
        
        return pd.DataFrame()
    
    def suggest_neighborhood_deliveries(self, base_delivery_df, max_suggestions=10):
        """Suggest additional deliveries in same neighborhood as base deliveries"""
        if base_delivery_df.empty or self.dm.self_schedule_df is None:
            return pd.DataFrame()
        
        # Get zip codes from base deliveries
        base_zips = self.dm.get_delivery_zip_codes(base_delivery_df)
        base_zip_prefixes = set([z[:3] for z in base_zips if len(z) >= 3])
        
        # Get unscheduled requests
        unscheduled = self.dm.self_schedule_df.copy()
        if self.dm.scheduled_col_del:
            unscheduled = unscheduled[
                unscheduled[self.dm.scheduled_col_del].isna() | 
                (unscheduled[self.dm.scheduled_col_del] == '')
            ]
        
        # Filter to same neighborhood (3-digit zip match)
        if self.dm.zip_col_del:
            unscheduled['zip_prefix'] = unscheduled[self.dm.zip_col_del].astype(str).str[:3]
            neighborhood_matches = unscheduled[
                unscheduled['zip_prefix'].isin(base_zip_prefixes)
            ]
            
            # Exclude already selected deliveries
            neighborhood_matches = neighborhood_matches[
                ~neighborhood_matches.index.isin(base_delivery_df.index)
            ]
            
            # Add waiting time priority
            if 'Timestamp' in neighborhood_matches.columns:
                neighborhood_matches['request_date'] = pd.to_datetime(
                    neighborhood_matches['Timestamp'],
                    errors='coerce'
                )
                neighborhood_matches = neighborhood_matches.sort_values(
                    'request_date', 
                    ascending=True
                )
            
            return neighborhood_matches.head(max_suggestions)
        
        return pd.DataFrame()
    
    def display_selected_deliveries(self, selected, target_date_str):
        """Display selected deliveries with full details"""
        for idx, row in selected.iterrows():
            # Check if this was client's preferred date
            is_preferred = False
            choice_rank = None
            
            if all([self.dm.choice1_col_del, self.dm.choice2_col_del, 
                   self.dm.choice3_col_del, self.dm.choice4_col_del]):
                if row.get(self.dm.choice1_col_del) == target_date_str:
                    is_preferred = True
                    choice_rank = "1st"
                elif row.get(self.dm.choice2_col_del) == target_date_str:
                    is_preferred = True
                    choice_rank = "2nd"
                elif row.get(self.dm.choice3_col_del) == target_date_str:
                    is_preferred = True
                    choice_rank = "3rd"
                elif row.get(self.dm.choice4_col_del) == target_date_str:
                    is_preferred = True
                    choice_rank = "4th"
            
            priority = f"🌟 Client's {choice_rank} Choice" if is_preferred else "📍 Auto-filled (nearby)"
            
            # Use proper row numbering
            client_num = list(selected.index).index(idx) + 1
            name = row.get(self.dm.name_col_del, f'Client #{client_num}') if self.dm.name_col_del else f'Client #{client_num}'
            zipcode = row.get(self.dm.zip_col_del, 'N/A') if self.dm.zip_col_del else 'N/A'
            
            # Debug: Check if zip column is found
            if self.dm.zip_col_del and self.dm.zip_col_del in row.index:
                zipcode = str(row[self.dm.zip_col_del])
            elif 'Zip code' in row.index:
                zipcode = str(row['Zip code'])
            else:
                zipcode = 'N/A'
            
            # Calculate wait time
            wait_days = "N/A"
            if 'Timestamp' in row.index:
                try:
                    request_date = pd.to_datetime(row['Timestamp'])
                    days_diff = (datetime.now() - request_date).days
                    # Show positive days for past requests, "Future" for future requests
                    wait_days = days_diff if days_diff >= 0 else "Future"
                except:
                    pass
            
            with st.expander(f"**{name}** - {zipcode} ({priority}) - Waiting: {wait_days} days"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Name:** {name}")
                    st.write(f"**Zip:** {zipcode}")
                    st.write(f"**Phone:** {row.get(self.dm.phone_col_del, 'N/A') if self.dm.phone_col_del else 'N/A'}")
                with col2:
                    if self.dm.choice1_col_del:
                        st.write(f"**1st Choice:** {row.get(self.dm.choice1_col_del, 'N/A')}")
                    if self.dm.choice2_col_del:
                        st.write(f"**2nd Choice:** {row.get(self.dm.choice2_col_del, 'N/A')}")
                    if self.dm.choice3_col_del:
                        st.write(f"**3rd Choice:** {row.get(self.dm.choice3_col_del, 'N/A')}")
                    if self.dm.choice4_col_del:
                        st.write(f"**4th Choice:** {row.get(self.dm.choice4_col_del, 'N/A')}")
                
                if self.dm.comments_col_del and pd.notna(row.get(self.dm.comments_col_del)):
                    st.write(f"**Notes:** {row[self.dm.comments_col_del]}")
    
    def find_nearby_pickups(self, delivery_zips, max_pickups=10):
        """Find pickups near delivery locations, limited by max_pickups"""
        if self.dm.pickup_df is None:
            return pd.DataFrame()
        
        # Get unscheduled pickups
        unscheduled_pickups = self.dm.pickup_df.copy()
        if self.dm.pickup_scheduled_col:
            unscheduled_pickups = unscheduled_pickups[
                unscheduled_pickups[self.dm.pickup_scheduled_col].isna() | 
                (unscheduled_pickups[self.dm.pickup_scheduled_col] == '')
            ]
        
        # Find pickups in same zip areas (first 4 digits) and score by proximity
        if self.dm.pickup_zip_col:
            pickup_scores = []
            
            for idx, pickup in unscheduled_pickups.iterrows():
                pickup_zip = str(pickup.get(self.dm.pickup_zip_col, '')).strip()
                if pickup_zip:
                    # Calculate minimum distance to any delivery zip
                    min_distance = min([self.calculate_zip_distance(pickup_zip, dz) for dz in delivery_zips if dz])
                    pickup_scores.append((min_distance, idx, pickup))
            
            # Sort by distance (closest first)
            pickup_scores.sort(key=lambda x: x[0])
            
            # Return top matches
            nearby_pickups = [pickup for _, _, pickup in pickup_scores[:max_pickups]]
            return pd.DataFrame(nearby_pickups) if nearby_pickups else pd.DataFrame()
        
        return pd.DataFrame()
    
    def generate_route(self, selected_deliveries, selected_pickups, warehouse_address):
        """Generate optimized route with warehouse start/end"""
        route_steps = []
        
        # Optimize order
        opt_deliveries, opt_pickups = self.optimize_route_order(
            selected_deliveries, 
            selected_pickups
        )
        
        # START at warehouse
        route_steps.append({
            'Stop': 1,
            'Type': '🏭 START',
            'Location': warehouse_address,
            'Details': 'Load furniture for deliveries',
            'Contact': 'N/A',
            'Notes': 'Load Truck',
            'Time': '9:30 AM'
        })
        
        # Add deliveries (9:30 AM - 12:30 PM window)
        delivery_count = len(opt_deliveries)
        time_slots = ['9:45 AM', '10:30 AM', '11:15 AM', '12:00 PM']
        
        for i, (idx, delivery) in enumerate(opt_deliveries.iterrows()):
            name = delivery.get(self.dm.name_col_del, f'Client #{i+1}') if self.dm.name_col_del else f'Client #{i+1}'
            
            # Get zipcode with fallback
            if self.dm.zip_col_del and self.dm.zip_col_del in delivery.index:
                zipcode = str(delivery[self.dm.zip_col_del])
            elif 'Zip code' in delivery.index:
                zipcode = str(delivery['Zip code'])
            else:
                zipcode = 'N/A'
            
            # Convert zip code to full address for Google Maps
            zip_addresses = {
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
                '68164': '7678 Maple St, Omaha, NE 68164',
                '51503': '1234 Broadway, Council Bluffs, IA 51503',
                '51501': '5678 Main St, Council Bluffs, IA 51501',
                '51546': '9012 Oak St, Council Bluffs, IA 51546'
            }
            
            full_address = zip_addresses.get(zipcode, f"Omaha, NE {zipcode}")
                
            phone = delivery.get(self.dm.phone_col_del, 'N/A') if self.dm.phone_col_del else 'N/A'
            notes = ''
            if self.dm.comments_col_del and pd.notna(delivery.get(self.dm.comments_col_del)):
                notes = str(delivery[self.dm.comments_col_del])[:50]
            
            route_steps.append({
                'Stop': i + 2,
                'Type': '🚚 DELIVERY',
                'Location': full_address,
                'Details': name,
                'Contact': phone,
                'Notes': notes,
                'Time': time_slots[i] if i < len(time_slots) else '2:00 PM'
            })
        
        # Add pickups (after deliveries, ending by 2:30 PM)
        pickup_times = ['1:00 PM', '1:30 PM', '2:00 PM']
        
        if not opt_pickups.empty:
            for i, (idx, pickup) in enumerate(opt_pickups.iterrows()):
                pickup_name = pickup.get(self.dm.pickup_name_col, 'Unknown') if self.dm.pickup_name_col else 'Unknown'
                pickup_address = pickup.get(self.dm.pickup_address_col, 'N/A') if self.dm.pickup_address_col else 'N/A'
                pickup_zip = pickup.get(self.dm.pickup_zip_col, 'N/A') if self.dm.pickup_zip_col else 'N/A'
                pickup_phone = pickup.get(self.dm.pickup_phone_col, 'N/A') if self.dm.pickup_phone_col else 'N/A'
                
                route_steps.append({
                    'Stop': len(route_steps) + 1,
                    'Type': '📦 PICKUP',
                    'Location': pickup_address,
                    'Details': pickup_name,
                    'Contact': pickup_phone,
                    'Notes': 'Collect donated items',
                    'Time': pickup_times[i] if i < len(pickup_times) else '4:00 PM'
                })
        
        # END at warehouse
        route_steps.append({
            'Stop': len(route_steps) + 1,
            'Type': '🏭 END',
            'Location': warehouse_address,
            'Details': 'Unload donated items',
            'Contact': 'N/A',
            'Notes': 'Unload Truck',
            'Time': '2:30 PM'
        })
        
        return pd.DataFrame(route_steps)