
import logging
import pandas as pd
import json
import os

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CriticAgent")

class CriticAgent:
    """
    Simulates an AI Critic that analyzes the trade log and provides feedback.
    In a real system, this would call an LLM (GPT-4/Claude) with the log content.
    """
    def __init__(self, log_path="data/trade_log.csv"):
        self.log_path = log_path

    def analyze(self):
        logger.info("🧠 Critic Agent is thinking...")
        
        if not os.path.exists(self.log_path):
            logger.warning("No trade log found to analyze.")
            return

        try:
            df = pd.read_csv(self.log_path)
            if df.empty:
                logger.warning("Trade log is empty.")
                return

            # Simple Rule-Based "Criticism"
            total_trades = len(df)
            wins = df[df['pnl'] > 0]
            losses = df[df['pnl'] <= 0]
            win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
            avg_pnl = df['pnl'].mean()

            report = {
                "summary": f"Analyzed {total_trades} trades. Win Rate: {win_rate:.1f}%. Avg PnL: {avg_pnl:.2f}%.",
                "strengths": [],
                "weaknesses": [],
                "recommendation": ""
            }

            if win_rate > 50:
                report["strengths"].append("Good win rate (>50%). Strategy is working.")
            else:
                report["weaknesses"].append("Win rate is low. Consider tightening stop-loss or increasing entry threshold.")

            if avg_pnl < 0:
                report["recommendation"] = "Strategy is losing money. Recommendation: PAUSE trading and Retrain model IMMEDIATELY."
            else:
                report["recommendation"] = "Strategy is profitable. Recommendation: CONTINUE but monitor volatility."

            # Save Analysis
            with open("data/critic_report.json", "w") as f:
                json.dump(report, f, indent=4)
                
            logger.info("📝 Critic Report Generated:\n" + json.dumps(report, indent=2))
            
        except Exception as e:
            logger.error(f"Critic analysis failed: {e}")

if __name__ == "__main__":
    critic = CriticAgent()
    critic.analyze()
