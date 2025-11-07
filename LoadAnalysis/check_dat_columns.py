"""
Check for DAT columns in the database table.
"""

from database_connection import DatabaseConnection
import pandas as pd

def check_dat_columns():
    """Check what DAT-related columns exist in the table."""
    query = "SELECT TOP 1 * FROM [dbo].[ReportMasterDataSetCache]"
    
    db = DatabaseConnection()
    if not db.connect():
        print("Failed to connect to database.")
        return
    
    try:
        db.cursor.execute(query)
        columns = [column[0] for column in db.cursor.description]
        
        print("All columns in ReportMasterDataSetCache:")
        print("=" * 60)
        for i, col in enumerate(columns, 1):
            print(f"{i:3d}. {col}")
        
        print("\n" + "=" * 60)
        print("DAT-related columns found:")
        print("=" * 60)
        dat_columns = [col for col in columns if 'DAT' in col.upper()]
        
        if dat_columns:
            for col in dat_columns:
                print(f"  ✓ {col}")
        else:
            print("  ✗ No DAT columns found")
            print("\nPossible DAT column names to check:")
            print("  - DATRate")
            print("  - DATTotal")
            print("  - DATMarketRate")
            print("  - DATRatePerMile")
            print("  - DATSpotRate")
            print("  - DATMarketRatePerMile")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.disconnect()

if __name__ == "__main__":
    check_dat_columns()

