"""
Load Analysis Script for ReportMasterDataSetCache Table
Analyzes TMS load data from the database.
"""

import pandas as pd
from database_connection import DatabaseConnection
from datetime import datetime
import os


def load_data_from_db(limit=None):
    """
    Load ReportMasterDataSetCache table from database into pandas DataFrame.
    
    Args:
        limit (int, optional): Limit number of rows to load. If None, loads all rows.
    
    Returns:
        pandas.DataFrame: DataFrame containing the load data
    """
    query = "SELECT * FROM [dbo].[ReportMasterDataSetCache]"
    if limit:
        query += f" ORDER BY LoadDetailId OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
    
    print(f"Loading data from ReportMasterDataSetCache...")
    if limit:
        print(f"Limiting to {limit} rows for testing.")
    
    with DatabaseConnection() as db:
        # Get column names
        db.cursor.execute(f"SELECT TOP 1 * FROM [dbo].[ReportMasterDataSetCache]")
        columns = [column[0] for column in db.cursor.description]
        
        # Execute full query
        db.cursor.execute(query)
        rows = db.cursor.fetchall()
        
        # Convert to DataFrame
        df = pd.DataFrame.from_records(rows, columns=columns)
        
        print(f"Loaded {len(df)} rows and {len(df.columns)} columns.")
        return df


def analyze_loads(df):
    """
    Perform comprehensive analysis on load data.
    
    Args:
        df (pandas.DataFrame): DataFrame containing load data
    """
    print("\n" + "="*80)
    print("LOAD ANALYSIS SUMMARY")
    print("="*80)
    
    # Basic Statistics
    print(f"\n📊 BASIC STATISTICS")
    print(f"Total Loads: {len(df):,}")
    print(f"Date Range: {df['Created'].min()} to {df['Created'].max()}")
    print(f"Unique Customers: {df['CustomerId'].nunique():,}")
    print(f"Unique Carriers: {df['CarrierName'].nunique():,}")
    
    # Status Analysis
    print(f"\n📋 LOAD STATUS BREAKDOWN")
    status_counts = df['LoadStatus'].value_counts()
    for status, count in status_counts.head(10).items():
        pct = (count / len(df)) * 100
        print(f"  {status}: {count:,} ({pct:.1f}%)")
    
    # Financial Analysis
    print(f"\n💰 FINANCIAL METRICS")
    print(f"Total Revenue: ${df['RevenueTotal'].sum():,.2f}")
    print(f"Average Revenue per Load: ${df['RevenueTotal'].mean():,.2f}")
    print(f"Total Customer Due: ${df['CustomerDue'].sum():,.2f}")
    print(f"Total Carrier Balance Due: ${df['CarrierBalanceDue'].sum():,.2f}")
    print(f"Total Expenses: ${df['ExpenseTotal'].sum():,.2f}")
    
    # Coverage Analysis
    print(f"\n🚚 COVERAGE ANALYSIS")
    if 'IsCovered' in df.columns:
        covered = df['IsCovered'].sum()
        needs_covered = df['NeedsCovered'].sum() if 'NeedsCovered' in df.columns else 0
        print(f"Covered Loads: {covered:,} ({covered/len(df)*100:.1f}%)")
        print(f"Needs Coverage: {needs_covered:,} ({needs_covered/len(df)*100:.1f}%)")
    
    # Boolean Flags Analysis
    print(f"\n🏷️  FLAG ANALYSIS")
    boolean_columns = ['IsTonu', 'IsReadyToCover', 'IsSpecialBilling', 'IsPartial', 
                       'IsTrailerRental', 'IsVoid', 'IsEnterprise', 'CarrierPayHold']
    for col in boolean_columns:
        if col in df.columns:
            true_count = df[col].sum()
            print(f"  {col}: {true_count:,} ({true_count/len(df)*100:.1f}%)")
    
    # Top Customers
    print(f"\n👥 TOP 10 CUSTOMERS BY REVENUE")
    top_customers = df.groupby('CustomerName')['RevenueTotal'].sum().sort_values(ascending=False).head(10)
    for customer, revenue in top_customers.items():
        print(f"  {customer}: ${revenue:,.2f}")
    
    # Top Carriers
    print(f"\n🚛 TOP 10 CARRIERS BY LOAD COUNT")
    top_carriers = df.groupby('CarrierName').size().sort_values(ascending=False).head(10)
    for carrier, count in top_carriers.items():
        print(f"  {carrier}: {count:,} loads")
    
    # State Analysis
    print(f"\n🗺️  TOP 10 ORIGIN STATES")
    if 'OriginState' in df.columns:
        origin_states = df['OriginState'].value_counts().head(10)
        for state, count in origin_states.items():
            print(f"  {state}: {count:,} loads")
    
    print(f"\n🗺️  TOP 10 DESTINATION STATES")
    if 'FinalState' in df.columns:
        final_states = df['FinalState'].value_counts().head(10)
        for state, count in final_states.items():
            print(f"  {state}: {count:,} loads")
    
    # Trailer Type Analysis
    if 'TrailerType' in df.columns:
        print(f"\n📦 TRAILER TYPE DISTRIBUTION")
        trailer_types = df['TrailerType'].value_counts().head(10)
        for trailer, count in trailer_types.items():
            pct = (count / len(df)) * 100
            print(f"  {trailer}: {count:,} ({pct:.1f}%)")
    
    # Date Analysis
    if 'WeekStartDate' in df.columns:
        print(f"\n📅 LOADS BY WEEK")
        weekly_loads = df.groupby('WeekStartDate').size().sort_values(ascending=False).head(10)
        for week, count in weekly_loads.items():
            print(f"  {week}: {count:,} loads")
    
    print("\n" + "="*80)


def export_to_csv(df, filename=None):
    """
    Export DataFrame to CSV file.
    
    Args:
        df (pandas.DataFrame): DataFrame to export
        filename (str, optional): Output filename. If None, uses timestamp.
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ReportMasterDataSetCache_{timestamp}.csv"
    
    filepath = os.path.join(os.path.dirname(__file__), filename)
    df.to_csv(filepath, index=False)
    print(f"\n✅ Data exported to: {filepath}")
    return filepath


def export_to_excel(df, filename=None):
    """
    Export DataFrame to Excel file with multiple sheets for analysis.
    
    Args:
        df (pandas.DataFrame): DataFrame to export
        filename (str, optional): Output filename. If None, uses timestamp.
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ReportMasterDataSetCache_{timestamp}.xlsx"
    
    filepath = os.path.join(os.path.dirname(__file__), filename)
    
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        # Main data
        df.to_excel(writer, sheet_name='All Data', index=False)
        
        # Summary by Customer
        customer_summary = df.groupby('CustomerName').agg({
            'LoadDetailId': 'count',
            'RevenueTotal': 'sum',
            'CustomerDue': 'sum',
            'BillTotal': 'sum'
        }).rename(columns={'LoadDetailId': 'LoadCount'}).sort_values('RevenueTotal', ascending=False)
        customer_summary.to_excel(writer, sheet_name='Customer Summary')
        
        # Summary by Carrier
        carrier_summary = df.groupby('CarrierName').agg({
            'LoadDetailId': 'count',
            'PayTotal': 'sum',
            'CarrierBalanceDue': 'sum'
        }).rename(columns={'LoadDetailId': 'LoadCount'}).sort_values('LoadCount', ascending=False)
        carrier_summary.to_excel(writer, sheet_name='Carrier Summary')
        
        # Summary by Status
        status_summary = df.groupby('LoadStatus').agg({
            'LoadDetailId': 'count',
            'RevenueTotal': 'sum'
        }).rename(columns={'LoadDetailId': 'LoadCount'}).sort_values('LoadCount', ascending=False)
        status_summary.to_excel(writer, sheet_name='Status Summary')
        
        # Summary by Week
        if 'WeekStartDate' in df.columns:
            weekly_summary = df.groupby('WeekStartDate').agg({
                'LoadDetailId': 'count',
                'RevenueTotal': 'sum'
            }).rename(columns={'LoadDetailId': 'LoadCount'}).sort_index()
            weekly_summary.to_excel(writer, sheet_name='Weekly Summary')
    
    print(f"\n✅ Data exported to Excel: {filepath}")
    return filepath


def main():
    """Main function to run load analysis."""
    print("="*80)
    print("TMS LOAD ANALYSIS - ReportMasterDataSetCache")
    print("="*80)
    
    try:
        # Load data from database
        # Remove limit=None to load all data, or set limit=1000 for testing
        df = load_data_from_db(limit=None)
        
        if df.empty:
            print("No data found in the table.")
            return
        
        # Display basic info
        print(f"\nDataFrame Shape: {df.shape}")
        print(f"\nColumn Names:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")
        
        # Perform analysis
        analyze_loads(df)
        
        # Export options
        print("\n" + "="*80)
        print("EXPORT OPTIONS")
        print("="*80)
        
        export_choice = input("\nExport data? (csv/excel/both/none): ").lower().strip()
        
        if export_choice in ['csv', 'both']:
            export_to_csv(df)
        
        if export_choice in ['excel', 'both']:
            export_to_excel(df)
        
        if export_choice == 'none':
            print("Skipping export.")
        
        print("\n✅ Analysis complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

