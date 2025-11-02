import pandas as pd
from lightweight_charts import Chart
from datetime import datetime, timedelta
import os


def load_date_range(start_date, end_date, data_dir='./Data/Storage/BTCUSDTSWAP_candle1m/'):
    """
    Load candle data for a date range.
    
    Args:
        start_date: Start date as string 'YYYY-MM-DD' or datetime
        end_date: End date as string 'YYYY-MM-DD' or datetime
        data_dir: Directory containing the CSV files
    
    Returns:
        Combined DataFrame with all candles
    """
    # Convert to datetime if strings
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    dfs = []
    current_date = start_date
    
    # Iterate through each day in the range
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        file_path = os.path.join(data_dir, f'BTC-USDT-SWAP-candle1m-{date_str}.csv')
        
        if os.path.exists(file_path):
            print(f"Loading: {date_str}")
            df = pd.read_csv(file_path)
            # Clean and prepare candle data
            df = df.drop(['volume_ccy','volCcyQuote','timestamp'], axis=1)
            df.rename(columns={"timestamp_1m": 'time'}, inplace=True)
            df['time'] = pd.to_datetime(df['time'])
            # Ensure timezone-naive
            if df['time'].dt.tz is not None:
                df['time'] = df['time'].dt.tz_localize(None)
            dfs.append(df)
        else:
            print(f"Warning: File not found for {date_str}")
        
        current_date += timedelta(days=1)
    
    if not dfs:
        raise ValueError("No data files found in the specified range")
    
    # Combine all dataframes
    df_combined = pd.concat(dfs, ignore_index=True)
    
    # Sort by time to ensure proper ordering
    df_combined = df_combined.sort_values('time').reset_index(drop=True)
    
    return df_combined


if __name__ == '__main__':
    
    chart = Chart(toolbox=True)  # Enable toolbox for drawing tools
    
    # Option 1: Load specific date range (easy way)
    df = load_date_range('2021-10-01', '2021-10-03')
    
    # Option 2: Manual list of files (if you prefer)
    # files = [
    #     './Data/Storage/BTCUSDTSWAP_candle1m/BTC-USDT-SWAP-candle1m-2021-10-01.csv',
    #     './Data/Storage/BTCUSDTSWAP_candle1m/BTC-USDT-SWAP-candle1m-2021-10-02.csv',
    #     './Data/Storage/BTCUSDTSWAP_candle1m/BTC-USDT-SWAP-candle1m-2021-10-03.csv',
    # ]
    
    print(f"\nLoaded {len(df)} candles")
    print(f"Date range: {df['time'].min()} to {df['time'].max()}")
    print(f"Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
    
    chart.set(df)
    
    chart.show(block=True)