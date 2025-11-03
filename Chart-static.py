import pandas as pd
from lightweight_charts import Chart
from datetime import datetime, timedelta
import os
import sys
import warnings
import contextlib

# Suppress pywebview cleanup warnings
warnings.filterwarnings('ignore')

@contextlib.contextmanager
def suppress_stderr():
    """Temporarily suppress stderr to hide pywebview cleanup errors"""
    old_stderr = sys.stderr
    sys.stderr = open(os.devnull, 'w')
    try:
        yield
    finally:
        sys.stderr.close()
        sys.stderr = old_stderr


def load_date_range(start_date, end_date, data_dir='./Data/Storage/BTCUSDTSWAP_candle1m/', timeframe='1m'):
    """
    Load candle data for a date range.
    
    Args:
        start_date: Start date as string 'YYYY-MM-DD' or datetime
        end_date: End date as string 'YYYY-MM-DD' or datetime
        data_dir: Directory containing the CSV files
        timeframe: '1m' or '1s' for 1-minute or 1-second candles
    
    Returns:
        Combined DataFrame with all candles
    """
    # Convert to datetime if strings
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Determine column name based on timeframe
    time_col = 'timestamp_1s' if timeframe == '1s' else 'timestamp_1m'
    
    dfs = []
    current_date = start_date
    
    # Iterate through each day in the range
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        file_path = os.path.join(data_dir, f'BTC-USDT-SWAP-candle{timeframe}-{date_str}.csv')
        
        if os.path.exists(file_path):
            print(f"Loading {timeframe}: {date_str}")
            df = pd.read_csv(file_path)
            # Clean and prepare candle data
            df = df.drop(['volume_ccy','volCcyQuote','timestamp'], axis=1)
            df.rename(columns={time_col: 'time'}, inplace=True)
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
    
    # Create main chart for 1-minute candles (top)
    chart = Chart(
        toolbox=True,
        inner_width=1.0,
        inner_height=0.6  # Takes 60% of the window height
    )
    
    # Load 1-minute candle data
    df_1m = load_date_range(
        '2021-10-01', 
        '2021-10-03',
        data_dir='./Data/Storage/BTCUSDTSWAP_candle1m/',
        timeframe='1m'
    )
    
    print(f"\nLoaded {len(df_1m)} 1-minute candles")
    print(f"Date range: {df_1m['time'].min()} to {df_1m['time'].max()}")
    print(f"Price range: ${df_1m['low'].min():.2f} - ${df_1m['high'].max():.2f}")
    
    # Load fill history (trades)
    fills = pd.read_csv("./fill_historys.csv")
    fills['time'] = pd.to_datetime(fills['ts'], unit='ms')
    # Ensure timezone-naive
    if fills['time'].dt.tz is not None:
        fills['time'] = fills['time'].dt.tz_localize(None)
    
    # Filter fills for the date range
    start_time = df_1m['time'].min()
    end_time = df_1m['time'].max()
    fills_filtered = fills[(fills['time'] >= start_time) & (fills['time'] <= end_time)]
    
    print(f"\nLoaded {len(fills_filtered)} trades in date range")
    
    chart.set(df_1m)
    
    # Add trade markers to 1-minute chart
    for _, trade in fills_filtered.iterrows():
        # Entry trades (opening positions)
        if trade['role'] == 'open':
            if trade['side'] == 'BUY':
                # Long entry - green arrow up below the candle
                chart.marker(
                    time=trade['time'],
                    position='below',
                    shape='arrow_up',
                    color='#26a69a',  # Green
                    text=f"LONG {trade['qty']:.2f}@{trade['price']:.1f}"
                )
            else:  # SELL
                # Short entry - red arrow down above the candle
                chart.marker(
                    time=trade['time'],
                    position='above',
                    shape='arrow_down',
                    color='#ef5350',  # Red
                    text=f"SHORT {trade['qty']:.2f}@{trade['price']:.1f}"
                )
        
        # Exit trades (closing positions)
        else:  # role == 'close'
            if trade['side'] == 'SELL':
                # Closing long position - circle above
                chart.marker(
                    time=trade['time'],
                    position='above',
                    shape='circle',
                    color='#4caf50',  # Light green
                    text=f"EXIT {trade['tag']} {trade['qty']:.2f}@{trade['price']:.1f}"
                )
            else:  # BUY
                # Closing short position - circle below
                chart.marker(
                    time=trade['time'],
                    position='below',
                    shape='circle',
                    color='#ff5252',  # Light red
                    text=f"EXIT {trade['tag']} {trade['qty']:.2f}@{trade['price']:.1f}"
                )
    
    print(f"Added {len(fills_filtered)} trade markers to 1-minute chart")
    
    # Enable legend to show OHLC and returns on hover
    chart.legend(
        visible=True,
        ohlc=True,  # Show Open, High, Low, Close
        percent=True,  # Show percentage change
        color_based_on_candle=True  # Color changes based on candle direction
    )
    
    # Create subchart for 1-second candles (bottom)
    # No sync parameter means independent scrolling
    subchart = chart.create_subchart(
        position='bottom',
        width=1.0,
        height=0.4  # Takes 40% of the window height
    )
    
    # Load 1-second candle data
    df_1s = load_date_range(
        '2021-10-01', 
        '2021-10-03',
        data_dir='./Data/Storage/BTCUSDTSWAP_candle1s/',
        timeframe='1s'
    )
    
    print(f"\nLoaded {len(df_1s)} 1-second candles")
    print(f"Date range: {df_1s['time'].min()} to {df_1s['time'].max()}")
    
    subchart.set(df_1s)
    
    # Add trade markers to 1-second chart (same trades, different timeframe view)
    for _, trade in fills_filtered.iterrows():
        # Entry trades (opening positions)
        if trade['role'] == 'open':
            if trade['side'] == 'BUY':
                subchart.marker(
                    time=trade['time'],
                    position='below',
                    shape='arrow_up',
                    color='#26a69a',
                    text=f"LONG {trade['qty']:.2f}@{trade['price']:.1f}"
                )
            else:  # SELL
                subchart.marker(
                    time=trade['time'],
                    position='above',
                    shape='arrow_down',
                    color='#ef5350',
                    text=f"SHORT {trade['qty']:.2f}@{trade['price']:.1f}"
                )
        
        # Exit trades (closing positions)
        else:  # role == 'close'
            if trade['side'] == 'SELL':
                subchart.marker(
                    time=trade['time'],
                    position='above',
                    shape='circle',
                    color='#4caf50',
                    text=f"EXIT {trade['tag']} {trade['qty']:.2f}@{trade['price']:.1f}"
                )
            else:  # BUY
                subchart.marker(
                    time=trade['time'],
                    position='below',
                    shape='circle',
                    color='#ff5252',
                    text=f"EXIT {trade['tag']} {trade['qty']:.2f}@{trade['price']:.1f}"
                )
    
    print(f"Added {len(fills_filtered)} trade markers to 1-second chart")
    
    # Enable legend for 1s candles too
    subchart.legend(
        visible=True,
        ohlc=True,  # Show Open, High, Low, Close
        percent=True,  # Show percentage change
        color_based_on_candle=True  # Color changes based on candle direction
    )
    
    # Configure time scale to show seconds for 1s candles
    subchart.time_scale(
        time_visible=True,
        seconds_visible=True  # This enables seconds display
    )
    
    print("\n Chart ready! Top: 1-minute candles | Bottom: 1-second candles")
    
    # Show chart and suppress cleanup errors when closing
    with suppress_stderr():
        try:
            chart.show(block=True)
        finally:
            # Quick exit to avoid file cleanup warnings
            pass
    
    # Exit cleanly
    sys.exit(0)