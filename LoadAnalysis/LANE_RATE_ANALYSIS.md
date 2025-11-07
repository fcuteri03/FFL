# Lane & Rate Analysis Guide

This document describes the comprehensive lane and rate analysis capabilities for TMS load data.

## Overview

The `lane_rate_analysis.py` script provides detailed analysis of transportation lanes and rates to help optimize pricing, identify profitable routes, and make data-driven decisions.

## Key Analysis Features

### 1. Lane Identification
- **State-to-State Lanes**: High-level lane analysis (e.g., "CA → TX")
- **City-to-City Lanes**: Detailed lane analysis (e.g., "Los Angeles, CA → Dallas, TX")
- **Primary Lane**: Uses existing Lane column if available, otherwise defaults to State-to-State

### 2. Rate Metrics Calculated

#### Rate per Mile
- Revenue Rate per Mile: `RevenueTotal / Miles`
- Customer Rate per Mile: `BillTotal / Miles`
- Carrier Rate per Mile: `PayTotal / Miles`

#### Rate per Weight (CWT - per 100 lbs)
- Revenue Rate per CWT: `RevenueTotal / (Weight / 100)`
- Customer Rate per CWT: `BillTotal / (Weight / 100)`
- Carrier Rate per CWT: `PayTotal / (Weight / 100)`

#### Profitability Metrics
- Gross Profit: `RevenueTotal - PayTotal`
- Gross Margin: `(GrossProfit / RevenueTotal) * 100`
- Profit per Mile: `GrossProfit / Miles`
- Customer-Carrier Spread: `BillTotal - PayTotal`
- Spread Percentage: `(Spread / BillTotal) * 100`

### 3. Lane Analysis

#### Volume Analysis
- Top lanes by load count
- Lane frequency distribution
- High-volume corridors identification

#### Revenue Analysis
- Top lanes by total revenue
- Average revenue per lane
- Revenue concentration analysis

#### Rate Analysis
- Top lanes by rate per mile
- Rate variance by lane
- Rate consistency analysis

### 4. Rate Analysis

#### Overall Rate Statistics
- Mean, median, and percentile distributions
- Rate spread analysis (customer vs carrier)
- Rate volatility metrics

#### Rate by Distance
- Short-haul (0-100 miles)
- Medium-haul (101-500 miles)
- Long-haul (500+ miles)
- Rate patterns by distance

#### Rate by Weight
- Light loads (0-10k lbs)
- Medium loads (10k-30k lbs)
- Heavy loads (30k+ lbs)
- Rate patterns by weight

### 5. Profitability Analysis

#### Overall Metrics
- Total gross profit
- Overall gross margin
- Average profit per load
- Average profit per mile

#### Lane Profitability
- Most profitable lanes (by total profit)
- Highest margin lanes (by percentage)
- Underperforming lanes (negative margin)
- Profit consistency by lane

### 6. Time-Based Trend Analysis

#### Weekly Trends
- Load volume trends
- Revenue trends
- Rate trends
- Profitability trends

#### Monthly Trends
- Seasonal patterns
- Month-over-month comparisons
- Long-term rate trends

### 7. Customer vs Carrier Rate Analysis

#### Customer Analysis
- Top customers by rate per mile
- Customer rate consistency
- Customer profitability

#### Carrier Analysis
- Top carriers by rate per mile
- Carrier rate competitiveness
- Carrier utilization

#### Spread Analysis
- Average spread per load
- Spread percentage
- Spread by lane

## Usage

### Basic Usage

```python
python lane_rate_analysis.py
```

### Programmatic Usage

```python
from lane_rate_analysis import load_data_from_db, create_lane_identifier, calculate_rate_metrics

# Load data
df = load_data_from_db()

# Prepare data
df = create_lane_identifier(df)
df = calculate_rate_metrics(df)

# Your custom analysis here
```

## Export Options

The script exports comprehensive analysis to Excel with multiple sheets:

1. **All Data with Metrics**: Complete dataset with calculated metrics
2. **Lane Volume**: Load counts by lane
3. **Lane Revenue**: Revenue totals by lane
4. **Lane Rates**: Rate per mile by lane
5. **Lane Profitability**: Profit and margin by lane
6. **Rates by Distance**: Rate analysis by distance ranges
7. **Rates by Weight**: Rate analysis by weight ranges
8. **Weekly Trends**: Time-based weekly analysis
9. **Monthly Trends**: Time-based monthly analysis
10. **Customer Rates**: Customer rate analysis
11. **Carrier Rates**: Carrier rate analysis
12. **Lane Detail Summary**: Comprehensive lane-level summary

## Key Insights You Can Gain

### Pricing Optimization
- Identify lanes with high rates but low volume (opportunity for growth)
- Find lanes with low rates but high volume (pricing review needed)
- Compare your rates to market averages

### Route Optimization
- Identify most profitable lanes for expansion
- Find underperforming lanes that need attention
- Understand seasonal patterns for capacity planning

### Customer Management
- Identify high-value customers
- Find customers with consistent, profitable lanes
- Understand customer rate patterns

### Carrier Management
- Identify competitive carriers
- Find carriers with consistent performance
- Understand carrier rate patterns

### Strategic Planning
- Identify growth opportunities
- Understand market trends
- Plan for seasonal variations

## Best Practices

1. **Regular Analysis**: Run analysis monthly or quarterly to track trends
2. **Lane Minimums**: Focus on lanes with at least 3-5 loads for statistical significance
3. **Time Periods**: Analyze different time periods to understand trends
4. **Comparative Analysis**: Compare current period to previous periods
5. **Action Items**: Use insights to create actionable pricing and routing strategies

## Example Use Cases

### Use Case 1: Identify Pricing Opportunities
- Find lanes with high volume but below-average rates
- Target these lanes for rate increases
- Monitor impact over time

### Use Case 2: Optimize Carrier Selection
- Compare carrier rates by lane
- Identify most cost-effective carriers per lane
- Negotiate better rates with high-volume carriers

### Use Case 3: Seasonal Planning
- Identify seasonal patterns in rates and volumes
- Plan capacity for high-volume periods
- Adjust pricing for seasonal demand

### Use Case 4: Customer Profitability
- Identify most profitable customers
- Understand customer rate patterns
- Develop customer-specific pricing strategies

## Notes

- The script filters out loads with 0 miles or 0 revenue
- All monetary values are in the currency of your database
- Rates are calculated only for loads with valid distance/weight data
- Percentile analysis helps identify outliers and normal ranges

