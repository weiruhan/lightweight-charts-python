import pandas as pd
import numpy as np
from lightweight_charts import Chart
from datetime import datetime, timedelta
from time import sleep
import signal
import sys
import os


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\nInterrupt received, closing chart...')
    try:
        if 'chart' in globals():
            chart.exit()
    except Exception as e:
        print(f"Error during cleanup: {e}")
    sys.exit(0)


def load_date_range(start_date, end_date, data_dir='./Data/Storage/BTCUSDTSWAP_candle1m/', timeframe='1m'):
    """
    Load candle data for a date range.
    
    Args:
        start_date: Start date as string 'YYYY-MM-DD' or datetime
        end_date: End date as string 'YYYY-MM-DD' or datetime
        data_dir: Directory containing the CSV files
        timeframe: '1m' or '1s' for 1-minute or 1-second candles
    
    Returns:
        List of DataFrames (one per day) for progressive loading
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
    
    return dfs


if __name__ == '__main__':
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        chart = Chart(toolbox=True)  # Enable toolbox for drawing tools
        
        # ========== CONFIGURE DATE RANGE HERE ==========
        START_DATE = '2021-10-01'
        END_DATE = '2021-10-02'
        # ===============================================
        
        # Load candle data for date range
        dfs = load_date_range(START_DATE, END_DATE)
        
        if len(dfs) < 2:
            print("Error: Need at least 2 days of data for live updates")
            sys.exit(1)
        
        # First dataframe for initial display
        df1 = dfs[0]
        # Remaining dataframes for live updates
        df_remaining = pd.concat(dfs[1:], ignore_index=True)
        
        # Combine all for trade filtering
        df_all = pd.concat(dfs, ignore_index=True)
        
        print(f"\nLoaded {len(df1)} initial candles")
        print(f"Loaded {len(df_remaining)} candles for live updates")
        print(f"Date range: {df_all['time'].min()} to {df_all['time'].max()}")
        print(f"Price range: ${df_all['low'].min():.2f} - ${df_all['high'].max():.2f}")
        
        # Load fill history (trades)
        fills = pd.read_csv("./fill_historys.csv")
        fills['time'] = pd.to_datetime(fills['ts'], unit='ms')
        # Ensure timezone-naive
        if fills['time'].dt.tz is not None:
            fills['time'] = fills['time'].dt.tz_localize(None)
        
        # Filter fills for the date range we're displaying
        start_time = df_all['time'].min()
        end_time = df_all['time'].max()
        fills = fills[(fills['time'] >= start_time) & (fills['time'] <= end_time)]
        
        print(f"Loaded {len(fills)} trades between {start_time} and {end_time}")
        
        # Set initial data
        chart.set(df1)
        
        # Enable legend
        chart.legend(
            visible=True,
            ohlc=True,
            percent=True,
            color_based_on_candle=True
        )
        
        # Add markers for all trades in df1
        df1_max_time = df1['time'].max()
        fills_df1 = fills[fills['time'] <= df1_max_time]
        
        for _, trade in fills_df1.iterrows():
            # Entry trades (opening positions)
            if trade['role'] == 'open':
                if trade['side'] == 'BUY':
                    # Long entry - green arrow pointing up, below candle
                    chart.marker(
                        time=trade['time'],
                        position='below',
                        shape='arrow_up',
                        color='#26a69a',  # Green
                        text=f"LONG {trade['qty']:.2f}@{trade['price']:.1f}"
                    )
                else:  # SELL
                    # Short entry - red arrow pointing down, above candle
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
        
        print(f"Added {len(fills_df1)} trade markers to chart")
        chart.show(block=False)  # Show window but don't block yet
        
        # Live update with remaining data
        print(f"Starting live updates with {len(df_remaining)} candles...")
        fills_remaining = fills[fills['time'] > df1_max_time]
        
        window_closed = False
        for i, series in df_remaining.iterrows():
            try:
                if not chart.is_alive:
                    print("Chart window closed by user.")
                    window_closed = True
                    break
                
                chart.update(series)
                
                # Check if there's a trade at this time
                current_time = series['time']
                trades_at_time = fills_remaining[fills_remaining['time'] == current_time]
            except Exception as e:
                # WebView2 was disposed (user closed window)
                if "ObjectDisposedException" in str(type(e).__name__) or "disposed" in str(e).lower():
                    print("Chart window closed by user.")
                    window_closed = True
                    break
                # Re-raise other exceptions
                raise
            
            for _, trade in trades_at_time.iterrows():
                if trade['role'] == 'open':
                    if trade['side'] == 'BUY':
                        chart.marker(
                            time=trade['time'],
                            position='below',
                            shape='arrow_up',
                            color='#26a69a',
                            text=f"LONG {trade['qty']:.2f}@{trade['price']:.1f}"
                        )
                    else:
                        chart.marker(
                            time=trade['time'],
                            position='above',
                            shape='arrow_down',
                            color='#ef5350',
                            text=f"SHORT {trade['qty']:.2f}@{trade['price']:.1f}"
                        )
                else:
                    if trade['side'] == 'SELL':
                        chart.marker(
                            time=trade['time'],
                            position='above',
                            shape='circle',
                            color='#4caf50',
                            text=f"EXIT {trade['tag']} {trade['qty']:.2f}@{trade['price']:.1f}"
                        )
                    else:
                        chart.marker(
                            time=trade['time'],
                            position='below',
                            shape='circle',
                            color='#ff5252',
                            text=f"EXIT {trade['tag']} {trade['qty']:.2f}@{trade['price']:.1f}"
                        )
                print(f"[LIVE] {trade['role'].upper()} {trade['side']} @ {current_time}")
            
            sleep(0.05)  # Faster updates
        
        # After all updates, block until window is closed
        print("\nAll data loaded. Chart will remain open until you close the window.")
        print("(Close the window or press Ctrl+C to exit)")
        
        # This will block until the window is closed
        import asyncio
        asyncio.run(chart.show_async())
            
    except KeyboardInterrupt:
        print('\nInterrupt received, closing chart...')
    except Exception as e:
        # Filter out ObjectDisposedException which is expected when closing
        if "ObjectDisposedException" not in str(type(e).__name__) and "disposed" not in str(e).lower():
            print(f"Error occurred: {e}")
            import traceback
            traceback.print_exc()
    finally:
        # Simplified cleanup
        print("Chart closed.")
        # Force immediate exit to avoid file cleanup issues
        os._exit(0)
