import pandas as pd
from datetime import datetime, timedelta

class DataManager:
    """Handles all data loading, date offsetting, and column mapping"""
    
    def __init__(self):
        self.self_schedule_df = None
        self.pickup_df = None
        self.assistance_df = None  # NEW: Request Assistance form
        self.self_schedule_df_original = None
        self.pickup_df_original = None
        self.assistance_df_original = None
        
        # Delivery column mappings
        self.name_col_del = None
        self.zip_col_del = None
        self.scheduled_col_del = None
        self.choice1_col_del = None
        self.choice2_col_del = None
        self.choice3_col_del = None
        self.choice4_col_del = None
        self.phone_col_del = None
        self.comments_col_del = None
        
        # Pickup column mappings
        self.pickup_scheduled_col = None
        self.pickup_name_col = None
        self.pickup_address_col = None
        self.pickup_zip_col = None
        self.pickup_phone_col = None
        self.pickup_items_col = None
        
        # Request Assistance column mappings
        self.assist_name_col = None
        self.assist_email_col = None
        self.assist_phone_col = None
        self.assist_zip_col = None
        self.assist_scheduled_col = None
    
    def normalize_dates(self, df, target_columns):
        """Normalize date formats to handle both 2-digit and 4-digit years"""
        df = df.copy()
        
        for col in target_columns:
            if col not in df.columns:
                continue
            
            if 'comment' in col.lower():
                continue
            
            try:
                original_values = df[col].copy()
                # Handle multiple date formats
                date_series = pd.to_datetime(df[col], errors='coerce', infer_datetime_format=True)
                mask = date_series.notna()
                
                if mask.any():
                    # Normalize to consistent format
                    df.loc[mask, col] = date_series.loc[mask].dt.strftime('%-m/%-d/%Y')
                    df.loc[~mask, col] = original_values.loc[~mask]
            except Exception:
                pass
        
        return df
    
    def apply_date_offset(self, df, target_columns, months_offset):
        """Apply date offset to specific columns WITHOUT removing any data"""
        if months_offset == 0:
            return df
        
        df = df.copy()
        
        for col in target_columns:
            if col not in df.columns:
                continue
            
            if 'comment' in col.lower():
                continue
            
            try:
                original_values = df[col].copy()
                date_series = pd.to_datetime(df[col], errors='coerce', infer_datetime_format=True)
                mask = date_series.notna()
                
                if mask.any():
                    date_series.loc[mask] = date_series.loc[mask] + pd.DateOffset(months=months_offset)
                    df.loc[mask, col] = date_series.loc[mask].dt.strftime('%-m/%-d/%Y')
                    df.loc[~mask, col] = original_values.loc[~mask]
            except Exception:
                pass
        
        return df
    
    def load_self_schedule(self, file, months_offset=0):
        """Load and process self-schedule delivery data"""
        self.self_schedule_df_original = pd.read_csv(file)
        self.self_schedule_df = self.self_schedule_df_original.copy()
        
        # Map columns dynamically
        self.name_col_del = next((col for col in self.self_schedule_df.columns 
                                  if col.strip().lower() == 'name' or ('first and' in col.lower() and 'last name' in col.lower())), None)
        self.zip_col_del = next((col for col in self.self_schedule_df.columns 
                                if 'zip' in col.lower() or ('verify' in col.lower() and 'address' in col.lower())), None)
        # Look for actual address column (not just zip)
        self.address_col_del = next((col for col in self.self_schedule_df.columns 
                                    if 'address' in col.lower() and 'verify' not in col.lower()), None)
        self.scheduled_col_del = next((col for col in self.self_schedule_df.columns 
                                       if col.strip().lower() == 'scheduled date'), None)
        
        # Since there's no scheduled date column in the new format, all deliveries are unscheduled
        if self.scheduled_col_del is None:
            self.self_schedule_df['Scheduled Date'] = ''
            self.scheduled_col_del = 'Scheduled Date'
        self.choice1_col_del = next((col for col in self.self_schedule_df.columns 
                                     if '1st choice' in col.lower()), None)
        self.choice2_col_del = next((col for col in self.self_schedule_df.columns 
                                     if '2nd choice' in col.lower()), None)
        self.choice3_col_del = next((col for col in self.self_schedule_df.columns 
                                     if '3rd choice' in col.lower()), None)
        self.choice4_col_del = next((col for col in self.self_schedule_df.columns 
                                     if '4th choice' in col.lower()), None)
        self.phone_col_del = next((col for col in self.self_schedule_df.columns 
                                   if 'phone' in col.lower()), None)
        self.comments_col_del = next((col for col in self.self_schedule_df.columns 
                                      if 'comments' in col.lower()), None)
        
        # Always normalize date formats first
        date_columns = [col for col in [
            self.choice1_col_del, 
            self.choice2_col_del, 
            self.choice3_col_del, 
            self.choice4_col_del,
            self.scheduled_col_del,
            'Timestamp'
        ] if col is not None and col in self.self_schedule_df.columns]
        
        self.self_schedule_df = self.normalize_dates(self.self_schedule_df, date_columns)
        
        if months_offset > 0:
            self.self_schedule_df = self.apply_date_offset(
                self.self_schedule_df, 
                date_columns, 
                months_offset
            )
            
            if self.scheduled_col_del and self.scheduled_col_del in self.self_schedule_df.columns:
                self.self_schedule_df[self.scheduled_col_del] = ''
    
    def load_pickups(self, file, months_offset=0):
        """Load and process pickup data"""
        self.pickup_df_original = pd.read_csv(file)
        self.pickup_df = self.pickup_df_original.copy()
        
        self.pickup_scheduled_col = next((col for col in self.pickup_df.columns 
                                          if 'scheduled at' in col.lower() or col.strip().lower() == 'scheduled date'), None)
        self.pickup_name_col = next((col for col in self.pickup_df.columns 
                                     if col.strip() == 'Name'), None)
        self.pickup_address_col = next((col for col in self.pickup_df.columns 
                                        if 'pick up address' in col.lower()), None)
        self.pickup_zip_col = next((col for col in self.pickup_df.columns 
                                    if col.strip() == 'Zip Code'), None)
        self.pickup_phone_col = next((col for col in self.pickup_df.columns 
                                      if 'phone number' in col.lower()), None)
        self.pickup_items_col = next((col for col in self.pickup_df.columns 
                                      if 'please list items' in col.lower()), None)
        self.pickup_estimated_col = next((col for col in self.pickup_df.columns 
                                          if 'estimated pick up date' in col.lower()), None)
        
        if months_offset > 0:
            date_columns = ['Timestamp']
            estimated_date_col = next((col for col in self.pickup_df.columns 
                                       if 'estimated pick up date' in col.lower()), None)
            if estimated_date_col:
                date_columns.append(estimated_date_col)
            
            self.pickup_df = self.apply_date_offset(self.pickup_df, date_columns, months_offset)
            
            if self.pickup_scheduled_col and self.pickup_scheduled_col in self.pickup_df.columns:
                self.pickup_df[self.pickup_scheduled_col] = ''
    
    def load_assistance(self, file, months_offset=0):
        """Load and process request assistance data"""
        self.assistance_df_original = pd.read_csv(file)
        self.assistance_df = self.assistance_df_original.copy()
        
        # Map columns - adjust based on your form structure
        self.assist_name_col = next((col for col in self.assistance_df.columns 
                                     if 'name' in col.lower()), None)
        self.assist_email_col = next((col for col in self.assistance_df.columns 
                                      if 'email' in col.lower()), None)
        self.assist_phone_col = next((col for col in self.assistance_df.columns 
                                      if 'phone' in col.lower()), None)
        self.assist_zip_col = next((col for col in self.assistance_df.columns 
                                    if 'zip' in col.lower()), None)
        self.assist_scheduled_col = next((col for col in self.assistance_df.columns 
                                          if col.strip().lower() == 'scheduled date'), None)
        
        if months_offset > 0:
            date_columns = ['Timestamp']
            self.assistance_df = self.apply_date_offset(self.assistance_df, date_columns, months_offset)
            
            if self.assist_scheduled_col:
                self.assistance_df[self.assist_scheduled_col] = ''
    
    def get_delivery_stats(self):
        """Get delivery statistics"""
        if self.self_schedule_df is None:
            return {'total': 0, 'scheduled': 0, 'unscheduled': 0}
        
        total = len(self.self_schedule_df)
        
        if self.scheduled_col_del:
            scheduled = self.self_schedule_df[
                self.self_schedule_df[self.scheduled_col_del].notna() & 
                (self.self_schedule_df[self.scheduled_col_del] != '')
            ]
            scheduled_count = len(scheduled)
        else:
            scheduled_count = 0
        
        return {
            'total': total,
            'scheduled': scheduled_count,
            'unscheduled': total - scheduled_count
        }
    
    def get_pickup_stats(self):
        """Get pickup statistics"""
        if self.pickup_df is None:
            return {'total': 0, 'scheduled': 0, 'unscheduled': 0}
        
        total = len(self.pickup_df)
        
        if self.pickup_scheduled_col:
            scheduled = self.pickup_df[
                self.pickup_df[self.pickup_scheduled_col].notna() & 
                (self.pickup_df[self.pickup_scheduled_col] != '')
            ]
            scheduled_count = len(scheduled)
        else:
            scheduled_count = 0
        
        return {
            'total': total,
            'scheduled': scheduled_count,
            'unscheduled': total - scheduled_count
        }
    
    def get_delivery_zip_codes(self, df):
        """Extract clean zip codes from delivery dataframe"""
        if self.zip_col_del is None or df.empty:
            return []
        
        zips = df[self.zip_col_del].astype(str).str.strip().str.split().str[0].tolist()
        return [z for z in zips if z and z != 'nan']
    
    def get_upcoming_deliveries(self, days_ahead=30):
        """Get deliveries scheduled in next N days"""
        if self.scheduled_col_del is None or self.self_schedule_df is None:
            return pd.DataFrame()
        
        future_date = datetime.now() + timedelta(days=days_ahead)
        scheduled = self.self_schedule_df[
            self.self_schedule_df[self.scheduled_col_del].notna() & 
            (self.self_schedule_df[self.scheduled_col_del] != '')
        ].copy()
        
        if len(scheduled) > 0:
            scheduled['scheduled_datetime'] = pd.to_datetime(
                scheduled[self.scheduled_col_del], 
                errors='coerce'
            )
            return scheduled[
                scheduled['scheduled_datetime'] <= future_date
            ].sort_values('scheduled_datetime')
        
        return pd.DataFrame()
    
    def get_coverage_gaps(self):
        """Identify zip codes with requests but no recent deliveries"""
        if self.zip_col_del is None or self.self_schedule_df is None:
            return []
        
        all_zips = self.self_schedule_df[self.zip_col_del].astype(str).str[:5].value_counts()
        recent_scheduled = self.get_upcoming_deliveries(days_ahead=-30)
        
        if len(recent_scheduled) > 0 and self.zip_col_del in recent_scheduled.columns:
            served_zips = recent_scheduled[self.zip_col_del].astype(str).str[:5].value_counts()
            gaps = all_zips[~all_zips.index.isin(served_zips.index)]
            return gaps.index.tolist()
        
        return all_zips.index.tolist()