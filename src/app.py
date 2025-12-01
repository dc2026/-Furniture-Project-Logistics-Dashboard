import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from data_manager import DataManager
from scheduler import DeliveryScheduler
from address_geocoder import AddressGeocoder
from route_optimizer import RouteOptimizer
from map_visualizer import RouteMapVisualizer


# --- CONSTANTS ---
TFP_WAREHOUSE_ADDRESS = "10808 J St, Omaha, NE 68137"

# Page config
st.set_page_config(
    page_title="Furniture Project Logistics Dashboard",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'data_manager' not in st.session_state:
    st.session_state['data_manager'] = DataManager()
if 'geocoder' not in st.session_state:
    st.session_state['geocoder'] = AddressGeocoder()
if 'route_optimizer' not in st.session_state:
    st.session_state['route_optimizer'] = RouteOptimizer(st.session_state['geocoder'])
if 'map_visualizer' not in st.session_state:
    st.session_state['map_visualizer'] = RouteMapVisualizer()

data_manager = st.session_state['data_manager']
geocoder = st.session_state['geocoder']
route_optimizer = st.session_state['route_optimizer']
map_viz = st.session_state['map_visualizer']


# --- HEADER ---
st.title("🚚 Furniture Project Logistics Dashboard")
st.markdown("**Optimize delivery routes and manage pickups efficiently**")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Data Upload Section
    st.subheader("📁 Upload Data Files")
    
    delivery_file = st.file_uploader(
        "Furniture Delivery Self-Schedule CSV",
        type=['csv'],
        key='delivery_upload'
    )
    
    pickup_file = st.file_uploader(
        "Donor Pick Up CSV",
        type=['csv'],
        key='pickup_upload'
    )
    
    assistance_file = st.file_uploader(
        "Request Assistance CSV (Optional)",
        type=['csv'],
        key='assistance_upload'
    )
    
    # Clear cache button
    if st.button("🗑️ Clear Cache & Reset", use_container_width=True, help="Clear old data from memory"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    # Load button
    if st.button("🔄 Load/Reload Data", use_container_width=True):
        with st.spinner("Loading data..."):
            if delivery_file:
                data_manager.load_self_schedule(delivery_file)
                st.success("✅ Delivery data loaded")
            
            if pickup_file:
                data_manager.load_pickups(pickup_file)
                st.success("✅ Pickup data loaded")
            
            if assistance_file:
                data_manager.load_assistance(assistance_file)
                st.success("✅ Assistance requests loaded")
    
    # Quick stats
    if data_manager.self_schedule_df is not None:
        st.divider()
        st.subheader("📊 Quick Stats")
        
        delivery_stats = data_manager.get_delivery_stats()
        pickup_stats = data_manager.get_pickup_stats()
        
        st.metric("Pending Deliveries", delivery_stats['unscheduled'])
        st.metric("Pending Pickups", pickup_stats['unscheduled'])
    
    # Warehouse info - SHOW PROMINENTLY
    st.divider()
    st.subheader("🏭 Warehouse Location")
    
    # Make warehouse address editable
    warehouse_address = st.text_input(
        "Warehouse Address",
        value=TFP_WAREHOUSE_ADDRESS,
        help="Change this if your warehouse location is different"
    )
    
    # Update the constant if changed
    if warehouse_address != TFP_WAREHOUSE_ADDRESS:
        st.session_state['custom_warehouse'] = warehouse_address
        st.success("✅ Custom warehouse address set")
    
    # Use custom address if set
    if 'custom_warehouse' in st.session_state:
        TFP_WAREHOUSE_ADDRESS = st.session_state['custom_warehouse']

# --- MAIN CONTENT ---
if data_manager.self_schedule_df is None:
    st.info("👆 Please upload your data files using the sidebar to get started")
    st.stop()

# Create scheduler
scheduler = DeliveryScheduler(data_manager)

# --- TABS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📅 Schedule Deliveries",
    "🗺️ Optimized Routes",
    "⚠️ Overdue Requests",
    "📈 Analytics",
    "📊 Data View",
    "ℹ️ Help"
])

# --- TAB 1: SCHEDULE DELIVERIES ---
with tab1:
    st.header("📅 Schedule Deliveries")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Date selection
        earliest_date = scheduler.get_earliest_available_date()
        today = datetime.now().date()
        
        # Ensure earliest_date is not before today
        if earliest_date < today:
            earliest_date = today
        
        schedule_date = st.date_input(
            "Select Delivery Date",
            value=earliest_date,
            min_value=today
        )
        
        schedule_date_str = schedule_date.strftime('%-m/%-d/%Y')
    
    with col2:
        num_days = st.number_input(
            "Schedule Multiple Days",
            min_value=1,
            max_value=7,
            value=1,
            help="Schedule deliveries for multiple consecutive days"
        )
    
    # Auto-select deliveries button
    if st.button("🎯 Auto-Select Best Matches", use_container_width=True):
        with st.spinner("Analyzing delivery preferences and locations..."):
            selections = scheduler.auto_select_deliveries(
                schedule_date,
                num_days=num_days
            )
            st.session_state['auto_selections'] = selections
    
    # Display selections
    if 'auto_selections' in st.session_state:
        for date_str, selected in st.session_state['auto_selections'].items():
            st.subheader(f"📆 {date_str}")
            
            if len(selected) == 0:
                st.warning("No suitable deliveries found for this date")
                continue
            
            st.success(f"✅ Selected {len(selected)} deliveries")
            
            # Display each delivery
            scheduler.display_selected_deliveries(selected, date_str)
            
            # Suggest nearby pickups - DEFAULT 3 max
            st.subheader("📦 Suggested Nearby Pickups")
            delivery_zips = data_manager.get_delivery_zip_codes(selected)
            nearby_pickups = scheduler.find_nearby_pickups(delivery_zips, max_pickups=3)
            
            if not nearby_pickups.empty:
                for idx, pickup in nearby_pickups.iterrows():
                    pickup_name = pickup.get(data_manager.pickup_name_col, 'Unknown')
                    pickup_zip = pickup.get(data_manager.pickup_zip_col, 'N/A')
                    estimated_date = pickup.get(data_manager.pickup_estimated_col, 'N/A') if hasattr(data_manager, 'pickup_estimated_col') and data_manager.pickup_estimated_col else 'N/A'
                    
                    with st.expander(f"**{pickup_name}** - {pickup_zip} (Est: {estimated_date})"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Address:** {pickup.get(data_manager.pickup_address_col, 'N/A')}")
                            st.write(f"**Phone:** {pickup.get(data_manager.pickup_phone_col, 'N/A')}")
                            if estimated_date != 'N/A':
                                st.write(f"**Estimated Date:** {estimated_date}")
                        with col2:
                            if data_manager.pickup_items_col:
                                st.write(f"**Items:** {pickup.get(data_manager.pickup_items_col, 'N/A')}")
            else:
                st.info("No nearby pickups available")
            
            st.divider()

# --- TAB 2: OPTIMIZED ROUTES ---
with tab2:
    st.header("🗺️ Optimized Route Generation")
    
    if 'auto_selections' not in st.session_state:
        st.info("👈 Please use Tab 1 to select deliveries first")
    else:
        # Date selector
        available_dates = list(st.session_state['auto_selections'].keys())
        selected_route_date = st.selectbox(
            "Select Date for Route",
            available_dates
        )
        
        selected_deliveries = st.session_state['auto_selections'][selected_route_date]
        
        if len(selected_deliveries) == 0:
            st.warning("No deliveries selected for this date")
        else:
            # Get nearby pickups - DEFAULT 3 max (will auto-reduce if route too long)
            delivery_zips = data_manager.get_delivery_zip_codes(selected_deliveries)
            selected_pickups = scheduler.find_nearby_pickups(delivery_zips, max_pickups=3)
            
            # Generate optimized route
            if st.button("🚀 Generate Optimized Route", use_container_width=True):
                with st.spinner("Geocoding addresses and optimizing route..."):
                    # Set warehouse location
                    warehouse_coords = route_optimizer.set_warehouse(TFP_WAREHOUSE_ADDRESS)
                    
                    if not warehouse_coords:
                        st.error("Could not geocode warehouse address")
                        st.stop()
                    
                    # Prepare column mappings
                    delivery_cols = {
                        'name': data_manager.name_col_del,
                        'address': data_manager.address_col_del,  # Use actual address column if available
                        'zip': data_manager.zip_col_del,
                        'phone': data_manager.phone_col_del,
                        'notes': data_manager.comments_col_del
                    }
                    
                    pickup_cols = {
                        'name': data_manager.pickup_name_col,
                        'address': data_manager.pickup_address_col,
                        'phone': data_manager.pickup_phone_col,
                        'items': data_manager.pickup_items_col
                    }
                    
                    # Generate route with times using scheduler
                    route_df = scheduler.generate_route(
                        pd.DataFrame(selected_deliveries),
                        selected_pickups,
                        TFP_WAREHOUSE_ADDRESS
                    )
                    
                    if route_df.empty:
                        st.error("Could not generate route")
                        st.stop()
                    
                    # Store route in session state
                    route_data = {
                        'date': selected_route_date,
                        'route_df': route_df,
                        'distance': 25.0  # Placeholder distance
                    }
                    st.session_state['current_route'] = route_data
                    
                    st.success(f"✅ Route prepared! Approximate distance: {route_data['distance']:.1f} miles")
                    st.info("💡 **Next Step**: Click 'Optimize in Google Maps' below to get the truly optimal route using Google's routing engine")
            
            # Display current route if available
            if 'current_route' in st.session_state:
                route_data = st.session_state['current_route']
                
                st.subheader(f"🗺️ Optimized Route for {route_data['date']}")
                
                # Route metrics from DataFrame
                route_df = route_data['route_df']
                deliveries = len(route_df[route_df['Type'] == '🚚 DELIVERY'])
                pickups = len(route_df[route_df['Type'] == '📦 PICKUP'])
                total_stops = len(route_df) - 2  # Exclude START and END
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Stops", total_stops)
                col2.metric("Deliveries", deliveries)
                col3.metric("Pickups", pickups)
                
                st.info(f"**Approximate Distance**: {route_data['distance']:.1f} miles")
                st.warning("⚠️ **Important**: This is just the initial route. Use Google Maps optimization below for the truly optimal route.")
                
                with st.expander("💡 Why Google Maps Optimization?"):
                    st.markdown("""
                    **Google Maps has advantages no algorithm can match:**
                    1. **Real-time traffic data** from millions of users
                    2. **Complete road network** including restrictions and closures
                    3. **Turn-by-turn optimization** considering actual driving patterns
                    4. **Time-of-day routing** that adapts to traffic conditions
                    5. **Local knowledge** of construction, accidents, and road conditions
                    
                    **Result**: Google Maps will give you the most efficient route possible.
                    """)
                
                # Display route with times
                st.subheader("📍 Route Schedule with Times")
                
                # Display the route DataFrame with times
                route_df = route_data['route_df']
                st.dataframe(route_df, use_container_width=True, hide_index=True)
                
                # Also show detailed view
                st.subheader("📍 Detailed Route")
                for idx, row in route_df.iterrows():
                    if row['Type'] in ['🏭 START', '🏭 END']:
                        st.write(f"**{row['Time']}** - {row['Type']} - {row['Location']}")
                    else:
                        with st.expander(f"**{row['Time']}** - {row['Type']} - {row['Details']}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Location:** {row['Location']}")
                                st.write(f"**Contact:** {row['Contact']}")
                            with col2:
                                st.write(f"**Notes:** {row['Notes']}")
                
                # Action buttons
                st.subheader("📋 Route Actions")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Download manifest from route DataFrame
                    route_df = route_data['route_df']
                    manifest_data = []
                    for idx, row in route_df.iterrows():
                        if row['Type'] not in ['🏭 START', '🏭 END']:
                            manifest_data.append({
                                'Stop': row['Stop'],
                                'Type': row['Type'],
                                'Name': row['Details'],
                                'Address': row['Location'],
                                'Phone': row['Contact'],
                                'Notes': row['Notes'],
                                'Time': row['Time'],
                                'Signature': '_______________'
                            })
                    
                    manifest_df = pd.DataFrame(manifest_data)
                    manifest_csv = manifest_df.to_csv(index=False)
                    
                    st.download_button(
                        "📋 Download Manifest",
                        manifest_csv,
                        f"manifest_{selected_route_date.replace('/', '_')}.csv",
                        "text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    # Google Calendar integration
                    if st.button("📅 Add to Google Calendar", use_container_width=True):
                        import urllib.parse
                        from datetime import datetime
                        
                        # Create event title
                        event_title = f"Furniture Project Delivery Route - {route_data['date']}"
                        
                        # Create detailed description from route DataFrame
                        route_df = route_data['route_df']
                        event_details = f"Furniture Project Delivery Route\n\nDate: {route_data['date']}\nStops: {total_stops} ({deliveries} deliveries, {pickups} pickups)\nEstimated Distance: {route_data['distance']:.1f} miles\n\nRoute Details:\n\n"
                        
                        for idx, row in route_df.iterrows():
                            event_details += f"{row['Time']} - {row['Type']}\n"
                            if row['Type'] not in ['🏭 START', '🏭 END']:
                                event_details += f"Name: {row['Details']}\nLocation: {row['Location']}\nContact: {row['Contact']}\n"
                                if row['Notes']:
                                    event_details += f"Notes: {row['Notes']}\n"
                            event_details += "\n"
                        
                        # Convert date string to datetime object
                        try:
                            # Handle different date formats
                            if '/' in route_data['date']:
                                route_date_obj = datetime.strptime(route_data['date'], '%m/%d/%Y')
                            else:
                                route_date_obj = datetime.strptime(route_data['date'], '%Y-%m-%d')
                        except ValueError:
                            # Fallback to today's date if parsing fails
                            route_date_obj = datetime.now()
                            st.warning("Could not parse date, using today's date")
                        
                        # Format for Google Calendar (YYYYMMDDTHHMMSS)
                        start_datetime = route_date_obj.strftime('%Y%m%dT090000')  # 9:00 AM
                        end_datetime = route_date_obj.strftime('%Y%m%dT143000')    # 2:30 PM
                        
                        # URL encode all parameters
                        encoded_title = urllib.parse.quote(event_title)
                        encoded_details = urllib.parse.quote(event_details)
                        encoded_location = urllib.parse.quote(TFP_WAREHOUSE_ADDRESS)
                        
                        # Create Google Calendar URL
                        calendar_url = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={encoded_title}&dates={start_datetime}/{end_datetime}&details={encoded_details}&location={encoded_location}"
                        
                        st.markdown(f"[📅 Open Google Calendar]({calendar_url})")
                        st.success("✅ Click the link above to add to your Google Calendar!")
                        st.info(f"📅 Event scheduled for {route_date_obj.strftime('%A, %B %d, %Y')} from 9:00 AM to 2:30 PM")
                
                with col3:
                    # Google Maps optimization
                    if st.button("🗺️ Optimize in Google Maps", use_container_width=True):
                        # Convert route DataFrame back to stops format for Google Maps
                        route_df = route_data['route_df']
                        stops = []
                        
                        for idx, row in route_df.iterrows():
                            if row['Type'] not in ['🏭 START', '🏭 END']:
                                stops.append({
                                    'address': row['Location'],
                                    'name': row['Details'],
                                    'type': 'delivery' if '🚚' in row['Type'] else 'pickup'
                                })
                        
                        # Create Google Maps URL
                        maps_url = route_optimizer.create_google_maps_route_url(stops, TFP_WAREHOUSE_ADDRESS)
                        
                        st.markdown(f"[🗺️ Open Optimized Route in Google Maps]({maps_url})")
                        st.success("✅ Google Maps will automatically optimize this route for you!")
                        st.info("💡 **Tip**: Google Maps uses real-time traffic data and knows all the roads - this will be your most efficient route")
                
                # Map visualization
                if st.checkbox("🗺️ Show Route Map"):
                    route_coords = []
                    route_labels = []
                    
                    # Add warehouse start
                    if route_optimizer.warehouse_coords:
                        route_coords.append(route_optimizer.warehouse_coords)
                        route_labels.append(f"START: Warehouse")
                    
                    # Add route stops with valid coordinates
                    route_df = route_data['route_df']
                    for idx, row in route_df.iterrows():
                        if row['Type'] not in ['🏭 START', '🏭 END']:
                            # Try to geocode the location for mapping
                            coords = geocoder.geocode_address(row['Location'])
                            if coords:
                                route_coords.append(coords)
                                route_labels.append(f"{row['Time']} - {row['Details']} ({row['Type']})")
                    
                    # Add warehouse return
                    if route_optimizer.warehouse_coords:
                        route_coords.append(route_optimizer.warehouse_coords)
                        route_labels.append("END: Return to Warehouse")
                    
                    if len(route_coords) > 1:
                        try:
                            route_map = map_viz.create_route_map(route_coords, route_labels)
                            map_viz.display_map(route_map)
                        except Exception as e:
                            st.error(f"Could not display map: {e}")
                            st.info("Some addresses could not be geocoded for mapping")
                    else:
                        st.warning("Not enough valid coordinates to display map - try geocoding the addresses first")
                


# --- TAB 3: OVERDUE REQUESTS ---
with tab3:
    st.header("⚠️ Overdue Delivery Requests")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        days_threshold = st.number_input(
            "Days Waiting Threshold",
            min_value=14,
            max_value=120,
            value=56,
            step=7,
            help="Show requests waiting longer than this many days (default: 8 weeks)"
        )
    
    with col2:
        st.info(f"**Policy**: Typical wait time is 6-8 weeks. Showing requests waiting **{days_threshold}+ days**.")
    
    # Get overdue requests
    overdue_df = scheduler.get_overdue_requests(days_threshold)
    
    if overdue_df.empty:
        st.success("✅ No overdue requests! All clients are within the expected wait time.")
    else:
        st.warning(f"**{len(overdue_df)} requests** are overdue and need immediate attention")
        
        # Display overdue requests
        for idx, row in overdue_df.head(20).iterrows():
            days_waiting = row.get('days_waiting', 'N/A')
            name = row.get(data_manager.name_col_del, 'Unknown') if data_manager.name_col_del else 'Unknown'
            zip_code = row.get(data_manager.zip_col_del, 'N/A') if data_manager.zip_col_del else 'N/A'
            phone = row.get(data_manager.phone_col_del, 'N/A') if data_manager.phone_col_del else 'N/A'
            
            with st.expander(f"🔴 **{name}** - Waiting {days_waiting} days (Zip: {zip_code})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Name:** {name}")
                    st.write(f"**Phone:** {phone}")
                    st.write(f"**Zip:** {zip_code}")
                    st.write(f"**Days Waiting:** {days_waiting}")
                
                with col2:
                    if data_manager.choice1_col_del:
                        st.write(f"**1st Choice:** {row.get(data_manager.choice1_col_del, 'N/A')}")
                    if data_manager.choice2_col_del:
                        st.write(f"**2nd Choice:** {row.get(data_manager.choice2_col_del, 'N/A')}")
                    if data_manager.choice3_col_del:
                        st.write(f"**3rd Choice:** {row.get(data_manager.choice3_col_del, 'N/A')}")
                    if data_manager.choice4_col_del:
                        st.write(f"**4th Choice:** {row.get(data_manager.choice4_col_del, 'N/A')}")
                
                if data_manager.comments_col_del and pd.notna(row.get(data_manager.comments_col_del)):
                    st.write(f"**Notes:** {row[data_manager.comments_col_del]}")
                
                st.button(f"📞 Mark as Contacted", key=f"contact_{idx}")

# --- TAB 4: ANALYTICS ---
with tab4:
    st.header("📈 Scheduling Analytics & Data Visualizations")
    
    # Key metrics
    delivery_stats = data_manager.get_delivery_stats()
    pickup_stats = data_manager.get_pickup_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    fulfillment_rate = (delivery_stats['scheduled'] / delivery_stats['total'] * 100) if delivery_stats['total'] > 0 else 0
    
    col1.metric(
        "Fulfillment Rate",
        f"{fulfillment_rate:.1f}%",
        f"{delivery_stats['scheduled']} of {delivery_stats['total']}"
    )
    
    col2.metric(
        "Pending Deliveries",
        delivery_stats['unscheduled']
    )
    
    col3.metric(
        "Pending Pickups",
        pickup_stats['unscheduled']
    )
    
    col4.metric(
        "Estimated Routes Needed",
        f"{delivery_stats['unscheduled'] // 4}"
    )
    
    st.divider()
    
    # DATA VISUALIZATIONS
    col1, col2 = st.columns(2)
    
    with col1:
        # Geographic Distribution
        st.subheader("🗺️ Geographic Distribution")
        if data_manager.zip_col_del and data_manager.self_schedule_df is not None:
            zip_counts = data_manager.self_schedule_df[data_manager.zip_col_del].value_counts().head(10)
            if not zip_counts.empty:
                st.bar_chart(zip_counts)
                st.caption("Top 10 zip codes by request volume")
            else:
                st.info("No zip code data available")
    
    with col2:
        # Wait Time Distribution
        st.subheader("⏱️ Wait Time Analysis")
        if 'Timestamp' in data_manager.self_schedule_df.columns:
            df_copy = data_manager.self_schedule_df.copy()
            df_copy['request_date'] = pd.to_datetime(df_copy['Timestamp'], errors='coerce')
            df_copy['days_waiting'] = (datetime.now() - df_copy['request_date']).dt.days
            
            # Create wait time bins
            bins = [0, 14, 28, 42, 56, 70, 999]
            labels = ['0-2 weeks', '2-4 weeks', '4-6 weeks', '6-8 weeks', '8-10 weeks', '10+ weeks']
            df_copy['wait_category'] = pd.cut(df_copy['days_waiting'], bins=bins, labels=labels, right=False)
            
            wait_counts = df_copy['wait_category'].value_counts()
            if not wait_counts.empty:
                st.bar_chart(wait_counts)
                st.caption("Distribution of client wait times")
            else:
                st.info("No timestamp data available")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Request Volume Trends
        st.subheader("📈 Request Volume Trends")
        if 'Timestamp' in data_manager.self_schedule_df.columns:
            timestamp_df = data_manager.self_schedule_df.copy()
            timestamp_df['request_date'] = pd.to_datetime(timestamp_df['Timestamp'], errors='coerce')
            timestamp_df['week'] = timestamp_df['request_date'].dt.to_period('W')
            
            weekly_counts = timestamp_df.groupby('week').size()
            if not weekly_counts.empty:
                st.line_chart(weekly_counts)
                st.caption("Weekly request volume over time")
            else:
                st.info("No timestamp data for trends")
    
    with col2:
        # Scheduling Efficiency
        st.subheader("🎯 Scheduling Efficiency")
        if data_manager.scheduled_col_del:
            scheduled_df = data_manager.self_schedule_df.copy()
            scheduled_df['is_scheduled'] = scheduled_df[data_manager.scheduled_col_del].notna() & (scheduled_df[data_manager.scheduled_col_del] != '')
            
            efficiency_data = {
                'Scheduled': scheduled_df['is_scheduled'].sum(),
                'Unscheduled': (~scheduled_df['is_scheduled']).sum()
            }
            
            if sum(efficiency_data.values()) > 0:
                # Create pie chart data
                chart_data = pd.DataFrame(list(efficiency_data.items()), columns=['Status', 'Count'])
                st.bar_chart(chart_data.set_index('Status'))
                st.caption("Scheduled vs Unscheduled requests")
            else:
                st.info("No scheduling data available")
    
    st.divider()
    
    # Coverage gaps with enhanced visualization
    st.subheader("📍 Coverage Gaps Analysis")
    gaps = data_manager.get_coverage_gaps()
    
    if gaps:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.warning(f"**{len(gaps)} zip codes** have pending requests but no recent deliveries")
            
            # Show gap analysis chart
            if data_manager.zip_col_del:
                all_zips = data_manager.self_schedule_df[data_manager.zip_col_del].value_counts()
                gap_zips = {zip_code: all_zips.get(zip_code, 0) for zip_code in gaps[:10]}
                
                if gap_zips:
                    gap_df = pd.DataFrame(list(gap_zips.items()), columns=['Zip Code', 'Pending Requests'])
                    st.bar_chart(gap_df.set_index('Zip Code'))
                    st.caption("Pending requests in underserved zip codes")
        
        with col2:
            st.write("**Top Underserved Areas:**")
            for i, zip_code in enumerate(gaps[:10], 1):
                count = data_manager.self_schedule_df[data_manager.zip_col_del].value_counts().get(zip_code, 0)
                st.write(f"{i}. **{zip_code}** ({count} requests)")
        
        # Show coverage map
        if st.checkbox("Show Coverage Map"):
            try:
                coverage_map = map_viz.create_coverage_map(
                    data_manager.self_schedule_df,
                    data_manager.zip_col_del,
                    geocoder
                )
                map_viz.display_map(coverage_map)
            except Exception as e:
                st.error(f"Could not display coverage map: {e}")
                st.info("Some zip codes could not be geocoded for mapping")
    else:
        st.success("✅ All zip codes with requests have recent deliveries scheduled")
    
    st.divider()
    
    # Additional insights
    st.subheader("💡 Key Insights")
    
    insights = []
    
    # Average wait time
    if 'Timestamp' in data_manager.self_schedule_df.columns:
        df_copy = data_manager.self_schedule_df.copy()
        df_copy['request_date'] = pd.to_datetime(df_copy['Timestamp'], errors='coerce')
        df_copy['days_waiting'] = (datetime.now() - df_copy['request_date']).dt.days
        avg_wait = df_copy['days_waiting'].mean()
        if pd.notna(avg_wait):
            insights.append(f"⏱️ Average wait time: **{avg_wait:.1f} days** ({avg_wait/7:.1f} weeks)")
    
    # Busiest zip codes
    if data_manager.zip_col_del:
        top_zip = data_manager.self_schedule_df[data_manager.zip_col_del].value_counts().head(1)
        if not top_zip.empty:
            insights.append(f"📍 Busiest area: **{top_zip.index[0]}** with {top_zip.iloc[0]} requests")
    
    # Efficiency rate
    if fulfillment_rate > 0:
        if fulfillment_rate >= 80:
            insights.append(f"🎯 Excellent scheduling efficiency: **{fulfillment_rate:.1f}%** of requests scheduled")
        elif fulfillment_rate >= 60:
            insights.append(f"🟡 Good scheduling efficiency: **{fulfillment_rate:.1f}%** of requests scheduled")
        else:
            insights.append(f"🔴 Low scheduling efficiency: **{fulfillment_rate:.1f}%** of requests scheduled - consider more routes")
    
    # Coverage gaps insight
    if gaps:
        insights.append(f"⚠️ Service gaps: **{len(gaps)} zip codes** need attention for equitable coverage")
    
    for insight in insights:
        st.write(f"• {insight}")
    
    st.divider()
    
    # REPORTS & TABLES SECTION
    st.subheader("📄 Reports & Tables")
    
    report_tabs = st.tabs([
        "📊 Summary Tables",
        "🗺️ Geographic Report", 
        "⏱️ Wait Time Report",
        "📅 Scheduling Report"
    ])
    
    with report_tabs[0]:
        st.subheader("📊 Summary Statistics Table")
        
        # Create comprehensive summary table
        summary_data = {
            'Metric': [
                'Total Delivery Requests',
                'Scheduled Deliveries', 
                'Pending Deliveries',
                'Total Pickup Requests',
                'Scheduled Pickups',
                'Pending Pickups',
                'Fulfillment Rate (%)',
                'Estimated Routes Needed',
                'Underserved Zip Codes',
                'Average Wait Time (days)'
            ],
            'Value': [
                delivery_stats['total'],
                delivery_stats['scheduled'],
                delivery_stats['unscheduled'],
                pickup_stats['total'],
                pickup_stats['scheduled'], 
                pickup_stats['unscheduled'],
                f"{fulfillment_rate:.1f}%",
                delivery_stats['unscheduled'] // 4,
                len(gaps) if gaps else 0,
                f"{avg_wait:.1f}" if 'avg_wait' in locals() and pd.notna(avg_wait) else 'N/A'
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        
        # Download button for summary
        csv_summary = summary_df.to_csv(index=False)
        st.download_button(
            "📎 Download Summary Report",
            csv_summary,
            "tfp_summary_report.csv",
            "text/csv",
            use_container_width=True
        )
    
    with report_tabs[1]:
        st.subheader("🗺️ Geographic Distribution Report")
        
        if data_manager.zip_col_del and data_manager.self_schedule_df is not None:
            # Create detailed geographic report
            geo_df = data_manager.self_schedule_df.copy()
            
            # Group by zip code
            zip_summary = geo_df.groupby(data_manager.zip_col_del).agg({
                data_manager.name_col_del: 'count',
                data_manager.scheduled_col_del: lambda x: x.notna().sum() if data_manager.scheduled_col_del else 0
            }).reset_index()
            
            zip_summary.columns = ['Zip Code', 'Total Requests', 'Scheduled']
            zip_summary['Pending'] = zip_summary['Total Requests'] - zip_summary['Scheduled']
            zip_summary['Fulfillment Rate (%)'] = (zip_summary['Scheduled'] / zip_summary['Total Requests'] * 100).round(1)
            zip_summary['Status'] = zip_summary['Zip Code'].apply(lambda x: '⚠️ Underserved' if str(x) in gaps else '✅ Served')
            
            # Sort by total requests
            zip_summary = zip_summary.sort_values('Total Requests', ascending=False)
            
            st.dataframe(zip_summary, use_container_width=True, hide_index=True)
            
            # Download button
            csv_geo = zip_summary.to_csv(index=False)
            st.download_button(
                "📎 Download Geographic Report",
                csv_geo,
                "tfp_geographic_report.csv",
                "text/csv",
                use_container_width=True
            )
        else:
            st.info("No geographic data available")
    
    with report_tabs[2]:
        st.subheader("⏱️ Wait Time Analysis Report")
        
        if 'Timestamp' in data_manager.self_schedule_df.columns:
            wait_df = data_manager.self_schedule_df.copy()
            wait_df['request_date'] = pd.to_datetime(wait_df['Timestamp'], errors='coerce')
            wait_df['days_waiting'] = (datetime.now() - wait_df['request_date']).dt.days
            
            # Create wait time categories
            bins = [0, 14, 28, 42, 56, 70, 999]
            labels = ['0-2 weeks', '2-4 weeks', '4-6 weeks', '6-8 weeks', '8-10 weeks', '10+ weeks']
            wait_df['wait_category'] = pd.cut(wait_df['days_waiting'], bins=bins, labels=labels, right=False)
            
            # Create summary table
            wait_summary = wait_df.groupby('wait_category').agg({
                data_manager.name_col_del: 'count',
                'days_waiting': ['min', 'max', 'mean']
            }).round(1)
            
            wait_summary.columns = ['Count', 'Min Days', 'Max Days', 'Avg Days']
            wait_summary = wait_summary.reset_index()
            wait_summary['Percentage'] = (wait_summary['Count'] / wait_summary['Count'].sum() * 100).round(1)
            
            # Add status indicators
            wait_summary['Status'] = wait_summary['wait_category'].apply(
                lambda x: '✅ On Track' if x in ['0-2 weeks', '2-4 weeks', '4-6 weeks'] 
                else '🟡 Approaching Limit' if x == '6-8 weeks'
                else '🔴 Overdue'
            )
            
            st.dataframe(wait_summary, use_container_width=True, hide_index=True)
            
            # Detailed overdue list
            overdue_clients = wait_df[wait_df['days_waiting'] > 56].copy()
            if not overdue_clients.empty:
                st.subheader("🔴 Overdue Clients (8+ weeks)")
                
                overdue_report = overdue_clients[[
                    data_manager.name_col_del,
                    data_manager.zip_col_del,
                    data_manager.phone_col_del,
                    'days_waiting'
                ]].copy()
                
                overdue_report.columns = ['Client Name', 'Zip Code', 'Phone', 'Days Waiting']
                overdue_report = overdue_report.sort_values('Days Waiting', ascending=False)
                
                st.dataframe(overdue_report, use_container_width=True, hide_index=True)
                
                # Download overdue list
                csv_overdue = overdue_report.to_csv(index=False)
                st.download_button(
                    "📎 Download Overdue Clients List",
                    csv_overdue,
                    "tfp_overdue_clients.csv",
                    "text/csv",
                    use_container_width=True
                )
            
            # Download wait time report
            csv_wait = wait_summary.to_csv(index=False)
            st.download_button(
                "📎 Download Wait Time Report",
                csv_wait,
                "tfp_wait_time_report.csv",
                "text/csv",
                use_container_width=True
            )
        else:
            st.info("No timestamp data available for wait time analysis")
    
    with report_tabs[3]:
        st.subheader("📅 Scheduling Performance Report")
        
        if data_manager.scheduled_col_del:
            sched_df = data_manager.self_schedule_df.copy()
            
            # Create scheduling report by date preferences
            choice_cols = [data_manager.choice1_col_del, data_manager.choice2_col_del, 
                          data_manager.choice3_col_del, data_manager.choice4_col_del]
            
            scheduling_data = []
            
            for i, choice_col in enumerate(choice_cols, 1):
                if choice_col:
                    choice_requests = sched_df[sched_df[choice_col].notna()]
                    scheduled_on_choice = choice_requests[choice_requests[data_manager.scheduled_col_del] == choice_requests[choice_col]]
                    
                    scheduling_data.append({
                        'Choice Rank': f'{i}{["st", "nd", "rd", "th"][min(i-1, 3)]} Choice',
                        'Total Requests': len(choice_requests),
                        'Scheduled on Preferred Date': len(scheduled_on_choice),
                        'Success Rate (%)': round(len(scheduled_on_choice) / len(choice_requests) * 100, 1) if len(choice_requests) > 0 else 0
                    })
            
            if scheduling_data:
                sched_report_df = pd.DataFrame(scheduling_data)
                st.dataframe(sched_report_df, use_container_width=True, hide_index=True)
                
                # Overall scheduling metrics
                st.subheader("🎯 Overall Scheduling Metrics")
                
                total_scheduled = sched_df[data_manager.scheduled_col_del].notna().sum()
                total_requests = len(sched_df)
                
                metrics_data = {
                    'Metric': [
                        'Total Requests Received',
                        'Successfully Scheduled',
                        'Still Pending',
                        'Overall Success Rate (%)',
                        'Requests Scheduled on 1st Choice (%)',
                        'Requests Scheduled on Any Preferred Date (%)'
                    ],
                    'Value': [
                        total_requests,
                        total_scheduled,
                        total_requests - total_scheduled,
                        f"{(total_scheduled / total_requests * 100):.1f}%" if total_requests > 0 else "0%",
                        f"{sched_report_df.iloc[0]['Success Rate (%)']}%" if len(sched_report_df) > 0 else "N/A",
                        f"{sched_report_df['Success Rate (%)'].mean():.1f}%" if len(sched_report_df) > 0 else "N/A"
                    ]
                }
                
                metrics_df = pd.DataFrame(metrics_data)
                st.dataframe(metrics_df, use_container_width=True, hide_index=True)
                
                # Download scheduling report
                csv_sched = pd.concat([sched_report_df, pd.DataFrame([{}]), metrics_df]).to_csv(index=False)
                st.download_button(
                    "📎 Download Scheduling Report",
                    csv_sched,
                    "tfp_scheduling_report.csv",
                    "text/csv",
                    use_container_width=True
                )
            else:
                st.info("No scheduling preference data available")
        else:
            st.info("No scheduling data available")

# --- TAB 5: DATA VIEW ---
with tab5:
    st.header("📊 Data View - CSV Contents")
    
    # Data selector
    data_options = []
    if data_manager.self_schedule_df is not None:
        data_options.append("Delivery Requests")
    if data_manager.pickup_df is not None:
        data_options.append("Pickup Requests")
    if data_manager.assistance_df is not None:
        data_options.append("Assistance Requests")
    
    if not data_options:
        st.info("📁 No data loaded. Please upload CSV files in the sidebar.")
    else:
        selected_data = st.selectbox("Select Data to View", data_options)
        
        if selected_data == "Delivery Requests":
            st.subheader("📦 Delivery Self-Schedule Data")
            
            # Key columns for delivery data
            key_columns = []
            if data_manager.name_col_del:
                key_columns.append(data_manager.name_col_del)
            if data_manager.zip_col_del:
                key_columns.append(data_manager.zip_col_del)
            if data_manager.phone_col_del:
                key_columns.append(data_manager.phone_col_del)
            if data_manager.choice1_col_del:
                key_columns.append(data_manager.choice1_col_del)
            if data_manager.choice2_col_del:
                key_columns.append(data_manager.choice2_col_del)
            if data_manager.choice3_col_del:
                key_columns.append(data_manager.choice3_col_del)
            if data_manager.choice4_col_del:
                key_columns.append(data_manager.choice4_col_del)
            if data_manager.scheduled_col_del:
                key_columns.append(data_manager.scheduled_col_del)
            
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                show_scheduled = st.checkbox("Show Scheduled Only", False)
            with col2:
                show_unscheduled = st.checkbox("Show Unscheduled Only", False)
            
            # Filter data
            display_df = data_manager.self_schedule_df.copy()
            
            if show_scheduled and data_manager.scheduled_col_del:
                display_df = display_df[
                    display_df[data_manager.scheduled_col_del].notna() & 
                    (display_df[data_manager.scheduled_col_del] != '')
                ]
            elif show_unscheduled and data_manager.scheduled_col_del:
                display_df = display_df[
                    display_df[data_manager.scheduled_col_del].isna() | 
                    (display_df[data_manager.scheduled_col_del] == '')
                ]
            
            # Show relevant columns
            if key_columns:
                available_cols = [col for col in key_columns if col in display_df.columns]
                if available_cols:
                    st.dataframe(
                        display_df[available_cols].head(100),
                        use_container_width=True
                    )
                    
                    if len(display_df) > 100:
                        st.info(f"Showing first 100 of {len(display_df)} records")
                else:
                    st.dataframe(display_df.head(100), use_container_width=True)
            else:
                st.dataframe(display_df.head(100), use_container_width=True)
            
            # Summary stats
            st.subheader("📊 Summary")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Requests", len(display_df))
            
            if data_manager.scheduled_col_del:
                scheduled_count = len(display_df[
                    display_df[data_manager.scheduled_col_del].notna() & 
                    (display_df[data_manager.scheduled_col_del] != '')
                ])
                col2.metric("Scheduled", scheduled_count)
                col3.metric("Unscheduled", len(display_df) - scheduled_count)
        
        elif selected_data == "Pickup Requests":
            st.subheader("🔄 Pickup Request Data")
            
            # Filter options for pickups
            col1, col2, col3 = st.columns(3)
            with col1:
                show_scheduled_pickups = st.checkbox("Show Scheduled Only", False)
            with col2:
                show_unscheduled_pickups = st.checkbox("Show Unscheduled Only", False)
            with col3:
                show_december_pickups = st.checkbox("Show December Only", False)
            
            # Key columns for pickup data
            key_columns = []
            if data_manager.pickup_name_col:
                key_columns.append(data_manager.pickup_name_col)
            if data_manager.pickup_address_col:
                key_columns.append(data_manager.pickup_address_col)
            if data_manager.pickup_zip_col:
                key_columns.append(data_manager.pickup_zip_col)
            if data_manager.pickup_phone_col:
                key_columns.append(data_manager.pickup_phone_col)
            if data_manager.pickup_items_col:
                key_columns.append(data_manager.pickup_items_col)
            if hasattr(data_manager, 'pickup_estimated_col') and data_manager.pickup_estimated_col:
                key_columns.append(data_manager.pickup_estimated_col)
            if data_manager.pickup_scheduled_col:
                key_columns.append(data_manager.pickup_scheduled_col)
            
            # Filter data based on selections
            display_df = data_manager.pickup_df.copy()
            
            if show_scheduled_pickups and data_manager.pickup_scheduled_col:
                display_df = display_df[
                    display_df[data_manager.pickup_scheduled_col].notna() & 
                    (display_df[data_manager.pickup_scheduled_col] != '')
                ]
            elif show_unscheduled_pickups and data_manager.pickup_scheduled_col:
                display_df = display_df[
                    display_df[data_manager.pickup_scheduled_col].isna() | 
                    (display_df[data_manager.pickup_scheduled_col] == '')
                ]
            
            if show_december_pickups and hasattr(data_manager, 'pickup_estimated_col') and data_manager.pickup_estimated_col:
                display_df = display_df[
                    display_df[data_manager.pickup_estimated_col].str.contains('12/', na=False)
                ]
            
            if key_columns:
                available_cols = [col for col in key_columns if col in display_df.columns]
                if available_cols:
                    st.dataframe(
                        display_df[available_cols].head(100),
                        use_container_width=True
                    )
                else:
                    st.dataframe(display_df.head(100), use_container_width=True)
            else:
                st.dataframe(display_df.head(100), use_container_width=True)
            
            # Summary stats
            st.subheader("📊 Summary")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Pickups", len(display_df))
            
            if data_manager.pickup_scheduled_col:
                scheduled_count = len(display_df[
                    display_df[data_manager.pickup_scheduled_col].notna() & 
                    (display_df[data_manager.pickup_scheduled_col] != '')
                ])
                col2.metric("Scheduled", scheduled_count)
                col3.metric("Unscheduled", len(display_df) - scheduled_count)
        
        elif selected_data == "Assistance Requests":
            st.subheader("❓ Request Assistance Data")
            
            # Show assistance data
            display_df = data_manager.assistance_df.copy()
            st.dataframe(display_df.head(100), use_container_width=True)
            
            if len(display_df) > 100:
                st.info(f"Showing first 100 of {len(display_df)} records")
            
            st.metric("Total Assistance Requests", len(display_df))
        
        # Download options
        st.subheader("💾 Download Data")
        
        if selected_data == "Delivery Requests" and data_manager.self_schedule_df is not None:
            csv_data = display_df.to_csv(index=False)
            st.download_button(
                "Download Delivery Data as CSV",
                csv_data,
                "delivery_data.csv",
                "text/csv",
                use_container_width=True
            )
        
        elif selected_data == "Pickup Requests" and data_manager.pickup_df is not None:
            csv_data = display_df.to_csv(index=False)
            st.download_button(
                "Download Pickup Data as CSV",
                csv_data,
                "pickup_data.csv",
                "text/csv",
                use_container_width=True
            )
        
        elif selected_data == "Assistance Requests" and data_manager.assistance_df is not None:
            csv_data = display_df.to_csv(index=False)
            st.download_button(
                "Download Assistance Data as CSV",
                csv_data,
                "assistance_data.csv",
                "text/csv",
                use_container_width=True
            )

# --- TAB 6: HELP ---
with tab6:
    st.header("ℹ️ Help & Documentation")
    
    st.markdown("""
    ### 🚀 Getting Started
    
    1. **Upload Data**: Use the sidebar to upload your CSV files
    2. **Adjust Dates**: Use the date slider to move old dates forward
    3. **Set Warehouse**: Verify warehouse address in sidebar
    4. **Schedule Deliveries**: Go to the "Schedule Deliveries" tab
    5. **Optimize Routes**: Generate optimized routes in the "Optimized Routes" tab
    6. **Track Overdue**: Monitor overdue requests in the "Overdue Requests" tab
    
    ### 📋 Features
    
    - **Smart Scheduling**: Automatically matches deliveries to client preferences
    - **Google Maps Integration**: Uses Google's routing engine for true optimization
    - **Real-time Traffic**: Google Maps considers current traffic conditions
    - **Automatic Route Optimization**: Google Maps finds the most efficient route
    - **Overdue Tracking**: Identifies requests waiting longer than 8 weeks
    - **Interactive Maps**: See your route visualized on a map
    
    ### 🗺️ Google Maps Optimization
    
    **Why Google Maps is the best route optimizer:**
    - **Real-time traffic data** from millions of users worldwide
    - **Complete road database** including all streets, restrictions, and closures
    - **Machine learning algorithms** trained on billions of routes
    - **Turn-by-turn optimization** considering actual driving behavior
    - **Dynamic routing** that adapts to current conditions
    
    ### 🔧 How It Works
    
    1. **Prepare Route**: System selects deliveries and nearby pickups
    2. **Google Maps Optimization**: Click button to open route in Google Maps
    3. **Automatic Optimization**: Google Maps reorders stops for efficiency
    4. **Real-time Updates**: Route adapts to current traffic conditions
    5. **Turn-by-turn Navigation**: Follow optimized route with live guidance
    
    ### 📞 Support
    
    For questions or issues, contact the Furniture Project operations team.
    """)
    
    st.divider()
    
    with st.expander("🔗 Google Calendar Integration (FREE)"):
        st.markdown("""
        **Good news: Google Calendar integration is FREE!**
        
        The app uses simple URL-based calendar integration - no API keys needed!
        
        **How it works**:
        1. Generate a route in the "Optimized Routes" tab
        2. Click "Add to Google Calendar" button
        3. Browser opens Google Calendar with pre-filled event
        4. Review and save the event
        
        **What gets added**:
        - Complete route details with times and addresses
        - All stops listed in event description
        - Proper time blocks (9:30 AM - estimated end)
        - Warehouse location as event location
        
        **Cost**: $0.00 - uses standard Google Calendar web interface
        """)
    
    with st.expander("🗺️ Google Maps Integration"):
        st.markdown("""
        **How Google Maps Optimization Works:**
        1. System prepares your delivery and pickup stops
        2. Creates Google Maps URL with optimization enabled
        3. Google Maps automatically reorders stops for efficiency
        4. Uses real-time traffic data for optimal routing
        5. Provides turn-by-turn navigation with live updates
        
        **Advantages:**
        - No API keys or costs required
        - Uses Google's world-class routing algorithms
        - Considers real-time traffic and road conditions
        - Automatically handles road closures and restrictions
        """)
    
    with st.expander("📦 Required Package Installation"):
        st.code("""
pip install streamlit pandas geopy folium streamlit-folium openpyxl
        """, language="bash")
    
    with st.expander("📄 File Requirements"):
        st.markdown("""
        **Delivery Self-Schedule CSV** should contain:
        - First and Last Name
        - Address (full address preferred) or Zip Code  
        - Phone Number
        - 1st Choice through 4th Choice (dates)
        - Scheduled Date
        - Comments/Notes
        
        **Donor Pick Up CSV** should contain:
        - Name
        - Pick Up Address
        - Zip Code
        - Phone Number
        - Items List
        - Scheduled At
        """)