"""
Lane and Rate Analysis for TMS Load Data
Comprehensive analysis for transportation lane and rate optimization.
"""

import pandas as pd
import numpy as np
from database_connection import DatabaseConnection
from datetime import datetime
import os
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def load_data_from_db(limit=None):
    """Load ReportMasterDataSetCache table from database into pandas DataFrame."""
    query = "SELECT * FROM [dbo].[ReportMasterDataSetCache]"
    if limit:
        query += f" ORDER BY LoadDetailId OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
    
    print(f"Loading data from ReportMasterDataSetCache...")
    if limit:
        print(f"Limiting to {limit} rows for testing.")
    
    db = DatabaseConnection()
    if not db.connect():
        raise Exception("Failed to connect to database. Please check your connection string and Azure firewall settings.")
    
    try:
        db.cursor.execute(f"SELECT TOP 1 * FROM [dbo].[ReportMasterDataSetCache]")
        columns = [column[0] for column in db.cursor.description]
        db.cursor.execute(query)
        rows = db.cursor.fetchall()
        df = pd.DataFrame.from_records(rows, columns=columns)
        print(f"Loaded {len(df)} rows and {len(df.columns)} columns.")
        return df
    finally:
        db.disconnect()


def create_lane_identifier(df):
    """
    Create lane identifiers from origin and destination.
    Creates multiple lane formats for different analysis needs.
    """
    df = df.copy()
    
    # State-to-State Lane
    df['Lane_StateToState'] = df['OriginState'].astype(str) + ' → ' + df['FinalState'].astype(str)
    
    # City-to-City Lane (more specific)
    df['Lane_CityToCity'] = df['OriginCityState'].astype(str) + ' → ' + df['FinalCityState'].astype(str)
    
    # Use existing Lane column if available, otherwise use State-to-State
    if 'Lane' in df.columns and df['Lane'].notna().any():
        df['Lane_Primary'] = df['Lane']
    else:
        df['Lane_Primary'] = df['Lane_StateToState']
    
    return df


def calculate_rate_metrics(df):
    """Calculate rate per mile, rate per weight, and profitability metrics."""
    df = df.copy()
    
    # Convert Decimal types to float for calculations
    numeric_cols = ['RevenueTotal', 'BillTotal', 'PayTotal', 'Miles', 'Weight', 
                    'ExpenseTotal', 'CustomerDue', 'CarrierBalanceDue']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Rate per Mile calculations
    df['RatePerMile_Revenue'] = df['RevenueTotal'] / df['Miles'].replace(0, np.nan)
    df['RatePerMile_Customer'] = df['BillTotal'] / df['Miles'].replace(0, np.nan)
    df['RatePerMile_Carrier'] = df['PayTotal'] / df['Miles'].replace(0, np.nan)
    
    # Rate per Weight (CWT - per 100 lbs)
    df['Weight_CWT'] = df['Weight'] / 100  # Convert to hundredweight
    df['RatePerCWT_Revenue'] = df['RevenueTotal'] / df['Weight_CWT'].replace(0, np.nan)
    df['RatePerCWT_Customer'] = df['BillTotal'] / df['Weight_CWT'].replace(0, np.nan)
    df['RatePerCWT_Carrier'] = df['PayTotal'] / df['Weight_CWT'].replace(0, np.nan)
    
    # Profitability metrics
    df['GrossProfit'] = df['RevenueTotal'] - df['PayTotal']
    df['GrossMargin'] = (df['GrossProfit'] / df['RevenueTotal'].replace(0, np.nan)) * 100
    df['ProfitPerMile'] = df['GrossProfit'] / df['Miles'].replace(0, np.nan)
    
    # Margin analysis
    df['CustomerCarrierSpread'] = df['BillTotal'] - df['PayTotal']
    df['SpreadPercentage'] = (df['CustomerCarrierSpread'] / df['BillTotal'].replace(0, np.nan)) * 100
    
    return df


def analyze_lanes(df):
    """Comprehensive lane analysis."""
    print("\n" + "="*80)
    print("LANE ANALYSIS")
    print("="*80)
    
    # Lane Volume Analysis
    print("\n📊 TOP 20 LANES BY VOLUME (State-to-State)")
    lane_volume = df.groupby('Lane_StateToState').agg({
        'LoadDetailId': 'count',
        'RevenueTotal': 'sum',
        'Miles': 'mean',
        'Weight': 'mean'
    }).rename(columns={'LoadDetailId': 'LoadCount'}).sort_values('LoadCount', ascending=False)
    
    for idx, (lane, row) in enumerate(lane_volume.head(20).iterrows(), 1):
        print(f"  {idx:2d}. {lane}: {row['LoadCount']:,} loads, ${row['RevenueTotal']:,.2f} revenue")
    
    # Lane Revenue Analysis
    print("\n💰 TOP 20 LANES BY REVENUE (State-to-State)")
    lane_revenue = df.groupby('Lane_StateToState').agg({
        'LoadDetailId': 'count',
        'RevenueTotal': 'sum',
        'RevenueTotal': ['sum', 'mean']
    }).sort_values(('RevenueTotal', 'sum'), ascending=False)
    
    for idx, (lane, row) in enumerate(lane_revenue.head(20).iterrows(), 1):
        total_rev = row[('RevenueTotal', 'sum')]
        avg_rev = row[('RevenueTotal', 'mean')]
        count = row[('LoadDetailId', 'count')]
        print(f"  {idx:2d}. {lane}: ${total_rev:,.2f} total (${avg_rev:,.2f} avg, {count:,} loads)")
    
    # Lane Rate Analysis
    print("\n📈 TOP 20 LANES BY RATE PER MILE (Revenue)")
    lane_rates = df.groupby('Lane_StateToState').agg({
        'LoadDetailId': 'count',
        'RatePerMile_Revenue': 'mean',
        'Miles': 'mean',
        'RevenueTotal': 'sum'
    }).rename(columns={'LoadDetailId': 'LoadCount'}).sort_values('RatePerMile_Revenue', ascending=False)
    
    for idx, (lane, row) in enumerate(lane_rates.head(20).iterrows(), 1):
        if row['LoadCount'] >= 3:  # Only show lanes with at least 3 loads
            print(f"  {idx:2d}. {lane}: ${row['RatePerMile_Revenue']:.2f}/mile "
                  f"({row['LoadCount']:,} loads, {row['Miles']:.0f} avg miles)")
    
    return lane_volume, lane_revenue, lane_rates


def analyze_rates(df):
    """Comprehensive rate analysis."""
    print("\n" + "="*80)
    print("RATE ANALYSIS")
    print("="*80)
    
    # Overall Rate Statistics
    print("\n📊 OVERALL RATE STATISTICS")
    print(f"Average Revenue Rate per Mile: ${df['RatePerMile_Revenue'].mean():.2f}")
    print(f"Median Revenue Rate per Mile: ${df['RatePerMile_Revenue'].median():.2f}")
    print(f"Average Customer Rate per Mile: ${df['RatePerMile_Customer'].mean():.2f}")
    print(f"Average Carrier Rate per Mile: ${df['RatePerMile_Carrier'].mean():.2f}")
    print(f"Average Spread per Mile: ${df['CustomerCarrierSpread'].mean() / df['Miles'].mean():.2f}")
    
    # Rate Distribution
    print("\n📈 RATE PER MILE DISTRIBUTION (Revenue)")
    rate_percentiles = df['RatePerMile_Revenue'].quantile([0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
    for pct, value in rate_percentiles.items():
        print(f"  {int(pct*100)}th percentile: ${value:.2f}/mile")
    
    # Rate by Distance
    print("\n📏 RATE PER MILE BY DISTANCE RANGE")
    df['DistanceRange'] = pd.cut(df['Miles'], 
                                 bins=[0, 100, 250, 500, 1000, 2000, float('inf')],
                                 labels=['0-100', '101-250', '251-500', '501-1000', '1001-2000', '2000+'])
    rate_by_distance = df.groupby('DistanceRange', observed=True).agg({
        'RatePerMile_Revenue': 'mean',
        'LoadDetailId': 'count',
        'Miles': 'mean'
    }).rename(columns={'LoadDetailId': 'LoadCount'})
    
    for distance, row in rate_by_distance.iterrows():
        print(f"  {distance} miles: ${row['RatePerMile_Revenue']:.2f}/mile "
              f"({row['LoadCount']:,} loads, {row['Miles']:.0f} avg miles)")
    
    # Rate by Weight
    print("\n⚖️  RATE PER CWT BY WEIGHT RANGE")
    df['WeightRange'] = pd.cut(df['Weight'], 
                               bins=[0, 10000, 20000, 30000, 40000, float('inf')],
                               labels=['0-10k', '10k-20k', '20k-30k', '30k-40k', '40k+'])
    rate_by_weight = df.groupby('WeightRange', observed=True).agg({
        'RatePerCWT_Revenue': 'mean',
        'LoadDetailId': 'count',
        'Weight': 'mean'
    }).rename(columns={'LoadDetailId': 'LoadCount'})
    
    for weight, row in rate_by_weight.iterrows():
        print(f"  {weight} lbs: ${row['RatePerCWT_Revenue']:.2f}/CWT "
              f"({row['LoadCount']:,} loads, {row['Weight']:,.0f} avg lbs)")
    
    return rate_by_distance, rate_by_weight


def analyze_profitability(df):
    """Analyze profitability by lane and other dimensions."""
    print("\n" + "="*80)
    print("PROFITABILITY ANALYSIS")
    print("="*80)
    
    # Overall Profitability
    print("\n💰 OVERALL PROFITABILITY METRICS")
    total_revenue = df['RevenueTotal'].sum()
    total_carrier_pay = df['PayTotal'].sum()
    total_profit = df['GrossProfit'].sum()
    overall_margin = (total_profit / total_revenue) * 100 if total_revenue > 0 else 0
    
    print(f"Total Revenue: ${total_revenue:,.2f}")
    print(f"Total Carrier Pay: ${total_carrier_pay:,.2f}")
    print(f"Total Gross Profit: ${total_profit:,.2f}")
    print(f"Overall Gross Margin: {overall_margin:.2f}%")
    print(f"Average Profit per Load: ${df['GrossProfit'].mean():,.2f}")
    print(f"Average Profit per Mile: ${df['ProfitPerMile'].mean():.2f}")
    
    # Most Profitable Lanes
    print("\n🏆 TOP 20 MOST PROFITABLE LANES (by Total Profit)")
    lane_profit = df.groupby('Lane_StateToState').agg({
        'GrossProfit': 'sum',
        'GrossMargin': 'mean',
        'LoadDetailId': 'count',
        'RevenueTotal': 'sum'
    }).rename(columns={'LoadDetailId': 'LoadCount'}).sort_values('GrossProfit', ascending=False)
    
    for idx, (lane, row) in enumerate(lane_profit.head(20).iterrows(), 1):
        if row['LoadCount'] >= 3:
            print(f"  {idx:2d}. {lane}: ${row['GrossProfit']:,.2f} profit "
                  f"({row['GrossMargin']:.1f}% margin, {row['LoadCount']:,} loads)")
    
    # Highest Margin Lanes
    print("\n📈 TOP 20 LANES BY MARGIN % (minimum 5 loads)")
    lane_margin = df.groupby('Lane_StateToState').agg({
        'GrossMargin': 'mean',
        'GrossProfit': 'sum',
        'LoadDetailId': 'count'
    }).rename(columns={'LoadDetailId': 'LoadCount'})
    lane_margin = lane_margin[lane_margin['LoadCount'] >= 5].sort_values('GrossMargin', ascending=False)
    
    for idx, (lane, row) in enumerate(lane_margin.head(20).iterrows(), 1):
        print(f"  {idx:2d}. {lane}: {row['GrossMargin']:.1f}% margin "
              f"(${row['GrossProfit']:,.2f} profit, {row['LoadCount']:,} loads)")
    
    # Underperforming Lanes
    print("\n⚠️  UNDERPERFORMING LANES (Negative Margin, minimum 3 loads)")
    underperforming = lane_profit[lane_profit['GrossMargin'] < 0]
    underperforming = underperforming[underperforming['LoadCount'] >= 3].sort_values('GrossMargin')
    
    if len(underperforming) > 0:
        for idx, (lane, row) in enumerate(underperforming.head(10).iterrows(), 1):
            print(f"  {idx:2d}. {lane}: {row['GrossMargin']:.1f}% margin "
                  f"(${row['GrossProfit']:,.2f} loss, {row['LoadCount']:,} loads)")
    else:
        print("  No underperforming lanes found!")
    
    return lane_profit, lane_margin


def analyze_trends(df):
    """Analyze rate and volume trends over time."""
    print("\n" + "="*80)
    print("TIME-BASED TREND ANALYSIS")
    print("="*80)
    
    # Convert dates
    if 'WeekStartDate' in df.columns:
        df['WeekStartDate'] = pd.to_datetime(df['WeekStartDate'])
        df['YearWeek'] = df['WeekStartDate'].dt.to_period('W')
    
    if 'Created' in df.columns:
        df['Created'] = pd.to_datetime(df['Created'])
        df['YearMonth'] = df['Created'].dt.to_period('M')
    
    # Weekly Trends
    if 'WeekStartDate' in df.columns:
        print("\n📅 WEEKLY TRENDS (Last 20 weeks)")
        weekly_trends = df.groupby('YearWeek').agg({
            'LoadDetailId': 'count',
            'RevenueTotal': 'sum',
            'RatePerMile_Revenue': 'mean',
            'GrossProfit': 'sum'
        }).rename(columns={'LoadDetailId': 'LoadCount'}).tail(20)
        
        for week, row in weekly_trends.iterrows():
            print(f"  {week}: {row['LoadCount']:,} loads, "
                  f"${row['RevenueTotal']:,.2f} revenue, "
                  f"${row['RatePerMile_Revenue']:.2f}/mile, "
                  f"${row['GrossProfit']:,.2f} profit")
    
    # Monthly Trends
    if 'Created' in df.columns:
        print("\n📅 MONTHLY TRENDS")
        monthly_trends = df.groupby('YearMonth').agg({
            'LoadDetailId': 'count',
            'RevenueTotal': 'sum',
            'RatePerMile_Revenue': 'mean',
            'GrossProfit': 'sum',
            'GrossMargin': 'mean'
        }).rename(columns={'LoadDetailId': 'LoadCount'})
        
        for month, row in monthly_trends.iterrows():
            print(f"  {month}: {row['LoadCount']:,} loads, "
                  f"${row['RevenueTotal']:,.2f} revenue, "
                  f"${row['RatePerMile_Revenue']:.2f}/mile, "
                  f"{row['GrossMargin']:.1f}% margin")
    
    return weekly_trends if 'WeekStartDate' in df.columns else None, \
           monthly_trends if 'Created' in df.columns else None


def analyze_customer_carrier_rates(df):
    """Analyze rate differences between customers and carriers."""
    print("\n" + "="*80)
    print("CUSTOMER vs CARRIER RATE ANALYSIS")
    print("="*80)
    
    # Customer Rate Analysis
    print("\n👥 TOP 10 CUSTOMERS BY RATE PER MILE")
    customer_rates = df.groupby('CustomerName').agg({
        'RatePerMile_Customer': 'mean',
        'LoadDetailId': 'count',
        'BillTotal': 'sum',
        'Miles': 'mean'
    }).rename(columns={'LoadDetailId': 'LoadCount'}).sort_values('RatePerMile_Customer', ascending=False)
    
    for idx, (customer, row) in enumerate(customer_rates.head(10).iterrows(), 1):
        if row['LoadCount'] >= 5:
            print(f"  {idx:2d}. {customer}: ${row['RatePerMile_Customer']:.2f}/mile "
                  f"({row['LoadCount']:,} loads, ${row['BillTotal']:,.2f} total)")
    
    # Carrier Rate Analysis
    print("\n🚛 TOP 10 CARRIERS BY RATE PER MILE")
    carrier_rates = df.groupby('CarrierName').agg({
        'RatePerMile_Carrier': 'mean',
        'LoadDetailId': 'count',
        'PayTotal': 'sum',
        'Miles': 'mean'
    }).rename(columns={'LoadDetailId': 'LoadCount'}).sort_values('RatePerMile_Carrier', ascending=False)
    
    for idx, (carrier, row) in enumerate(carrier_rates.head(10).iterrows(), 1):
        if row['LoadCount'] >= 5:
            print(f"  {idx:2d}. {carrier}: ${row['RatePerMile_Carrier']:.2f}/mile "
                  f"({row['LoadCount']:,} loads, ${row['PayTotal']:,.2f} total)")
    
    # Spread Analysis
    print("\n💵 AVERAGE SPREAD (Customer Rate - Carrier Rate)")
    avg_spread = df['CustomerCarrierSpread'].mean()
    avg_spread_pct = df['SpreadPercentage'].mean()
    print(f"Average Spread per Load: ${avg_spread:,.2f}")
    print(f"Average Spread Percentage: {avg_spread_pct:.2f}%")
    
    return customer_rates, carrier_rates


def export_lane_rate_analysis(df, lane_volume, lane_revenue, lane_rates, 
                               lane_profit, rate_by_distance, rate_by_weight,
                               weekly_trends, monthly_trends, customer_rates, carrier_rates):
    """Export comprehensive lane/rate analysis to Excel."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Lane_Rate_Analysis_{timestamp}.xlsx"
    filepath = os.path.join(os.path.dirname(__file__), filename)
    
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        # Main data with calculated metrics
        df.to_excel(writer, sheet_name='All Data with Metrics', index=False)
        
        # Lane summaries
        lane_volume.to_excel(writer, sheet_name='Lane Volume')
        lane_revenue.to_excel(writer, sheet_name='Lane Revenue')
        lane_rates.to_excel(writer, sheet_name='Lane Rates')
        lane_profit.to_excel(writer, sheet_name='Lane Profitability')
        
        # Rate analysis
        rate_by_distance.to_excel(writer, sheet_name='Rates by Distance')
        rate_by_weight.to_excel(writer, sheet_name='Rates by Weight')
        
        # Time trends
        if weekly_trends is not None:
            weekly_trends.to_excel(writer, sheet_name='Weekly Trends')
        if monthly_trends is not None:
            monthly_trends.to_excel(writer, sheet_name='Monthly Trends')
        
        # Customer/Carrier rates
        customer_rates.to_excel(writer, sheet_name='Customer Rates')
        carrier_rates.to_excel(writer, sheet_name='Carrier Rates')
        
        # Detailed lane analysis
        lane_detail = df.groupby('Lane_StateToState').agg({
            'LoadDetailId': 'count',
            'RevenueTotal': ['sum', 'mean'],
            'PayTotal': ['sum', 'mean'],
            'GrossProfit': ['sum', 'mean'],
            'GrossMargin': 'mean',
            'RatePerMile_Revenue': 'mean',
            'RatePerMile_Customer': 'mean',
            'RatePerMile_Carrier': 'mean',
            'Miles': 'mean',
            'Weight': 'mean',
            'CustomerName': lambda x: ', '.join(x.unique()[:5]),  # Top 5 customers
            'CarrierName': lambda x: ', '.join(x.unique()[:5])  # Top 5 carriers
        })
        lane_detail.to_excel(writer, sheet_name='Lane Detail Summary')
    
    print(f"\n✅ Comprehensive analysis exported to: {filepath}")
    return filepath


def main():
    """Main function to run lane/rate analysis."""
    print("="*80)
    print("LANE & RATE ANALYSIS - TMS Load Data")
    print("="*80)
    
    try:
        # Load data
        df = load_data_from_db(limit=None)
        
        if df.empty:
            print("No data found in the table.")
            return
        
        # Prepare data
        print("\nPreparing data for analysis...")
        df = create_lane_identifier(df)
        df = calculate_rate_metrics(df)
        
        # Filter out invalid data
        df = df[df['Miles'] > 0]  # Remove loads with 0 miles
        df = df[df['RevenueTotal'] > 0]  # Remove loads with 0 revenue
        
        print(f"Analyzing {len(df):,} valid loads...")
        
        # Perform analyses
        lane_volume, lane_revenue, lane_rates = analyze_lanes(df)
        rate_by_distance, rate_by_weight = analyze_rates(df)
        lane_profit, lane_margin = analyze_profitability(df)
        weekly_trends, monthly_trends = analyze_trends(df)
        customer_rates, carrier_rates = analyze_customer_carrier_rates(df)
        
        # Export
        print("\n" + "="*80)
        try:
            export_choice = input("\nExport comprehensive analysis to Excel? (yes/no): ").lower().strip()
        except (EOFError, KeyboardInterrupt):
            # Non-interactive mode - auto export
            export_choice = 'yes'
            print("\nNon-interactive mode detected. Auto-exporting to Excel...")
        
        if export_choice in ['yes', 'y', '']:
            export_lane_rate_analysis(df, lane_volume, lane_revenue, lane_rates,
                                    lane_profit, rate_by_distance, rate_by_weight,
                                    weekly_trends, monthly_trends, customer_rates, carrier_rates)
        
        print("\n✅ Lane & Rate Analysis complete!")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

