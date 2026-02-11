
import schedule
import time
import logging
import subprocess
import sys
import os

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Scheduler")

def job_retrain():
    logger.info("⏰ Triggering Weekly Retraining...")
    subprocess.run([sys.executable, "src/pipeline.py", "--symbol", "BTC-USD", "--model", "lstm"])

def job_critic():
    logger.info("🕵️ Triggering Daily Critic Analysis...")
    subprocess.run([sys.executable, "src/agent_critic.py"])

def run_scheduler():
    logger.info("⏳ Scheduler Started. Running jobs...")
    
    # Schedule Retraining every Sunday at 00:00
    schedule.every().sunday.at("00:00").do(job_retrain)
    
    # Schedule Critic every day at 23:55
    schedule.every().day.at("23:55").do(job_critic)
    
    # Run once immediately for demonstration if requested
    # job_retrain() 
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    try:
        run_scheduler()
    except KeyboardInterrupt:
        logger.info("🛑 Scheduler Stopped.")
