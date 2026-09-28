import logging
from datetime import datetime, timedelta
from typing import List, Dict

logger = logging.getLogger(__name__)

class NewsFilter:
    """
    Filters trading activity around high-impact news events.
    """
    def __init__(self, pause_before_mins: int = 30, pause_after_mins: int = 30):
        self.pause_before = timedelta(minutes=pause_before_mins)
        self.pause_after = timedelta(minutes=pause_after_mins)
        self.news_events: List[Dict] = []
        self.logger = logging.getLogger(__name__)

    def load_events(self, events: List[Dict]):
        """
        Load a list of news events.
        Format: [{'time': datetime, 'currency': 'USD', 'impact': 'HIGH'}]
        """
        self.news_events = events
        self.logger.info(f"Loaded {len(self.news_events)} news events")

    def is_trading_allowed(self, symbol: str, current_time: datetime) -> bool:
        """
        Check if trading is allowed for a symbol at the given time.
        """
        # Determine currencies in the symbol (e.g., 'EURUSD' -> 'EUR', 'USD')
        # We slice precisely to 3 and 3:6 to avoid matching 'USD.pro' or suffix issues
        currencies = [symbol[:3], symbol[3:6]]

        for event in self.news_events:
            # Check if event affects the symbol's currencies and is high impact
            if event['currency'] in currencies and event.get('impact', 'HIGH') == 'HIGH':
                news_time = event['time']

                # Check if current time is within the restricted window
                if (news_time - self.pause_before) <= current_time <= (news_time + self.pause_after):
                    self.logger.info(f"Trading paused for {symbol} due to news event at {news_time}")
                    return False

        return True
