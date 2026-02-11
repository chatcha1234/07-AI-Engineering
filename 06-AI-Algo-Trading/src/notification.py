import os
import logging
import requests

logger = logging.getLogger("NotificationService")

class NotificationService:
    def __init__(self):
        self.line_token = os.getenv("LINE_NOTIFY_TOKEN")
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        self.enabled = bool(self.line_token or (self.telegram_token and self.telegram_chat_id))
        if not self.enabled:
            logger.info("ℹ️ Notification tokens not found. Alerts will be logged only.")

    def send(self, message: str, level: str = "INFO"):
        """Send notification to all configured channels."""
        # Add emoji prefix based on level
        emojis = {
            "ERROR": "🔴",
            "SUCCESS": "🟢",
            "WARNING": "⚠️",
            "INFO": "ℹ️"
        }
        prefix = emojis.get(level, "ℹ️")
        formatted_message = f"{prefix} {message}"
        
        # Always log to system logger
        if level == "ERROR":
            logger.error(f"🔔 {message}")
        elif level == "WARNING":
            logger.warning(f"🔔 {message}")
        else:
            logger.info(f"🔔 {message}")
            
        if not self.enabled:
            return

        self._send_line(formatted_message)
        self._send_telegram(formatted_message)

    def _send_line(self, message: str):
        if not self.line_token:
            return
        try:
            url = "https://notify-api.line.me/api/notify"
            headers = {"Authorization": f"Bearer {self.line_token}"}
            data = {"message": message}
            requests.post(url, headers=headers, data=data, timeout=5)
        except Exception as e:
            logger.error(f"Failed to send LINE: {e}")

    def _send_telegram(self, message: str):
        if not self.telegram_token or not self.telegram_chat_id:
            return
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {"chat_id": self.telegram_chat_id, "text": message}
            requests.post(url, data=data, timeout=5)
        except Exception as e:
            logger.error(f"Failed to send Telegram: {e}")
