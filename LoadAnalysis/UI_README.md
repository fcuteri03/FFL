# TMS Lane & Rate Analysis Dashboard

Interactive web-based dashboard for analyzing TMS load data.

## Features

- 📊 **Overview Dashboard**: Key metrics and visualizations
- 🛣️ **Lane Analysis**: Top lanes by volume, revenue, and profitability
- 💰 **Rate Analysis**: Rate distributions and comparisons
- 📈 **Trends**: Time-based analysis (monthly/weekly trends)
- 📋 **Data Explorer**: Interactive data table with filtering and export

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the dashboard:**
   ```bash
   streamlit run app.py
   ```

   Or use the provided scripts:
   - **Windows Batch**: Double-click `run_app.bat`
   - **PowerShell**: Run `.\run_app.ps1`

## Usage

1. **Start the app**: Run `streamlit run app.py`
2. **Open browser**: The app will automatically open in your default browser at `http://localhost:8501`
3. **Use filters**: Use the sidebar to filter by date range, states, customers, etc.
4. **Explore tabs**: Navigate between different analysis views
5. **Export data**: Use the Data Explorer tab to download filtered data as CSV

## Features Overview

### Overview Tab
- Key metrics (total loads, revenue, profit, margins)
- Top lanes by volume chart
- Revenue vs Profit scatter plot

### Lane Analysis Tab
- Top lanes by volume and revenue tables
- Lane profitability chart
- Interactive lane comparisons

### Rate Analysis Tab
- Rate distribution histogram
- Rate by distance range analysis
- Customer vs Carrier rate comparisons

### Trends Tab
- Monthly load volume and revenue trends
- Rate per mile trends over time
- Time-based patterns

### Data Explorer Tab
- Interactive data table
- Column selection
- Search functionality
- CSV export

## Configuration

The app uses the same database connection settings from `config.py`. Make sure your connection string is configured correctly.

## Troubleshooting

- **Port already in use**: If port 8501 is busy, Streamlit will use the next available port
- **Connection errors**: Check your database connection string in `config.py`
- **Slow loading**: Data is cached for 1 hour. Refresh the page to reload from database

## Tips

- Use the sidebar filters to narrow down your analysis
- Hover over charts for detailed information
- Export filtered data from the Data Explorer tab
- The dashboard automatically refreshes when you change filters

