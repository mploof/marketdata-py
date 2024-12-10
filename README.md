# MarketData API Client

This Python module provides a client for interacting with the [marketdata.app](https://marketdata.app) API. It offers both synchronous and asynchronous methods to fetch various financial data, including stock candles, options chains, and options quotes.

## Features

- Synchronous and asynchronous API clients
- Caching mechanism for efficient data retrieval
- Parallel processing for bulk data requests
- Support for various API endpoints:
  - Stock candles
  - Options chains
  - Options quotes
  - Index candles and quotes
  - Market status
  - Earnings data
  - Stock news

## Configuration

Create a file named `marketdata_api.key` in the `credentials` directory and add your MarketData API key to it.

## Usage

### Basic Usage

```python
from marketdata.manager import MarketDataManager
from datetime import date

mdm = MarketDataManager()

# Fetch stock candles
candles = mdm.get_stock_candles(["AAPL", "GOOGL"], "1D", from_date=date(2023, 1, 1), to_date=date(2023, 6, 1))

# Print the results
for symbol, df in candles.items():
    print(f"Candles for {symbol}:")
    print(df.head())
    print("\n")
```

### Fetching Options Data

```python
from marketdata.client_params import OptionsChainParams, OptionsQuoteParams

# Fetch options chains
chain_params = [
    OptionsChainParams(underlying="AAPL"),
    OptionsChainParams(underlying="GOOGL")
]
chains = mdm.get_options_chains(chain_params)

# Fetch options quotes
quote_params = [
    OptionsQuoteParams(option_symbol="AAPL230616C00150000"),
    OptionsQuoteParams(option_symbol="GOOGL230616P02000000")
]
quotes = mdm.get_options_quotes(quote_params)
```

### Using BasicParams and FromToParams

The `BasicParams` and `FromToParams` classes are used to provide common parameters for API requests:

```python
from marketdata.client_params import BasicParams, FromToParams
from datetime import date

# Basic parameters
basic_params = BasicParams(
    lookup_date=date(2023, 6, 1),
    dateformat="timestamp",
    limit=1000
)

# Date range parameters
from_to_params = FromToParams(
    from_date=date(2023, 1, 1),
    to_date=date(2023, 6, 1)
)

# Use these params in API calls
candles = mdm.get_stock_candles(
    ["AAPL"],
    "1D",
    basic_params=basic_params,
    from_to_params=from_to_params
)
```

`BasicParams` includes common options like date format and result limits, while `FromToParams` specifies date ranges for historical data queries.

### Caching

The module implements caching to reduce API calls and improve performance. Cached data is stored in the `./data/cache` directory.
