"""
Quick analysis script - non-interactive version for automation.
"""

import pandas as pd
from database_connection import DatabaseConnection


def get_load_data(query=None):
    """
    Get load data from ReportMasterDataSetCache table.
    
    Args:
        query (str, optional): Custom SQL query. If None, selects all data.
    
    Returns:
        pandas.DataFrame: DataFrame containing the load data
    """
    if query is None:
        query = "SELECT * FROM [dbo].[ReportMasterDataSetCache]"
    
    with DatabaseConnection() as db:
        db.cursor.execute(query)
        columns = [column[0] for column in db.cursor.description]
        rows = db.cursor.fetchall()
        return pd.DataFrame.from_records(rows, columns=columns)


def get_summary_stats(df):
    """
    Get summary statistics for the load data.
    
    Args:
        df (pandas.DataFrame): DataFrame containing load data
    
    Returns:
        dict: Dictionary containing summary statistics
    """
    return {
        'total_loads': len(df),
        'total_revenue': float(df['RevenueTotal'].sum()),
        'avg_revenue': float(df['RevenueTotal'].mean()),
        'total_customer_due': float(df['CustomerDue'].sum()),
        'total_carrier_balance': float(df['CarrierBalanceDue'].sum()),
        'unique_customers': int(df['CustomerId'].nunique()),
        'unique_carriers': int(df['CarrierName'].nunique()),
        'covered_loads': int(df['IsCovered'].sum()) if 'IsCovered' in df.columns else 0,
        'needs_coverage': int(df['NeedsCovered'].sum()) if 'NeedsCovered' in df.columns else 0,
    }


if __name__ == "__main__":
    # Quick example
    df = get_load_data()
    stats = get_summary_stats(df)
    
    print("Quick Summary:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

