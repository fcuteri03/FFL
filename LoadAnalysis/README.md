# SQL Server Database Connection Project

This Python project provides a simple interface to connect to and interact with a SQL Server database.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure your connection string:**
   - Open `config.py`
   - Replace the `CONNECTION_STRING` with your actual SQL Server connection details
   
   **Connection String Formats:**
   
   **SQL Server Authentication:**
   ```
   DRIVER={ODBC Driver 17 for SQL Server};SERVER=your_server;DATABASE=your_database;UID=your_username;PWD=your_password
   ```
   
   **Windows Authentication:**
   ```
   DRIVER={ODBC Driver 17 for SQL Server};SERVER=your_server;DATABASE=your_database;Trusted_Connection=yes;
   ```
   
   **Note:** If you're using a different ODBC driver version, you may need to adjust the DRIVER name (e.g., `ODBC Driver 18 for SQL Server` or `SQL Server`).

## Usage

### Basic Usage

```python
from database_connection import DatabaseConnection

# Create connection
db = DatabaseConnection()

# Connect to database
if db.connect():
    # Execute a query
    results = db.execute_query("SELECT * FROM YourTable")
    for row in results:
        print(row)
    
    # Disconnect
    db.disconnect()
```

### Using Context Manager

```python
from database_connection import DatabaseConnection

# Automatically handles connection and disconnection
with DatabaseConnection() as db:
    results = db.execute_query("SELECT * FROM YourTable")
    for row in results:
        print(row)
```

### Execute Non-Query Statements

```python
with DatabaseConnection() as db:
    # Insert example
    db.execute_non_query(
        "INSERT INTO YourTable (column1, column2) VALUES (?, ?)",
        ('value1', 'value2')
    )
    
    # Update example
    db.execute_non_query(
        "UPDATE YourTable SET column1 = ? WHERE id = ?",
        ('new_value', 1)
    )
```

## Running the Example

Run the main script to test your connection:

```bash
python database_connection.py
```

This will:
- Connect to your database
- Display SQL Server version
- List all tables in the database

## Troubleshooting

- **ODBC Driver not found:** Make sure you have the SQL Server ODBC driver installed. You can download it from Microsoft's website.
- **Connection timeout:** Check that your server name, database name, and credentials are correct.
- **Firewall issues:** Ensure your firewall allows connections to the SQL Server port (default: 1433).

