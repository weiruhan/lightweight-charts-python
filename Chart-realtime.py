import pandas as pd
import numpy as np
from lightweight_charts import Chart
from time import sleep
import signal
import sys


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\nInterrupt received, closing chart...')
    try:
        if 'chart' in globals():
            chart.exit()
    except Exception as e:
        print(f"Error during cleanup: {e}")
    sys.exit(0)


if __name__ == '__main__':
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        chart = Chart(toolbox=True)  # Enable toolbox for drawing tools
        
        # Load candle data
        df1 = pd.read_csv("./Data/Storage/BTCUSDTSWAP_candle1m/BTC-USDT-SWAP-candle1m-2021-10-01.csv")
        df2 = pd.read_csv("./Data/Storage/BTCUSDTSWAP_candle1m/BTC-USDT-SWAP-candle1m-2021-10-02.csv")
        
        # Clean and prepare candle data
        df1 = df1.drop(['volume_ccy','volCcyQuote','timestamp'], axis=1)
        df1.rename(columns={"timestamp_1m": 'time'}, inplace=True)
        df1['time'] = pd.to_datetime(df1['time'])
        # Ensure timezone-naive
        if df1['time'].dt.tz is not None:
            df1['time'] = df1['time'].dt.tz_localize(None)
        
        df2 = df2.drop(['volume_ccy','volCcyQuote','timestamp'], axis=1)
        df2.rename(columns={"timestamp_1m": 'time'}, inplace=True)
        df2['time'] = pd.to_datetime(df2['time'])
        # Ensure timezone-naive
        if df2['time'].dt.tz is not None:
            df2['time'] = df2['time'].dt.tz_localize(None)
        
        # Combine both dataframes to get all trades
        df_all = pd.concat([df1, df2], ignore_index=True)
        
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
        chart.show()
        
        # Live update with df2 data (optional - you can comment this out to just see static chart)
        print("Starting live updates with df2 data...")
        fills_df2 = fills[fills['time'] > df1_max_time]
        
        for i, series in df2.iterrows():
            if not chart.is_alive:
                break
            
            chart.update(series)
            
            # Check if there's a trade at this time
            current_time = series['time']
            trades_at_time = fills_df2[fills_df2['time'] == current_time]
            
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
            
    except KeyboardInterrupt:
        print('\nInterrupt received, closing chart...')
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Ensure proper cleanup
        if 'chart' in locals():
            try:
                chart.exit()
            except Exception as e:
                print(f"Error during cleanup: {e}")
        print("Chart closed.")
