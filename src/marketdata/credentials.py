import os
from typing import Optional

def get_api_key() -> Optional[str]:
    """Get API key from environment variable or raise helpful error."""
    api_key = os.environ.get('MARKET_DATA_API_KEY')
    if not api_key:
        raise ValueError(
            "MARKET_DATA_API_KEY environment variable not set. "
            "Please set it with your API key from marketdata.app"
        )
    return api_key

MARKET_DATA_API_KEY = get_api_key()