"""
Timeseries daily from Yahoo Finance.
"""

from datetime import date, datetime
import time
import urllib

from datasets import load_dataset
import pandas as pd
import requests

from systematic_trading.datasets.raw import Raw


class TimeseriesDaily(Raw):
    """
    Timeseries daily from Yahoo Finance.
    """

    def __init__(self, suffix: str = None, tag_date: date = None, username: str = None):
        super().__init__(suffix, tag_date, username)
        self.name = f"timeseries-daily-{suffix}"
        self.expected_columns = [
            "symbol",
            "date",
            "open",
            "high",
            "low",
            "close",
            "adj_close",
            "volume",
        ]
        self.dataset_df = pd.DataFrame(columns=self.expected_columns)

    def __get_timeseries_daily_with_retry(self, ticker: str, retries=10, delay=300):
        from_timestamp = int(datetime.timestamp(datetime(1980, 1, 1)))
        to_timestamp = int(datetime.timestamp(datetime.now()))
        url = f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}?period1={from_timestamp}&period2={to_timestamp}&interval=1d&events=history&includeAdjustedClose=true"
        for _ in range(retries):
            try:
                df = pd.read_csv(url)
                df["Date"] = pd.to_datetime(df["Date"]).dt.date.apply(
                    lambda x: x.isoformat()
                )
                return df
            except urllib.error.HTTPError:
                print(f"Connection error with {url}. Retrying in {delay} seconds...")
                time.sleep(delay)
        raise ConnectionError(f"Failed to connect to {url} after {retries} retries")

    def append_frame(self, symbol: str):
        ticker = self.symbol_to_ticker(symbol)
        df = self.__get_timeseries_daily_with_retry(ticker)
        if df is None:
            self.frames[symbol] = None
            return
        df.rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "volume",
            },
            inplace=True,
        )
        df["symbol"] = symbol
        # use reindex() to set 'symbol' as the first column
        df = df.reindex(columns=["symbol"] + list(df.columns[:-1]))
        self.frames[symbol] = df

    def set_dataset_df(self):
        self.dataset_df = pd.concat([f for f in self.frames.values() if f is not None])
        self.dataset_df.sort_values(by=["symbol", "date"], inplace=True)
        self.dataset_df.reset_index(drop=True, inplace=True)
