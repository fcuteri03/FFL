"""
Database connection module for SQL Server.
"""

import pyodbc
from config import CONNECTION_STRING


class DatabaseConnection:
    """Handles SQL Server database connections."""
    
    def __init__(self, connection_string=None):
        """
        Initialize database connection.
        
        Args:
            connection_string (str, optional): Custom connection string. 
                                             If None, uses CONNECTION_STRING from config.
        """
        self.connection_string = connection_string or CONNECTION_STRING
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Establish connection to SQL Server database."""
        try:
            self.connection = pyodbc.connect(self.connection_string)
            self.cursor = self.connection.cursor()
            print("Successfully connected to SQL Server database!")
            return True
        except pyodbc.Error as e:
            print(f"Error connecting to database: {e}")
            return False
    
    def disconnect(self):
        """Close database connection."""
        try:
            if self.cursor:
                self.cursor.close()
                self.cursor = None
        except Exception:
            pass  # Cursor may already be closed
        
        try:
            if self.connection:
                self.connection.close()
                self.connection = None
                print("Database connection closed.")
        except Exception:
            pass  # Connection may already be closed
    
    def execute_query(self, query, params=None):
        """
        Execute a SELECT query and return results.
        
        Args:
            query (str): SQL query to execute
            params (tuple, optional): Parameters for parameterized query
            
        Returns:
            list: Query results
        """
        if not self.connection:
            raise Exception("Not connected to database. Call connect() first.")
        
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor.fetchall()
        except pyodbc.Error as e:
            print(f"Error executing query: {e}")
            raise
    
    def execute_non_query(self, query, params=None):
        """
        Execute INSERT, UPDATE, DELETE, or other non-query statements.
        
        Args:
            query (str): SQL statement to execute
            params (tuple, optional): Parameters for parameterized query
            
        Returns:
            int: Number of rows affected
        """
        if not self.connection:
            raise Exception("Not connected to database. Call connect() first.")
        
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.connection.commit()
            return self.cursor.rowcount
        except pyodbc.Error as e:
            self.connection.rollback()
            print(f"Error executing statement: {e}")
            raise
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


if __name__ == "__main__":
    # Example usage
    db = DatabaseConnection()
    
    if db.connect():
        try:
            # Example: Get database version
            result = db.execute_query("SELECT @@VERSION AS SQLServerVersion")
            print("\nSQL Server Version:")
            for row in result:
                print(row[0])
            
            # Example: List all tables
            tables = db.execute_query("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_TYPE = 'BASE TABLE'
            """)
            print("\nTables in database:")
            for table in tables:
                print(f"  - {table[0]}")
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            db.disconnect()

