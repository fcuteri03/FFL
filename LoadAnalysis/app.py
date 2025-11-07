"""
Streamlit Dashboard for Lane & Rate Analysis
Interactive web UI for TMS load data analysis.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from database_connection import DatabaseConnection
from datetime import datetime, timedelta
import os

# Increase pandas styler render limit for large dataframes
pd.set_option("styler.render.max_elements", 1000000)

# Page configuration
st.set_page_config(
    page_title="TMS Lane & Rate Analysis",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data():
    """Load data from database with caching, including LaneKey calculation."""
    # Create LaneKey in SQL: OriginCity,OriginState-DestinationCity,DestinationState,TrailerType
    # First extract city from OriginCityState (before comma) and state from OriginState
    query = """
    SELECT *,
        LTRIM(RTRIM(ISNULL(SUBSTRING(OriginCityState, 1, CHARINDEX(',', OriginCityState + ',') - 1), ''))) AS OriginCity_Extracted,
        LTRIM(RTRIM(ISNULL(OriginState, ''))) AS OriginState_Use,
        LTRIM(RTRIM(ISNULL(SUBSTRING(FinalCityState, 1, CHARINDEX(',', FinalCityState + ',') - 1), ''))) AS FinalCity_Extracted,
        LTRIM(RTRIM(ISNULL(FinalState, ''))) AS FinalState_Use,
        LTRIM(RTRIM(ISNULL(CAST(TrailerType AS NVARCHAR(200)), ''))) AS TrailerType_Use,
        LTRIM(RTRIM(ISNULL(SUBSTRING(OriginCityState, 1, CHARINDEX(',', OriginCityState + ',') - 1), ''))) + ',' +
        LTRIM(RTRIM(ISNULL(OriginState, ''))) + '-' +
        LTRIM(RTRIM(ISNULL(SUBSTRING(FinalCityState, 1, CHARINDEX(',', FinalCityState + ',') - 1), ''))) + ',' +
        LTRIM(RTRIM(ISNULL(FinalState, ''))) + ',' +
        LTRIM(RTRIM(ISNULL(CAST(TrailerType AS NVARCHAR(200)), ''))) AS LaneKey
    FROM [dbo].[ReportMasterDataSetCache]
    """
    
    db = DatabaseConnection()
    if not db.connect():
        st.error("Failed to connect to database. Please check your connection settings.")
        return None
    
    try:
        db.cursor.execute(query)
        query_columns = [column[0] for column in db.cursor.description]
        rows = db.cursor.fetchall()
        df = pd.DataFrame.from_records(rows, columns=query_columns)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None
    finally:
        db.disconnect()


@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_dat_data():
    """Load DAT rate data from DATRateviewSpotRateHistory table with LaneKey calculation."""
    # Map TruckType: v->Van, r->Reefer, f->Flatbed
    # Create LaneKey: OriginCity,OriginState-DestinationCity,DestinationState,TrailerType
    query = """
    SELECT *,
        CASE 
            WHEN LOWER(LTRIM(RTRIM(ISNULL(CAST(TruckType AS NVARCHAR(10)), '')))) = 'v' THEN 'Van'
            WHEN LOWER(LTRIM(RTRIM(ISNULL(CAST(TruckType AS NVARCHAR(10)), '')))) = 'r' THEN 'Reefer'
            WHEN LOWER(LTRIM(RTRIM(ISNULL(CAST(TruckType AS NVARCHAR(10)), '')))) = 'f' THEN 'Flatbed'
            ELSE LTRIM(RTRIM(ISNULL(CAST(TruckType AS NVARCHAR(200)), '')))
        END AS TrailerType_Mapped,
        LTRIM(RTRIM(ISNULL(CAST(OriginCity AS NVARCHAR(500)), ''))) + ',' +
        LTRIM(RTRIM(ISNULL(CAST(OriginState AS NVARCHAR(50)), ''))) + '-' +
        LTRIM(RTRIM(ISNULL(CAST(DestinationCity AS NVARCHAR(500)), ''))) + ',' +
        LTRIM(RTRIM(ISNULL(CAST(DestinationState AS NVARCHAR(50)), ''))) + ',' +
        CASE 
            WHEN LOWER(LTRIM(RTRIM(ISNULL(CAST(TruckType AS NVARCHAR(10)), '')))) = 'v' THEN 'Van'
            WHEN LOWER(LTRIM(RTRIM(ISNULL(CAST(TruckType AS NVARCHAR(10)), '')))) = 'r' THEN 'Reefer'
            WHEN LOWER(LTRIM(RTRIM(ISNULL(CAST(TruckType AS NVARCHAR(10)), '')))) = 'f' THEN 'Flatbed'
            ELSE LTRIM(RTRIM(ISNULL(CAST(TruckType AS NVARCHAR(200)), '')))
        END AS LaneKey
    FROM [dbo].[DATRateviewSpotRateHistory]
    """
    
    db = DatabaseConnection()
    if not db.connect():
        return None
    
    try:
        db.cursor.execute(query)
        columns = [column[0] for column in db.cursor.description]
        rows = db.cursor.fetchall()
        df_dat = pd.DataFrame.from_records(rows, columns=columns)
        return df_dat
    except Exception as e:
        st.warning(f"Could not load DAT data: {e}")
        return None
    finally:
        db.disconnect()


def map_truck_type_to_trailer(truck_type):
    """Map DAT truck type to TrailerType."""
    mapping = {
        'v': 'Van',
        'r': 'Reefer',
        'f': 'Flatbed'
    }
    return mapping.get(str(truck_type).lower(), str(truck_type))


def normalize_city_state(city_state_str):
    """Normalize city/state string for matching."""
    if pd.isna(city_state_str):
        return ''
    # Convert to string, strip, and normalize
    s = str(city_state_str).strip()
    # Remove extra spaces
    s = ' '.join(s.split())
    return s


def create_lane_key(origin_city, origin_state, dest_city, dest_state, trailer_type):
    """Create a composite key for lane matching: OriginCity,OriginState-DestinationCity,DestinationState,TrailerType"""
    # Normalize all components
    origin_city = normalize_city_state(origin_city)
    origin_state = normalize_city_state(origin_state)
    dest_city = normalize_city_state(dest_city)
    dest_state = normalize_city_state(dest_state)
    trailer_type = normalize_city_state(trailer_type)
    
    # Create key: OriginCity,OriginState-DestinationCity,DestinationState,TrailerType
    key = f"{origin_city},{origin_state}-{dest_city},{dest_state},{trailer_type}"
    return key


def merge_dat_data(df, df_dat):
    """Merge DAT rate data with load data using composite lane keys from SQL."""
    if df_dat is None or df_dat.empty:
        return df
    
    df = df.copy()
    df_dat = df_dat.copy()
    
    # Convert DAT data types
    numeric_dat_cols = ['SpotAvgLinehaulRate', 'SpotLowLinehaulRate', 'SpotHighLinehaulRate', 
                       'SpotTimeFrame', 'PcMilerPracticalMileage']
    for col in numeric_dat_cols:
        if col in df_dat.columns:
            df_dat[col] = pd.to_numeric(df_dat[col], errors='coerce')
    
    # Convert dates
    if 'DateCreated' in df_dat.columns:
        df_dat['DateCreated'] = pd.to_datetime(df_dat['DateCreated'], errors='coerce')
    
    if 'Created' in df.columns:
        df['Created'] = pd.to_datetime(df['Created'], errors='coerce')
    
    # Both dataframes should already have LaneKey from SQL queries
    # Normalize LaneKey to ensure exact matching (trim, uppercase for comparison)
    if 'LaneKey' in df.columns and 'LaneKey' in df_dat.columns:
        # Normalize keys for matching (case-insensitive, trimmed)
        df['LaneKey_Normalized'] = df['LaneKey'].astype(str).str.strip().str.upper()
        df_dat['LaneKey_Normalized'] = df_dat['LaneKey'].astype(str).str.strip().str.upper()
        
        # Deduplicate DAT data - keep only one record per LaneKey (prefer most recent DateCreated)
        # This prevents the merge from creating duplicate rows
        if 'DateCreated' in df_dat.columns:
            df_dat_dedup = df_dat.sort_values('DateCreated', ascending=False).drop_duplicates(
                subset=['LaneKey_Normalized'], 
                keep='first'
            )
        else:
            df_dat_dedup = df_dat.drop_duplicates(subset=['LaneKey_Normalized'], keep='first')
        
        # Merge on normalized key - left join ensures no new rows are created
        df_merged = df.merge(
            df_dat_dedup[['LaneKey_Normalized', 'SpotAvgLinehaulRate', 'SpotLowLinehaulRate', 'SpotHighLinehaulRate', 
                    'SpotTimeFrame', 'DateCreated', 'PcMilerPracticalMileage']],
            on='LaneKey_Normalized',
            how='left',
            suffixes=('', '_DAT')
        )
        
        # Verify no duplicates were created (should be same length as original df)
        if len(df_merged) != len(df):
            st.warning(f"Warning: Merge created {len(df_merged) - len(df)} duplicate rows. This should not happen.")
            # Remove duplicates if they exist, keeping first occurrence
            df_merged = df_merged.drop_duplicates(subset=df.columns.tolist(), keep='first')
        
        # Clean up normalized key column
        if 'LaneKey_Normalized' in df_merged.columns:
            df_merged = df_merged.drop(columns=['LaneKey_Normalized'])
    else:
        # Fallback: if LaneKey doesn't exist, return original df
        st.warning("LaneKey not found in dataframes. DAT matching may not work correctly.")
        return df
    
    # Clean up temporary columns that might have been created
    cleanup_cols = ['OriginCity_Extracted', 'FinalCity_Extracted', 
                    'OriginState_Extracted', 'FinalState_Extracted', 
                    'OriginState_Use', 'FinalState_Use', 'TrailerType_Use',
                    'TrailerType_Mapped']
    for col in cleanup_cols:
        if col in df_merged.columns:
            df_merged = df_merged.drop(columns=[col])
    
    return df_merged


def prepare_data(df, df_dat=None):
    """Prepare and calculate metrics for the data."""
    df = df.copy()
    
    # Convert Decimal types to float
    numeric_cols = ['RevenueTotal', 'BillTotal', 'PayTotal', 'Miles', 'Weight', 
                    'ExpenseTotal', 'CustomerDue', 'CarrierBalanceDue']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Filter valid data (keep negative revenue for analysis)
    df = df[df['Miles'] > 0]
    # Don't filter out negative revenue - we want to see it
    
    # Merge DAT data if available
    if df_dat is not None and not df_dat.empty:
        df = merge_dat_data(df, df_dat)
    
    # Create detailed lane identifier (Origin City/State → Destination City/State)
    df['Lane_Detailed'] = df['OriginCityState'].astype(str) + ' → ' + df['FinalCityState'].astype(str)
    df['Lane_StateToState'] = df['OriginState'].astype(str) + ' → ' + df['FinalState'].astype(str)
    df['Lane_CityToCity'] = df['OriginCityState'].astype(str) + ' → ' + df['FinalCityState'].astype(str)
    
    if 'Lane' in df.columns and df['Lane'].notna().any():
        df['Lane_Primary'] = df['Lane']
    else:
        df['Lane_Primary'] = df['Lane_Detailed']
    
    # Calculate metrics
    df['RatePerMile_Revenue'] = df['RevenueTotal'] / df['Miles'].replace(0, np.nan)
    df['RatePerMile_Customer'] = df['BillTotal'] / df['Miles'].replace(0, np.nan)
    df['RatePerMile_Carrier'] = df['PayTotal'] / df['Miles'].replace(0, np.nan)
    
    df['Weight_CWT'] = df['Weight'] / 100
    df['RatePerCWT_Revenue'] = df['RevenueTotal'] / df['Weight_CWT'].replace(0, np.nan)
    
    # Calculate Gross Margin directly from RevenueTotal and PayTotal
    df['GrossMargin'] = ((df['RevenueTotal'] - df['PayTotal']) / df['RevenueTotal'].replace(0, np.nan)) * 100
    
    df['CustomerCarrierSpread'] = df['BillTotal'] - df['PayTotal']
    df['SpreadPercentage'] = (df['CustomerCarrierSpread'] / df['BillTotal'].replace(0, np.nan)) * 100
    
    # Round all pay, bill, and revenue columns to 2 decimal places
    pay_bill_revenue_cols = ['RevenueTotal', 'BillTotal', 'PayTotal', 
                             'CustomerCarrierSpread', 'RatePerMile_Revenue', 'RatePerMile_Customer', 
                             'RatePerMile_Carrier', 'RatePerCWT_Revenue']
    for col in pay_bill_revenue_cols:
        if col in df.columns:
            df[col] = df[col].round(2)
    
    # Calculate DAT total pay (rate per mile * miles) - ignore fuel surcharge
    if 'SpotAvgLinehaulRate' in df.columns:
        df['DAT_AvgTotalPay'] = (df['SpotAvgLinehaulRate'] * df['Miles']).round(2)
        df['DAT_LowTotalPay'] = (df['SpotLowLinehaulRate'] * df['Miles']).round(2)
        df['DAT_HighTotalPay'] = (df['SpotHighLinehaulRate'] * df['Miles']).round(2)
        
        # Compare PayTotal vs DAT
        df['PayTotal_vs_DAT_Avg'] = (df['PayTotal'] - df['DAT_AvgTotalPay']).round(2)
        df['PayTotal_vs_DAT_Low'] = (df['PayTotal'] - df['DAT_LowTotalPay']).round(2)
        df['PayTotal_vs_DAT_High'] = (df['PayTotal'] - df['DAT_HighTotalPay']).round(2)
        
        # Rate per mile comparisons
        df['RatePerMile_vs_DAT_Avg'] = (df['RatePerMile_Carrier'] - df['SpotAvgLinehaulRate']).round(2)
        df['RatePerMile_vs_DAT_Low'] = (df['RatePerMile_Carrier'] - df['SpotLowLinehaulRate']).round(2)
        df['RatePerMile_vs_DAT_High'] = (df['RatePerMile_Carrier'] - df['SpotHighLinehaulRate']).round(2)
    
    # Date conversions
    if 'Created' in df.columns:
        df['Created'] = pd.to_datetime(df['Created'], errors='coerce')
        df['YearMonth'] = df['Created'].dt.to_period('M')
        df['Year'] = df['Created'].dt.year
        df['Month'] = df['Created'].dt.month
    
    if 'WeekStartDate' in df.columns:
        df['WeekStartDate'] = pd.to_datetime(df['WeekStartDate'], errors='coerce')
        df['YearWeek'] = df['WeekStartDate'].dt.to_period('W')
        df['WeekYear'] = df['WeekStartDate'].dt.isocalendar().year
    
    return df


def style_revenue(val):
    """Style function for revenue - negative in red."""
    if pd.isna(val):
        return ''
    if val < 0:
        return 'background-color: #ffcccc; color: #cc0000'
    return ''


def style_avg_revenue(val):
    """Style function for avg revenue - negative=red, 0-299.99=yellow, 300+=green."""
    if pd.isna(val):
        return ''
    if val < 0:
        return 'background-color: #ffcccc; color: #cc0000; font-weight: bold'
    elif val < 300:
        return 'background-color: #fff4cc; color: #cc9900; font-weight: bold'
    else:
        return 'background-color: #ccffcc; color: #006600; font-weight: bold'


def calc_low_excluding_zero(series):
    """Calculate the lowest value excluding zeros. If min is 0, return second lowest."""
    # Filter out zeros and NaN
    non_zero = series[(series != 0) & (series.notna())]
    
    if len(non_zero) == 0:
        # If all values are zero or NaN, return NaN
        return np.nan
    elif len(non_zero) == 1:
        # If only one non-zero value, return it
        return non_zero.min()
    else:
        # Get sorted unique values
        sorted_values = non_zero.sort_values().unique()
        # Return the minimum (first value in sorted array)
        return sorted_values[0]


def format_numeric_columns(df, exclude_cols=None):
    """Format numeric columns in dataframe to 2 decimal places for display."""
    if exclude_cols is None:
        exclude_cols = []
    
    df_formatted = df.copy()
    numeric_cols = df_formatted.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        if col not in exclude_cols:
            # Round to 2 decimal places but keep as numeric for calculations
            df_formatted[col] = df_formatted[col].round(2)
    
    return df_formatted


def format_chart_data(df, numeric_cols=None):
    """Round numeric columns in dataframe to 2 decimal places for chart display."""
    df_formatted = df.copy()
    if numeric_cols is None:
        numeric_cols = df_formatted.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        if col in df_formatted.columns:
            df_formatted[col] = df_formatted[col].round(2)
    
    return df_formatted


def main():
    """Main application."""
    st.markdown('<h1 class="main-header">🚛 TMS Lane & Rate Analysis Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar filters
    st.sidebar.header("📊 Filters & Controls")
    
    # Load data
    with st.spinner("Loading data from database..."):
        df_raw = load_data()
        df_dat_raw = load_dat_data()
    
    if df_raw is None or df_raw.empty:
        st.error("No data available. Please check your database connection.")
        return
    
    # Prepare data
    df = prepare_data(df_raw, df_dat_raw)
    
    # Show DAT data status
    if df_dat_raw is not None and not df_dat_raw.empty:
        dat_matched = df['SpotAvgLinehaulRate'].notna().sum()
        st.sidebar.info(f"📊 DAT Data: {dat_matched:,} loads matched with DAT rates")
    else:
        st.sidebar.warning("⚠️ DAT data not available")
    
    st.sidebar.success(f"✅ Loaded {len(df):,} loads")
    
    # Date range filter
    if 'Created' in df.columns and df['Created'].notna().any():
        min_date = df['Created'].min().date()
        max_date = df['Created'].max().date()
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        if len(date_range) == 2:
            df = df[(df['Created'].dt.date >= date_range[0]) & (df['Created'].dt.date <= date_range[1])]
    
    # State filter
    if 'OriginState' in df.columns:
        states = sorted(df['OriginState'].dropna().unique())
        selected_states = st.sidebar.multiselect("Origin States", states)
        if selected_states:
            df = df[df['OriginState'].isin(selected_states)]
    
    # Customer filter
    if 'CustomerName' in df.columns:
        customers = sorted(df['CustomerName'].dropna().unique())
        selected_customers = st.sidebar.multiselect("Customers", customers)
        if selected_customers:
            df = df[df['CustomerName'].isin(selected_customers)]
    
    # Trailer type filter
    if 'TrailerType' in df.columns:
        trailer_types = sorted(df['TrailerType'].dropna().unique())
        selected_trailers = st.sidebar.multiselect("Trailer Types", trailer_types)
        if selected_trailers:
            df = df[df['TrailerType'].isin(selected_trailers)]
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Overview", "🛣️ Lane Pivot Analysis", "💰 Rate Analysis", 
        "📈 Year-over-Year Trends", "👥 Customer/Carrier Analysis", "📋 Data Explorer"
    ])
    
    # Tab 1: Overview
    with tab1:
        st.header("📊 Overview Metrics")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Loads", f"{len(df):,}")
            st.metric("Total Revenue", f"${df['RevenueTotal'].sum():,.2f}")
        
        with col2:
            st.metric("Avg Rate/Mile", f"${df['RatePerMile_Revenue'].mean():.2f}")
            st.metric("Total Pay", f"${df['PayTotal'].sum():,.2f}")
        
        with col3:
            st.metric("Avg Margin", f"{df['GrossMargin'].mean():.2f}%")
            st.metric("Unique Lanes", f"{df['Lane_Detailed'].nunique():,}")
        
        with col4:
            st.metric("Unique Customers", f"{df['CustomerName'].nunique():,}")
            st.metric("Unique Carriers", f"{df['CarrierName'].nunique():,}")
        
        st.divider()
        
        # Top lanes chart
        st.subheader("Top 15 Lanes by Volume")
        lane_volume = df.groupby('Lane_Detailed').agg({
            'LoadDetailId': 'count',
            'RevenueTotal': 'sum'
        }).rename(columns={'LoadDetailId': 'LoadCount'}).sort_values('LoadCount', ascending=False).head(15)
        
        # Format numeric columns to 2 decimal places for chart
        lane_volume = format_chart_data(lane_volume.reset_index(), numeric_cols=['RevenueTotal'])
        
        fig = px.bar(
            lane_volume,
            x='Lane_Detailed',
            y='LoadCount',
            title="Load Count by Lane",
            labels={'Lane_Detailed': 'Lane', 'LoadCount': 'Number of Loads'},
            color='RevenueTotal',
            color_continuous_scale='Blues'
        )
        fig.update_xaxes(tickangle=45)
        fig.update_layout(yaxis=dict(tickformat='.0f'))
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Top 15 lanes by total revenue
        st.subheader("Top 15 Lanes by Total Revenue")
        top_revenue = df.groupby('Lane_Detailed').agg({
            'RevenueTotal': 'sum',
            'LoadDetailId': 'count',
            'RatePerMile_Revenue': 'mean'
        }).rename(columns={'LoadDetailId': 'LoadCount'}).sort_values('RevenueTotal', ascending=False).head(15)
        top_revenue = format_numeric_columns(top_revenue.reset_index(), exclude_cols=['LoadCount'])
        top_revenue['LoadCount'] = top_revenue['LoadCount'].astype(int)
        
        st.dataframe(
            top_revenue.style.format({
                'RevenueTotal': '${:,.2f}',
                'RatePerMile_Revenue': '${:.2f}',
                'LoadCount': '{:,.0f}'
            }, na_rep=''),
            use_container_width=True,
            hide_index=True
        )
        
        st.divider()
        
        # Top 15 lanes by avg revenue (minimum 5 loads required)
        st.subheader("Top 15 Lanes by Average Revenue (Minimum 5 Loads)")
        top_avg_revenue = df.groupby('Lane_Detailed').agg({
            'RevenueTotal': 'mean',
            'LoadDetailId': 'count',
            'RatePerMile_Revenue': 'mean'
        }).rename(columns={'LoadDetailId': 'LoadCount', 'RevenueTotal': 'AvgRevenue'})
        # Filter to lanes with at least 5 loads
        top_avg_revenue = top_avg_revenue[top_avg_revenue['LoadCount'] >= 5].sort_values('AvgRevenue', ascending=False).head(15)
        top_avg_revenue = format_numeric_columns(top_avg_revenue.reset_index(), exclude_cols=['LoadCount'])
        top_avg_revenue['LoadCount'] = top_avg_revenue['LoadCount'].astype(int)
        
        st.dataframe(
            top_avg_revenue.style.format({
                'AvgRevenue': '${:,.2f}',
                'RatePerMile_Revenue': '${:.2f}',
                'LoadCount': '{:,.0f}'
            }, na_rep=''),
            use_container_width=True,
            hide_index=True
        )
        
        st.divider()
        
        # Bottom 15 lanes by avg revenue (minimum 5 loads required)
        st.subheader("Bottom 15 Lanes by Average Revenue (Minimum 5 Loads)")
        bottom_avg_revenue = df.groupby('Lane_Detailed').agg({
            'RevenueTotal': 'mean',
            'LoadDetailId': 'count',
            'RatePerMile_Revenue': 'mean'
        }).rename(columns={'LoadDetailId': 'LoadCount', 'RevenueTotal': 'AvgRevenue'})
        # Filter to lanes with at least 5 loads
        bottom_avg_revenue = bottom_avg_revenue[bottom_avg_revenue['LoadCount'] >= 5].sort_values('AvgRevenue', ascending=True).head(15)
        bottom_avg_revenue = format_numeric_columns(bottom_avg_revenue.reset_index(), exclude_cols=['LoadCount'])
        bottom_avg_revenue['LoadCount'] = bottom_avg_revenue['LoadCount'].astype(int)
        
        st.dataframe(
            bottom_avg_revenue.style.format({
                'AvgRevenue': '${:,.2f}',
                'RatePerMile_Revenue': '${:.2f}',
                'LoadCount': '{:,.0f}'
            }, na_rep=''),
            use_container_width=True,
            hide_index=True
        )
        
        st.divider()
        
        # Average days between loads by lane
        st.subheader("Average Days Between Loads by Lane")
        if 'Created' in df.columns and df['Created'].notna().any():
            # Calculate days between loads for each lane
            days_between_data = []
            
            for lane in df['Lane_Detailed'].unique():
                lane_data = df[df['Lane_Detailed'] == lane].copy()
                lane_data = lane_data.sort_values('Created')
                
                if len(lane_data) > 1:
                    # Calculate time differences between consecutive loads
                    lane_data['DaysBetween'] = lane_data['Created'].diff().dt.days
                    avg_days = lane_data['DaysBetween'].mean()
                    
                    if not pd.isna(avg_days):
                        days_between_data.append({
                            'Lane_Detailed': lane,
                            'AvgDaysBetween': round(avg_days, 2),
                            'LoadCount': len(lane_data),
                            'TotalRevenue': lane_data['RevenueTotal'].sum(),
                            'AvgRevenue': lane_data['RevenueTotal'].mean()
                        })
            
            if days_between_data:
                days_between_df = pd.DataFrame(days_between_data)
                days_between_df = format_numeric_columns(days_between_df, exclude_cols=['LoadCount'])
                days_between_df['LoadCount'] = days_between_df['LoadCount'].astype(int)
                days_between_df = days_between_df.sort_values('AvgDaysBetween', ascending=True)
                
                st.dataframe(
                    days_between_df.style.format({
                        'AvgDaysBetween': '{:.2f}',
                        'TotalRevenue': '${:,.2f}',
                        'AvgRevenue': '${:,.2f}',
                        'LoadCount': '{:,.0f}'
                    }, na_rep=''),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Show summary statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Overall Avg Days Between Loads", f"{days_between_df['AvgDaysBetween'].mean():.2f}")
                with col2:
                    st.metric("Median Days Between Loads", f"{days_between_df['AvgDaysBetween'].median():.2f}")
                with col3:
                    st.metric("Lanes with Daily Loads (<1 day)", f"{(days_between_df['AvgDaysBetween'] < 1).sum():,}")
            else:
                st.info("No date data available to calculate days between loads.")
        else:
            st.info("Date information not available for calculating days between loads.")
    
    # Tab 2: Enhanced Lane Pivot Analysis
    with tab2:
        st.header("🛣️ Detailed Lane Pivot Analysis")
        
        # Lane pivot with origin, destination, trailer type
        st.subheader("Lane Analysis by Origin → Destination & Trailer Type")
        
        # Group by detailed lane and trailer type
        pivot_cols = ['Lane_Detailed', 'TrailerType'] if 'TrailerType' in df.columns else ['Lane_Detailed']
        
        lane_pivot = df.groupby(pivot_cols).agg({
            'LoadDetailId': 'count',
            'RevenueTotal': ['sum', 'mean'],
            'BillTotal': 'sum',
            'PayTotal': 'sum',
            'GrossMargin': 'mean',
            'RatePerMile_Revenue': 'mean',
            'Miles': 'mean',
            'CustomerName': 'nunique',
            'CarrierName': 'nunique'
        }).round(2)
        
        # Flatten column names
        lane_pivot.columns = ['_'.join(col).strip('_') for col in lane_pivot.columns.values]
        lane_pivot = lane_pivot.rename(columns={
            'LoadDetailId_count': 'LoadCount',
            'RevenueTotal_sum': 'TotalRevenue',
            'RevenueTotal_mean': 'AvgRevenue',
            'BillTotal_sum': 'TotalBill',
            'PayTotal_sum': 'TotalPay',
            'GrossMargin_mean': 'AvgMargin',
            'RatePerMile_Revenue_mean': 'AvgRatePerMile',
            'Miles_mean': 'AvgMiles',
            'CustomerName_nunique': 'UniqueCustomers',
            'CarrierName_nunique': 'UniqueCarriers'
        })
        
        lane_pivot = lane_pivot.reset_index()
        lane_pivot = lane_pivot.sort_values('TotalRevenue', ascending=False)
        
        # Add PayTotal vs DAT comparison (Low, High, Avg) if available
        if 'SpotAvgLinehaulRate' in df.columns:
            # Calculate PayTotal_Low excluding zeros
            pay_low = df.groupby(pivot_cols)['PayTotal'].apply(calc_low_excluding_zero).round(2)
            
            dat_comparison = df.groupby(pivot_cols).agg({
                'PayTotal': ['max', 'mean'],
                'DAT_LowTotalPay': 'mean',
                'DAT_HighTotalPay': 'mean',
                'DAT_AvgTotalPay': 'mean',
                'RatePerMile_Carrier': ['min', 'max', 'mean'],
                'SpotLowLinehaulRate': 'mean',  # Keep for calculation but will not display
                'SpotHighLinehaulRate': 'mean',  # Keep for calculation but will not display
                'SpotAvgLinehaulRate': 'mean'  # Keep for calculation but will not display
            }).round(2)
            
            # Ensure all pay/bill/revenue columns are rounded to 2 decimal places
            pay_bill_revenue_agg_cols = ['PayTotal_max', 'PayTotal_mean', 'DAT_LowTotalPay', 
                                        'DAT_HighTotalPay', 'DAT_AvgTotalPay']
            for col in pay_bill_revenue_agg_cols:
                if col in dat_comparison.columns:
                    dat_comparison[col] = dat_comparison[col].round(2)
            
            # Flatten column names
            dat_comparison.columns = ['_'.join(col).strip('_') for col in dat_comparison.columns.values]
            dat_comparison = dat_comparison.rename(columns={
                'PayTotal_max': 'PayTotal_High',
                'PayTotal_mean': 'PayTotal_Avg',
                'RatePerMile_Carrier_min': 'RatePerMile_Low',
                'RatePerMile_Carrier_max': 'RatePerMile_High',
                'RatePerMile_Carrier_mean': 'RatePerMile_Avg'
            })
            
            # Add PayTotal_Low from custom calculation
            dat_comparison['PayTotal_Low'] = pay_low
            
            dat_comparison = dat_comparison.reset_index()
            lane_pivot = lane_pivot.merge(dat_comparison, on=pivot_cols, how='left')
            
            # Reorder columns to put PayTotal_Low in the correct position (Low, High, Avg)
            # Place PayTotal columns right after TotalPay if it exists, otherwise after LoadCount
            if 'PayTotal_Low' in lane_pivot.columns:
                cols = lane_pivot.columns.tolist()
                # Remove PayTotal columns from their current positions
                for col in ['PayTotal_Low', 'PayTotal_High', 'PayTotal_Avg']:
                    if col in cols:
                        cols.remove(col)
                
                # Find where to insert - after TotalPay if it exists
                insert_idx = None
                if 'TotalPay' in cols:
                    insert_idx = cols.index('TotalPay') + 1
                elif 'LoadCount' in cols:
                    insert_idx = cols.index('LoadCount') + 1
                else:
                    insert_idx = len(pivot_cols) + 1  # After pivot columns
                
                # Insert PayTotal columns in order: Low, High, Avg
                cols.insert(insert_idx, 'PayTotal_Low')
                if 'PayTotal_High' in lane_pivot.columns:
                    cols.insert(insert_idx + 1, 'PayTotal_High')
                if 'PayTotal_Avg' in lane_pivot.columns:
                    cols.insert(insert_idx + 2, 'PayTotal_Avg')
                
                lane_pivot = lane_pivot[cols]
        
        # Ensure count columns are integers (no decimals)
        for col in ['LoadCount', 'UniqueCustomers', 'UniqueCarriers']:
            if col in lane_pivot.columns:
                lane_pivot[col] = lane_pivot[col].astype(int)
        
        # Format numeric columns to 2 decimal places
        lane_pivot = format_numeric_columns(lane_pivot, exclude_cols=['LoadCount', 'UniqueCustomers', 'UniqueCarriers'])
        
        # Apply styling
        styled_pivot = lane_pivot.style.applymap(
            style_revenue, subset=['TotalRevenue']
        ).applymap(
            style_avg_revenue, subset=['AvgRevenue']
        ).format({
            col: '{:,.2f}' for col in lane_pivot.select_dtypes(include=[np.number]).columns 
            if col not in ['LoadCount', 'UniqueCustomers', 'UniqueCarriers']
        }, na_rep='').format({
            col: '{:,.0f}' for col in ['LoadCount', 'UniqueCustomers', 'UniqueCarriers'] 
            if col in lane_pivot.columns
        }, na_rep='')
        
        st.dataframe(
            styled_pivot,
            use_container_width=True,
            height=600
        )
        
        # DAT Comparison Section
        if 'SpotAvgLinehaulRate' in df.columns and 'DAT_AvgTotalPay' in lane_pivot.columns:
            st.divider()
            st.subheader("📊 PayTotal vs DAT Market Rates Comparison")
            
            # Filter to lanes with DAT data
            lane_pivot_dat = lane_pivot[lane_pivot['DAT_AvgTotalPay'].notna()].copy()
            
            if len(lane_pivot_dat) > 0:
                # Calculate differences before filtering columns
                # Use lane_pivot_dat which has all the columns
                if 'PayTotal_Avg' in lane_pivot_dat.columns and 'DAT_AvgTotalPay' in lane_pivot_dat.columns:
                    lane_pivot_dat['Pay_vs_DAT_Avg'] = (lane_pivot_dat['PayTotal_Avg'] - lane_pivot_dat['DAT_AvgTotalPay']).round(2)
                    lane_pivot_dat['Pay_vs_DAT_Low'] = (lane_pivot_dat['PayTotal_Low'] - lane_pivot_dat['DAT_LowTotalPay']).round(2)
                    lane_pivot_dat['Pay_vs_DAT_High'] = (lane_pivot_dat['PayTotal_High'] - lane_pivot_dat['DAT_HighTotalPay']).round(2)
                
                if 'RatePerMile_Avg' in lane_pivot_dat.columns and 'SpotAvgLinehaulRate' in lane_pivot_dat.columns:
                    lane_pivot_dat['RatePerMile_vs_DAT_Avg'] = (lane_pivot_dat['RatePerMile_Avg'] - lane_pivot_dat['SpotAvgLinehaulRate']).round(2)
                    lane_pivot_dat['RatePerMile_vs_DAT_Low'] = (lane_pivot_dat['RatePerMile_Low'] - lane_pivot_dat['SpotLowLinehaulRate']).round(2)
                    lane_pivot_dat['RatePerMile_vs_DAT_High'] = (lane_pivot_dat['RatePerMile_High'] - lane_pivot_dat['SpotHighLinehaulRate']).round(2)
                
                # Create comparison summary (exclude Spot rate columns and SpotTimeFrame from display)
                comparison_cols = ['Lane_Detailed', 'TrailerType', 'LoadCount', 
                               'PayTotal_Low', 'PayTotal_High', 'PayTotal_Avg',
                               'DAT_LowTotalPay', 'DAT_HighTotalPay', 'DAT_AvgTotalPay',
                               'RatePerMile_Low', 'RatePerMile_High', 'RatePerMile_Avg',
                               'Pay_vs_DAT_Avg', 'Pay_vs_DAT_Low', 'Pay_vs_DAT_High',
                               'RatePerMile_vs_DAT_Avg', 'RatePerMile_vs_DAT_Low', 'RatePerMile_vs_DAT_High']
                
                comparison_df = lane_pivot_dat[[col for col in comparison_cols if col in lane_pivot_dat.columns]].copy()
                
                comparison_df = comparison_df.sort_values('Pay_vs_DAT_Avg' if 'Pay_vs_DAT_Avg' in comparison_df.columns else 'LoadCount', ascending=True)
                
                # Format numeric columns to 2 decimal places
                comparison_df = format_numeric_columns(comparison_df, exclude_cols=['LoadCount'])
                
                st.write(f"**Lanes with DAT Data: {len(comparison_df):,}**")
                
                # Format for display
                styled_comparison = comparison_df.style.format({
                    col: '{:,.2f}' for col in comparison_df.select_dtypes(include=[np.number]).columns 
                    if col != 'LoadCount'
                }, na_rep='')
                
                st.dataframe(styled_comparison, use_container_width=True, height=400)
                
                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if 'Pay_vs_DAT_Avg' in comparison_df.columns:
                        avg_diff = comparison_df['Pay_vs_DAT_Avg'].mean()
                        st.metric("Avg Pay vs DAT", f"${avg_diff:,.2f}", 
                                 delta=f"{'Above' if avg_diff > 0 else 'Below'} DAT Market")
                with col2:
                    if 'Pay_vs_DAT_Avg' in comparison_df.columns:
                        above_dat = (comparison_df['Pay_vs_DAT_Avg'] > 0).sum()
                        st.metric("Lanes Above DAT", f"{above_dat:,}", 
                                 delta=f"{above_dat/len(comparison_df)*100:.2f}%")
                with col3:
                    if 'Pay_vs_DAT_Avg' in comparison_df.columns:
                        below_dat = (comparison_df['Pay_vs_DAT_Avg'] < 0).sum()
                        st.metric("Lanes Below DAT", f"{below_dat:,}",
                                 delta=f"{below_dat/len(comparison_df)*100:.2f}%")
                with col4:
                    # Removed SpotTimeFrame display
                    pass
        
        # Summary statistics
        st.divider()
        st.subheader("Summary Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Lanes", f"{len(lane_pivot):,}")
        with col2:
            st.metric("Lanes with Negative Revenue", f"{(lane_pivot['TotalRevenue'] < 0).sum():,}")
            st.metric("High Revenue Lanes (≥$300)", f"{(lane_pivot['AvgRevenue'] >= 300).sum():,}")
        with col3:
            st.metric("Low Revenue Lanes ($0-$299.99)", f"{((lane_pivot['AvgRevenue'] >= 0) & (lane_pivot['AvgRevenue'] < 300)).sum():,}")
    
    # Tab 3: Rate Analysis
    with tab3:
        st.header("💰 Rate Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Rate Distribution")
            # Round rate data for display
            df_chart = df.copy()
            df_chart['RatePerMile_Revenue'] = df_chart['RatePerMile_Revenue'].round(2)
            
            fig = px.histogram(
                df_chart,
                x='RatePerMile_Revenue',
                nbins=50,
                title="Rate per Mile Distribution",
                labels={'RatePerMile_Revenue': 'Rate per Mile ($)', 'count': 'Number of Loads'}
            )
            fig.update_layout(xaxis=dict(tickformat='.2f'), yaxis=dict(tickformat='.0f'))
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Rate by Distance")
            df['DistanceRange'] = pd.cut(
                df['Miles'],
                bins=[0, 100, 250, 500, 1000, 2000, float('inf')],
                labels=['0-100', '101-250', '251-500', '501-1000', '1001-2000', '2000+']
            )
            rate_by_distance = df.groupby('DistanceRange', observed=True).agg({
                'RatePerMile_Revenue': 'mean',
                'LoadDetailId': 'count'
            }).rename(columns={'LoadDetailId': 'LoadCount'}).round(2)
            
            fig = px.bar(
                rate_by_distance.reset_index(),
                x='DistanceRange',
                y='RatePerMile_Revenue',
                title="Average Rate per Mile by Distance Range",
                labels={'DistanceRange': 'Distance (miles)', 'RatePerMile_Revenue': 'Rate per Mile ($)'},
                text='LoadCount'
            )
            fig.update_traces(texttemplate='%{text} loads', textposition='outside')
            fig.update_layout(yaxis=dict(tickformat='.2f'))
            st.plotly_chart(fig, use_container_width=True)
    
    # Tab 4: Year-over-Year Trends
    with tab4:
        st.header("📈 Year-over-Year Trends")
        
        if 'Year' in df.columns and 'Month' in df.columns:
            # Year comparison
            year_comparison = df.groupby(['Year', 'Month']).agg({
                'LoadDetailId': 'count',
                'RevenueTotal': 'sum',
                'RatePerMile_Revenue': 'mean',
                'GrossMargin': 'mean'
            }).rename(columns={'LoadDetailId': 'LoadCount'}).round(2).reset_index()
            
            # Get available years
            years = sorted(year_comparison['Year'].unique())
            
            if len(years) > 1:
                selected_years = st.multiselect("Select Years to Compare", years, default=years[-2:] if len(years) >= 2 else years)
                
                if selected_years:
                    year_filtered = year_comparison[year_comparison['Year'].isin(selected_years)]
                    
                    # Monthly comparison chart
                    st.subheader("Monthly Comparison by Year")
                    fig = px.line(
                        year_filtered,
                        x='Month',
                        y='RevenueTotal',
                        color='Year',
                        markers=True,
                        title="Monthly Revenue Comparison",
                        labels={'RevenueTotal': 'Total Revenue ($)', 'Month': 'Month'}
                    )
                    fig.update_layout(yaxis=dict(tickformat='.2f'))
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Load count comparison
                    fig2 = px.line(
                        year_filtered,
                        x='Month',
                        y='LoadCount',
                        color='Year',
                        markers=True,
                        title="Monthly Load Count Comparison",
                        labels={'LoadCount': 'Number of Loads', 'Month': 'Month'}
                    )
                    fig2.update_layout(yaxis=dict(tickformat='.0f'))
                    st.plotly_chart(fig2, use_container_width=True)
                    
                    # Rate comparison
                    fig3 = px.line(
                        year_filtered,
                        x='Month',
                        y='RatePerMile_Revenue',
                        color='Year',
                        markers=True,
                        title="Monthly Rate per Mile Comparison",
                        labels={'RatePerMile_Revenue': 'Rate per Mile ($)', 'Month': 'Month'}
                    )
                    fig3.update_layout(yaxis=dict(tickformat='.2f'))
                    st.plotly_chart(fig3, use_container_width=True)
                    
                    # Summary table
                    st.subheader("Year Summary")
                    year_summary = df[df['Year'].isin(selected_years)].groupby('Year').agg({
                        'LoadDetailId': 'count',
                        'RevenueTotal': 'sum',
                        'RatePerMile_Revenue': 'mean',
                        'GrossMargin': 'mean'
                    }).rename(columns={'LoadDetailId': 'LoadCount'}).round(2)
                    
                    # Format for display
                    styled_summary = year_summary.style.format({
                        col: '{:,.2f}' for col in year_summary.select_dtypes(include=[np.number]).columns 
                        if col != 'LoadCount'
                    }, na_rep='').format({
                        'LoadCount': '{:,.0f}'
                    }, na_rep='')
                    st.dataframe(styled_summary, use_container_width=True)
            
            # Weekly trends
            if 'WeekStartDate' in df.columns and df['WeekStartDate'].notna().any():
                st.subheader("Weekly Trends (Last 20 Weeks)")
                weekly_trends = df.groupby('WeekStartDate').agg({
                    'LoadDetailId': 'count',
                    'RevenueTotal': 'sum',
                    'RatePerMile_Revenue': 'mean'
                }).rename(columns={'LoadDetailId': 'LoadCount'}).round(2).tail(20).reset_index()
                
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(
                    go.Scatter(x=weekly_trends['WeekStartDate'], y=weekly_trends['LoadCount'], 
                              name="Load Count", mode='lines+markers'),
                    secondary_y=False,
                )
                fig.add_trace(
                    go.Scatter(x=weekly_trends['WeekStartDate'], y=weekly_trends['RevenueTotal'], 
                              name="Revenue", mode='lines+markers'),
                    secondary_y=True,
                )
                fig.update_xaxes(title_text="Week")
                fig.update_yaxes(title_text="Load Count", secondary_y=False, tickformat='.0f')
                fig.update_yaxes(title_text="Revenue ($)", secondary_y=True, tickformat='.2f')
                fig.update_layout(title="Weekly Load Volume and Revenue Trends")
                st.plotly_chart(fig, use_container_width=True)
    
    # Tab 5: Customer/Carrier Analysis with Lanes
    with tab5:
        st.header("👥 Customer & Carrier Analysis with Lane Details")
        
        # Customer analysis with lanes
        st.subheader("Customer Analysis - Revenue by Lane")
        customer_lane_analysis = df.groupby(['CustomerName', 'Lane_Detailed']).agg({
            'LoadDetailId': 'count',
            'RevenueTotal': 'sum',
            'PayTotal': 'sum',
            'GrossMargin': 'mean',
            'RatePerMile_Customer': 'mean'
        }).rename(columns={
            'LoadDetailId': 'LoadCount',
            'RatePerMile_Customer': 'AvgCustomerRate'
        }).reset_index()
        
        customer_lane_analysis = customer_lane_analysis.sort_values('RevenueTotal', ascending=True)
        
        # Format numeric columns to 2 decimal places
        customer_lane_analysis = format_numeric_columns(customer_lane_analysis, exclude_cols=['LoadCount'])
        
        st.write("**Lowest Revenue Areas**")
        loss_areas = customer_lane_analysis.head(20)
        styled_loss = loss_areas.style.applymap(
            style_revenue, subset=['RevenueTotal']
        ).format({
            col: '{:,.2f}' for col in loss_areas.select_dtypes(include=[np.number]).columns if col != 'LoadCount'
        }, na_rep='')
        st.dataframe(styled_loss, use_container_width=True)
        
        st.write("**Highest Revenue Areas**")
        profit_areas = customer_lane_analysis.sort_values('RevenueTotal', ascending=False).head(20)
        styled_profit = profit_areas.style.applymap(
            style_revenue, subset=['RevenueTotal']
        ).format({
            col: '{:,.2f}' for col in profit_areas.select_dtypes(include=[np.number]).columns if col != 'LoadCount'
        }, na_rep='')
        st.dataframe(styled_profit, use_container_width=True)
        
        st.divider()
        
        # Carrier analysis with lanes
        st.subheader("Carrier Analysis - Revenue by Lane")
        carrier_lane_analysis = df.groupby(['CarrierName', 'Lane_Detailed']).agg({
            'LoadDetailId': 'count',
            'PayTotal': 'sum',
            'RevenueTotal': 'sum',
            'GrossMargin': 'mean',
            'RatePerMile_Carrier': 'mean'
        }).rename(columns={
            'LoadDetailId': 'LoadCount',
            'RatePerMile_Carrier': 'AvgCarrierRate'
        }).reset_index()
        
        carrier_lane_analysis = carrier_lane_analysis.sort_values('RevenueTotal', ascending=True)
        
        # Format numeric columns to 2 decimal places
        carrier_lane_analysis = format_numeric_columns(carrier_lane_analysis, exclude_cols=['LoadCount'])
        
        st.write("**Lowest Revenue Areas**")
        carrier_loss = carrier_lane_analysis.head(20)
        styled_carrier_loss = carrier_loss.style.applymap(
            style_revenue, subset=['RevenueTotal']
        ).format({
            col: '{:,.2f}' for col in carrier_loss.select_dtypes(include=[np.number]).columns if col != 'LoadCount'
        }, na_rep='')
        st.dataframe(styled_carrier_loss, use_container_width=True)
        
        st.write("**Highest Revenue Areas**")
        carrier_profit = carrier_lane_analysis.sort_values('RevenueTotal', ascending=False).head(20)
        styled_carrier_profit = carrier_profit.style.applymap(
            style_revenue, subset=['RevenueTotal']
        ).format({
            col: '{:,.2f}' for col in carrier_profit.select_dtypes(include=[np.number]).columns if col != 'LoadCount'
        }, na_rep='')
        st.dataframe(styled_carrier_profit, use_container_width=True)
        
        # PayTotal vs DAT comparison if available
        if 'SpotAvgLinehaulRate' in df.columns:
            st.divider()
            st.subheader("PayTotal vs DAT Market Rate Comparison by Carrier & Lane")
            
            # Filter to loads with DAT data
            df_with_dat = df[df['SpotAvgLinehaulRate'].notna()].copy()
            
            if len(df_with_dat) > 0:
                # Ensure DAT total pay columns exist - calculate if missing and round to 2 decimal places
                if 'DAT_AvgTotalPay' not in df_with_dat.columns:
                    df_with_dat['DAT_AvgTotalPay'] = (df_with_dat['SpotAvgLinehaulRate'] * df_with_dat['Miles']).round(2)
                if 'DAT_LowTotalPay' not in df_with_dat.columns:
                    df_with_dat['DAT_LowTotalPay'] = (df_with_dat['SpotLowLinehaulRate'] * df_with_dat['Miles']).round(2)
                if 'DAT_HighTotalPay' not in df_with_dat.columns:
                    df_with_dat['DAT_HighTotalPay'] = (df_with_dat['SpotHighLinehaulRate'] * df_with_dat['Miles']).round(2)
                
                # Calculate PayTotal_Low excluding zeros
                pay_low = df_with_dat.groupby(['CarrierName', 'Lane_Detailed', 'TrailerType'])['PayTotal'].apply(calc_low_excluding_zero).round(2)
                
                pay_dat_comparison = df_with_dat.groupby(['CarrierName', 'Lane_Detailed', 'TrailerType']).agg({
                    'PayTotal': ['max', 'mean'],
                    'DAT_LowTotalPay': 'mean',
                    'DAT_HighTotalPay': 'mean',
                    'DAT_AvgTotalPay': 'mean',
                    'RatePerMile_Carrier': ['min', 'max', 'mean'],
                    'SpotAvgLinehaulRate': 'mean',  # Keep for calculation but will drop from display
                    'LoadDetailId': 'count'
                }).round(2)
                
                # Ensure all pay/bill/revenue columns are rounded to 2 decimal places
                pay_bill_revenue_agg_cols = ['PayTotal_max', 'PayTotal_mean', 'DAT_LowTotalPay', 
                                            'DAT_HighTotalPay', 'DAT_AvgTotalPay']
                for col in pay_bill_revenue_agg_cols:
                    if col in pay_dat_comparison.columns:
                        pay_dat_comparison[col] = pay_dat_comparison[col].round(2)
                
                # Flatten column names
                pay_dat_comparison.columns = ['_'.join(col).strip('_') for col in pay_dat_comparison.columns.values]
                pay_dat_comparison = pay_dat_comparison.rename(columns={
                    'PayTotal_max': 'PayTotal_High',
                    'PayTotal_mean': 'PayTotal_Avg',
                    'RatePerMile_Carrier_min': 'RatePerMile_Low',
                    'RatePerMile_Carrier_max': 'RatePerMile_High',
                    'RatePerMile_Carrier_mean': 'RatePerMile_Avg',
                    'LoadDetailId_count': 'LoadCount'
                })
                
                # Add PayTotal_Low from custom calculation
                pay_dat_comparison['PayTotal_Low'] = pay_low
                
                pay_dat_comparison = pay_dat_comparison.reset_index()
                
                # Reorder columns to put PayTotal_Low in the correct position (Low, High, Avg)
                # Place PayTotal columns right after LoadCount
                if 'PayTotal_Low' in pay_dat_comparison.columns:
                    cols = pay_dat_comparison.columns.tolist()
                    # Remove PayTotal columns from their current positions
                    for col in ['PayTotal_Low', 'PayTotal_High', 'PayTotal_Avg']:
                        if col in cols:
                            cols.remove(col)
                    
                    # Find where to insert - after LoadCount
                    insert_idx = None
                    if 'LoadCount' in cols:
                        insert_idx = cols.index('LoadCount') + 1
                    else:
                        insert_idx = 3  # After CarrierName, Lane_Detailed, TrailerType
                    
                    # Insert PayTotal columns in order: Low, High, Avg
                    cols.insert(insert_idx, 'PayTotal_Low')
                    if 'PayTotal_High' in pay_dat_comparison.columns:
                        cols.insert(insert_idx + 1, 'PayTotal_High')
                    if 'PayTotal_Avg' in pay_dat_comparison.columns:
                        cols.insert(insert_idx + 2, 'PayTotal_Avg')
                    
                    pay_dat_comparison = pay_dat_comparison[cols]
                
                # Calculate differences - check if columns exist first and round to 2 decimal places
                if 'DAT_AvgTotalPay_mean' in pay_dat_comparison.columns:
                    pay_dat_comparison['Pay_vs_DAT_Avg'] = (pay_dat_comparison['PayTotal_Avg'] - pay_dat_comparison['DAT_AvgTotalPay_mean']).round(2)
                if 'DAT_LowTotalPay_mean' in pay_dat_comparison.columns:
                    pay_dat_comparison['Pay_vs_DAT_Low'] = (pay_dat_comparison['PayTotal_Low'] - pay_dat_comparison['DAT_LowTotalPay_mean']).round(2)
                if 'DAT_HighTotalPay_mean' in pay_dat_comparison.columns:
                    pay_dat_comparison['Pay_vs_DAT_High'] = (pay_dat_comparison['PayTotal_High'] - pay_dat_comparison['DAT_HighTotalPay_mean']).round(2)
                if 'SpotAvgLinehaulRate_mean' in pay_dat_comparison.columns:
                    pay_dat_comparison['RatePerMile_vs_DAT_Avg'] = (pay_dat_comparison['RatePerMile_Avg'] - pay_dat_comparison['SpotAvgLinehaulRate_mean']).round(2)
                
                # Rename the aggregated DAT columns for consistency
                if 'DAT_AvgTotalPay_mean' in pay_dat_comparison.columns:
                    pay_dat_comparison = pay_dat_comparison.rename(columns={'DAT_AvgTotalPay_mean': 'DAT_AvgTotalPay'})
                if 'DAT_LowTotalPay_mean' in pay_dat_comparison.columns:
                    pay_dat_comparison = pay_dat_comparison.rename(columns={'DAT_LowTotalPay_mean': 'DAT_LowTotalPay'})
                if 'DAT_HighTotalPay_mean' in pay_dat_comparison.columns:
                    pay_dat_comparison = pay_dat_comparison.rename(columns={'DAT_HighTotalPay_mean': 'DAT_HighTotalPay'})
                if 'SpotAvgLinehaulRate_mean' in pay_dat_comparison.columns:
                    pay_dat_comparison = pay_dat_comparison.rename(columns={'SpotAvgLinehaulRate_mean': 'SpotAvgLinehaulRate'})
                
                # Remove Spot rate columns and SpotTimeFrame from display
                cols_to_drop = ['SpotLowLinehaulRate', 'SpotHighLinehaulRate', 'SpotAvgLinehaulRate', 'SpotTimeFrame']
                for col in cols_to_drop:
                    if col in pay_dat_comparison.columns:
                        pay_dat_comparison = pay_dat_comparison.drop(columns=[col])
                
                # Sort by Pay_vs_DAT_Avg if it exists, otherwise by LoadCount
                if 'Pay_vs_DAT_Avg' in pay_dat_comparison.columns:
                    pay_dat_comparison = pay_dat_comparison.sort_values('Pay_vs_DAT_Avg', ascending=True)
                else:
                    pay_dat_comparison = pay_dat_comparison.sort_values('LoadCount', ascending=False)
                
                st.write(f"**Carrier/Lane combinations with DAT Data: {len(pay_dat_comparison):,}**")
                st.dataframe(pay_dat_comparison.head(50), use_container_width=True, height=400)
    
    # Tab 6: Data Explorer
    with tab6:
        st.header("📋 Data Explorer")
        
        st.subheader("Filtered Data")
        st.write(f"Showing {len(df):,} loads")
        
        # Limit display rows
        max_display_rows = st.slider("Maximum rows to display", 100, 10000, 1000, 100)
        
        # Column selector
        all_columns = df.columns.tolist()
        default_cols = ['LoadDetailId', 'DfNumber', 'Lane_Detailed', 'CustomerName', 
                       'CarrierName', 'TrailerType', 'RevenueTotal', 'GrossMargin', 
                       'RatePerMile_Revenue', 'Miles', 'Created']
        selected_cols = st.multiselect("Select Columns", all_columns, default=default_cols)
        
        if selected_cols:
            display_df = df[selected_cols].copy()
            
            # Search
            search_term = st.text_input("Search (filters by DF Number, Customer, or Carrier)")
            if search_term:
                mask = (
                    display_df['DfNumber'].astype(str).str.contains(search_term, case=False, na=False) |
                    display_df['CustomerName'].astype(str).str.contains(search_term, case=False, na=False) |
                    display_df['CarrierName'].astype(str).str.contains(search_term, case=False, na=False)
                )
                display_df = display_df[mask]
            
            # Limit rows for display
            display_count = len(display_df)
            if display_count > max_display_rows:
                st.warning(f"Showing first {max_display_rows:,} of {display_count:,} rows. Use filters to narrow down results.")
                display_df_display = display_df.head(max_display_rows)
            else:
                display_df_display = display_df
            
            # Apply styling only if dataframe is not too large
            if len(display_df_display) * len(display_df_display.columns) < 500000:
                # Apply styling
                if 'RevenueTotal' in display_df_display.columns:
                    styled_display = display_df_display.style.applymap(
                        style_revenue, subset=['RevenueTotal']
                    )
                else:
                    styled_display = display_df_display
                st.dataframe(styled_display, use_container_width=True, height=400)
            else:
                # Too large for styling, display without styling
                st.dataframe(display_df_display, use_container_width=True, height=400)
            
            # Download button (downloads full filtered dataset, not just displayed rows)
            csv = display_df.to_csv(index=False)
            st.download_button(
                label=f"📥 Download All Filtered Data as CSV ({display_count:,} rows)",
                data=csv,
                file_name=f"lane_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )


if __name__ == "__main__":
    main()
