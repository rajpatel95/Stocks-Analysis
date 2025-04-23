import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

# Set pandas display options
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.float_format', lambda x: '%.2f' % x)

def analyze_stock_recovery(ticker, start_date="2015-01-01", end_date="2025-04-19", drop_threshold=20):
    # Get data from Yahoo Finance
    data = yf.download(ticker, start=start_date, end=end_date, interval="1d")
    
    # Calculate All-Time High using High prices for the specific ticker
    high_prices = data['High'][ticker] if isinstance(data['High'], pd.DataFrame) else data['High']
    low_prices = data['Low'][ticker] if isinstance(data['Low'], pd.DataFrame) else data['Low']
    close_prices = data['Close'][ticker] if isinstance(data['Close'], pd.DataFrame) else data['Close']
    
    # Get the latest close price for unrecovered drops
    latest_price = close_prices[-1]
    latest_date = data.index[-1]
    
    # Calculate All-Time High and track its date
    all_time_high = high_prices.cummax()
    
    # Create a series to track ATH dates
    ath_dates = pd.Series(index=data.index, dtype='datetime64[ns]')
    current_ath = float('-inf')
    current_ath_date = None
    
    for date in data.index:
        if high_prices[date] >= current_ath:
            current_ath = high_prices[date]
            current_ath_date = date
        ath_dates[date] = current_ath_date
    
    # Add columns to the dataframe
    data.loc[:, ('AllTimeHigh', '')] = all_time_high
    data.loc[:, ('ATHDate', '')] = ath_dates
    data.loc[:, ('DropPercent', '')] = ((all_time_high - low_prices) / all_time_high * 100).round(2)
    
    # Find dates where drop was around threshold% (between threshold-2 and threshold+2)
    drop_dates = data[
        (data[('DropPercent', '')] >= drop_threshold-2) & 
        (data[('DropPercent', '')] <= drop_threshold+2)
    ].index
    
    # Analyze recovery for each drop
    recovery_data = []
    
    for drop_date in drop_dates:
        drop_ath = data.loc[drop_date, ('AllTimeHigh', '')]
        ath_date = data.loc[drop_date, ('ATHDate', '')]
        drop_price = close_prices[drop_date]  # Price at drop
        drop_low = low_prices[drop_date]      # Day's low at drop
        
        # Get all data after the drop
        future_data = data[drop_date:]
        
        # Find first date where price exceeds previous ATH
        recovery_dates = future_data[future_data['High'][ticker] >= drop_ath].index if isinstance(data['High'], pd.DataFrame) else future_data[future_data['High'] >= drop_ath].index
        
        if len(recovery_dates) > 0:
            recovery_date = recovery_dates[0]
            days_to_recover = (recovery_date - drop_date).days
            recovery_price = high_prices[recovery_date]  # Price at recovery
            status = "Recovered"
        else:
            recovery_date = latest_date
            days_to_recover = None
            recovery_price = latest_price  # Use current price for unrecovered drops
            status = "Not Recovered"
            
        recovery_data.append({
            'Drop_Date': drop_date,
            'ATH_Date': ath_date,
            'ATH_Price': drop_ath,
            'Drop_Low': drop_low,
            'Drop_Close': drop_price,
            'Drop_Percentage': data.loc[drop_date, ('DropPercent', '')],
            'Recovery_Date': recovery_date,
            'Recovery_Price': recovery_price,
            'Current_Recovery_Percent': ((recovery_price - drop_low) / drop_low * 100).round(2),
            'Days_to_Recover': days_to_recover,
            'Status': status
        })
    
    recovery_df = pd.DataFrame(recovery_data)
    
    # Format the DataFrame for better readability
    if not recovery_df.empty:
        recovery_df['Drop_Date'] = recovery_df['Drop_Date'].dt.strftime('%Y-%m-%d')
        recovery_df['ATH_Date'] = recovery_df['ATH_Date'].dt.strftime('%Y-%m-%d')
        recovery_df['Recovery_Date'] = recovery_df['Recovery_Date'].dt.strftime('%Y-%m-%d')
        
        # Reorder and rename columns for clarity
        recovery_df = recovery_df.rename(columns={
            'Drop_Date': 'Drop Date',
            'ATH_Date': 'ATH Date',
            'ATH_Price': 'ATH Price',
            'Drop_Low': 'Drop Low',
            'Drop_Close': 'Drop Close',
            'Drop_Percentage': 'Drop %',
            'Recovery_Date': 'Recovery/Current Date',
            'Recovery_Price': 'Recovery/Current Price',
            'Current_Recovery_Percent': 'Recovery %',
            'Days_to_Recover': 'Days to Recover',
            'Status': 'Status'
        })
    
    return recovery_df

# Get user input for ticker and threshold
ticker = input("Enter the ticker symbol: ")
drop_threshold = int(input("Enter the drop threshold percentage: "))

# Run the analysis with user inputs
recovery_analysis = analyze_stock_recovery(ticker, drop_threshold=drop_threshold)

print("\nDetailed Recovery Analysis:")
if not recovery_analysis.empty:
    # First show unrecovered drops
    unrecovered = recovery_analysis[recovery_analysis['Status'] == "Not Recovered"]
    if not unrecovered.empty:
        print("\nUNRECOVERED DROPS:")
        print(unrecovered[['Drop Date', 'ATH Price', 'Drop Low', 'Recovery/Current Price', 'Drop %', 'Recovery %']].to_string(index=False))
    
    # Then show recovered drops
    recovered = recovery_analysis[recovery_analysis['Status'] == "Recovered"]
    if not recovered.empty:
        print("\nRECOVERED DROPS:")
        print(recovered[['Drop Date', 'ATH Price', 'Drop Low', 'Recovery/Current Price', 'Drop %', 'Days to Recover']].to_string(index=False))
    
    print("\nSummary Statistics:")
    print(f"Total number of {drop_threshold}% drops: {len(recovery_analysis)}")
    print(f"Number of recovered drops: {len(recovered)}")
    print(f"Number of unrecovered drops: {len(unrecovered)}")
    
    if not recovered.empty:
        print(f"\nRecovery Statistics (for recovered drops):")
        print(f"Average recovery time: {recovered['Days to Recover'].mean():.0f} days")
        print(f"Fastest recovery: {recovered['Days to Recover'].min():.0f} days")
        print(f"Longest recovery: {recovered['Days to Recover'].max():.0f} days")
else:
    print(f"No drops of {drop_threshold}% or more found in the given time period.")
