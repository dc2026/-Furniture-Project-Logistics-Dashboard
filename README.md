# Furniture Project Logistics Dashboard

A comprehensive Streamlit application for The Furniture Project to optimize delivery routes and manage furniture pickups efficiently in the Omaha, NE and Council Bluffs, IA area.

## Features

### 🚚 Smart Delivery Scheduling
- **Client Preference Matching**: Automatically matches deliveries to client-requested dates
- **Geographic Clustering**: Groups deliveries by zip code areas to minimize travel time
- **Overdue Request Tracking**: Identifies clients waiting longer than 8 weeks

### 🗺️ Route Optimization
- **Google Maps Integration**: Uses Google's routing engine for real-time traffic optimization
- **Equity-Aware Geographic Clustering Algorithm (EAGCA)**: Prevents back-and-forth travel between neighborhoods
- **Time-Based Scheduling**: Deliveries 9:45 AM - 12:00 PM, Pickups 1:00 PM - 2:30 PM

### 📊 Analytics & Reporting
- **Coverage Gap Analysis**: Identifies underserved zip codes
- **Wait Time Distribution**: Tracks client wait times and fulfillment rates
- **Geographic Reports**: Service area analysis with downloadable CSV reports
- **Interactive Visualizations**: Charts and maps for operational insights

### 📅 Calendar Integration
- **Free Google Calendar**: URL-based integration (no API keys required)
- **Route Manifests**: Downloadable delivery schedules with signatures
- **Time Management**: Proper scheduling within TFP operating hours (9:00 AM - 2:30 PM)

## Installation

1. **Clone the repository**
```bash
git clone https://github.com/dc2026/furniture-project-logistics-dashboard.git
cd furniture-project-logistics-dashboard
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
streamlit run src/app.py
```

## Usage

### Getting Started
1. **Upload Data**: Use the sidebar to upload your CSV files
2. **Set Warehouse**: Verify warehouse address (default: 10808 J St, Omaha, NE 68137)
3. **Schedule Deliveries**: Go to "Schedule Deliveries" tab
4. **Generate Routes**: Create optimized routes in "Optimized Routes" tab
5. **Track Performance**: Monitor analytics and overdue requests

### Required CSV Files

#### Delivery Self-Schedule CSV
- **Columns**: Timestamp, Name, Zip code, Phone, 1st Choice, 2nd Choice, 3rd Choice, 4th Choice, Scheduled Date
- **Format**: Dates in M/D/YYYY format

#### Pickup Requests CSV  
- **Columns**: Timestamp, Name, Pick Up Address, Zip Code, Phone Number, Items, Estimated Pick Up Date, Scheduled At
- **Format**: Full addresses with city and state (e.g., "1234 Main St Omaha NE")

#### Request Assistance CSV (Optional)
- **Columns**: Timestamp, Name, Email, Phone, Zip Code, Type of Assistance Needed, Description, Scheduled Date

### Key Workflow

1. **Auto-Select Deliveries**: System finds clients who requested specific dates
2. **Geographic Clustering**: Groups deliveries by 3-digit zip code areas
3. **Pickup Matching**: Finds 2-3 nearby pickups in same areas
4. **Route Generation**: Creates time-based schedule with Google Maps integration
5. **Calendar Export**: Add complete route to Google Calendar
6. **Google Maps Optimization**: Open route in Google Maps for real-time optimization

## Technical Architecture

### Project Structure
```
furniture-project-logistics-dashboard/
├── src/                    # Source code
│   ├── app.py             # Main Streamlit interface
│   ├── scheduler.py       # Delivery scheduling logic
│   ├── data_manager.py    # CSV data loading
│   ├── route_optimizer.py # Google Maps integration
│   ├── address_geocoder.py# Address geocoding
│   └── map_visualizer.py  # Interactive mapping
├── data/                  # Data files
│   └── sample_data/       # Sample CSV files
├── docs/                  # Documentation
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

### Key Algorithms
- **EAGCA (Equity-Aware Geographic Clustering Algorithm)**: Optimizes routes by completing all stops in one area before moving to the next
- **Date Preference Scoring**: Prioritizes client-requested dates with fallback options
- **Proximity-Based Pickup Selection**: Finds pickups near delivery locations

## Service Area

- **Primary**: Omaha, Nebraska (68xxx zip codes)
- **Secondary**: Council Bluffs, Iowa (51xxx zip codes)
- **Operating Hours**: 9:00 AM - 2:30 PM
- **Delivery Window**: 9:45 AM - 12:00 PM
- **Pickup Window**: 1:00 PM - 2:30 PM

## Google Maps Integration

The system leverages Google Maps for route optimization because:
- **Real-time traffic data** from millions of users
- **Complete road network** including restrictions and closures  
- **Machine learning algorithms** trained on billions of routes
- **Turn-by-turn optimization** considering actual driving patterns
- **No API costs** - uses standard Google Maps web interface

## Data Privacy & Security

- All client data remains local to your system
- No external APIs required for core functionality
- Google Maps integration uses public web interface only
- CSV files can be stored securely on local infrastructure

## Support

For questions or issues with the Furniture Project Logistics Dashboard, contact the TFP operations team.

## License

This project is developed for The Furniture Project's internal use.