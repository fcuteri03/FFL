"""
Configuration file for database connection.
Replace the connection string with your actual SQL Server connection string.
"""

# SQL Server connection string
# Format: "DRIVER={ODBC Driver 17 for SQL Server};SERVER=your_server;DATABASE=your_database;UID=your_username;PWD=your_password"
# Or use Windows Authentication: "DRIVER={ODBC Driver 17 for SQL Server};SERVER=your_server;DATABASE=your_database;Trusted_Connection=yes;"
CONNECTION_STRING = "DRIVER={ODBC Driver 18 for SQL Server};Server=tcp:dfdatarep.database.windows.net,1433;Database=DFMain;Uid=DFAdmin;Pwd=TBYObAnSTyK04rhAcf5s;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

