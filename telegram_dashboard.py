import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class TelegramDashboard:
    """
    Manages a live-updating dashboard in a Telegram chat.
    It sends an initial message and then updates (edits) it to avoid spamming the chat.
    """
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.message_id: Optional[int] = None
        self.logger = logging.getLogger(__name__)

    def _send_message(self, text: str) -> Optional[int]:
        """Send a new message and return its ID."""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                return response.json().get('result', {}).get('message_id')
            else:
                self.logger.error(f"Failed to send Telegram message: {response.text}")
        except Exception as e:
            self.logger.error(f"Telegram API error: {e}")
        return None

    def _edit_message(self, text: str) -> bool:
        """Edit an existing message."""
        if not self.message_id:
            return False

        url = f"{self.base_url}/editMessageText"
        payload = {
            "chat_id": self.chat_id,
            "message_id": self.message_id,
            "text": text,
            "parse_mode": "HTML"
        }
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                return True
            else:
                self.logger.error(f"Failed to edit Telegram message: {response.text}")
        except Exception as e:
            self.logger.error(f"Telegram API error: {e}")
        return False

    def update_dashboard(self, equity: float, expected_profit: float, risk_amount: float, num_trades: int, balance: float):
        """
        Updates the dashboard message with current stats.
        If the message doesn't exist yet, it sends a new one.
        """
        if not self.bot_token or not self.chat_id:
            return

        # Format the dashboard text
        text = (
            "📊 <b>Prop Firm Bot Dashboard</b> 📊\n"
            "-----------------------------------\n"
            f"💰 <b>Balance:</b> ${balance:.2f}\n"
            f"📈 <b>Live Equity:</b> ${equity:.2f}\n"
            f"🟢 <b>Expected PnL:</b> ${expected_profit:.2f}\n"
            f"🔴 <b>Risk Amount (If SL hit):</b> ${risk_amount:.2f}\n"
            f"📉 <b>Final Bal (If SL hit):</b> ${(balance - risk_amount):.2f}\n"
            f"📝 <b>Open Trades:</b> {num_trades}\n"
            "-----------------------------------\n"
            "<i>Live status updates automatically.</i>"
        )

        # If we already sent a message, try to edit it
        if self.message_id:
            success = self._edit_message(text)
            if not success:
                # If editing failed (e.g., message was deleted by user), send a new one
                self.message_id = self._send_message(text)
        else:
            # Send the initial dashboard message
            self.message_id = self._send_message(text)
