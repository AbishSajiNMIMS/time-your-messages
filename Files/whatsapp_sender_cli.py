#!/usr/bin/env python3
"""
WhatsApp message scheduler CLI and web interface
"""

import argparse
import json
import sys
from datetime import datetime
import threading
import time
import webbrowser
import os
import logging
from pathlib import Path
from bs4 import BeautifulSoup

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

try:
    from flask import Flask, render_template, request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global scheduler
scheduler = BackgroundScheduler()




def create_sample_config():
    """Create a sample contacts.json file"""
    sample = {
        "messages": [
            {
                "sender": "+1234567890",
                "recipient": "+9876543210",
                "message": "Hello! This is a test message.",
                "send_at": "2024-03-01 15:30:00"
            }
        ]
    }
    
    with open("contacts.json", "w") as f:
        json.dump(sample, f, indent=2)
    
    logger.info("Created sample contacts.json")


def send_message_via_whatsapp(sender: str, recipient: str, message: str):
    """Send a message via WhatsApp Web with robust error handling"""
    driver = None
    try:
        logger.info(f"🚀 Starting to send message from {sender} to {recipient}...")
        
        # Get chrome profile if set
        chrome_profile = os.getenv("WA_CHROME_PROFILE")
        
        options = uc.ChromeOptions()
        if chrome_profile:
            options.user_data_dir = chrome_profile
            logger.info(f"Using Chrome profile: {chrome_profile}")
        else:
            logger.info("Using default Chrome profile")
        
        # determine chrome binary location
        chrome_bin = os.getenv('WA_CHROME_PATH') or os.getenv('CHROME_PATH')
        if not chrome_bin:
            for path in [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]:
                if os.path.exists(path):
                    chrome_bin = path
                    break
        if chrome_bin:
            options.binary_location = chrome_bin
            logger.info(f"Using Chrome binary at: {chrome_bin}")
        else:
            logger.warning("No Chrome binary location found; driver may fail")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Open browser
        logger.info("🔓 Opening Chrome browser...")
        driver = uc.Chrome(options=options, version_main=None)
        
        # Remove the + from phone number for WhatsApp URL
        phone = recipient.replace('+', '')
        chat_url = f"https://web.whatsapp.com/send?phone={phone}"
        
        logger.info(f"📍 Navigating to: {chat_url}")
        driver.get(chat_url)
        
        # take initial screenshot
        try:
            os.makedirs('screenshots', exist_ok=True)
            path = os.path.join('screenshots', f'before_{recipient.replace("+","")}_{int(time.time())}.png')
            driver.save_screenshot(path)
            logger.info(f"🖼 Saved initial screenshot: {path}")
        except Exception as e:
            logger.warning(f"Could not save initial screenshot: {e}")
        
        # Wait for the page to fully load
        logger.info("⏳ Waiting for page to load (15 seconds)...")
        time.sleep(8)
        
        # Check if we're logged in by looking for message box
        logger.info("🔍 Looking for message input field...")
        
        # Try multiple methods to find and interact with message box
        message_sent = False
        
        # Method 1: Using the data-tab attribute
        try:
            logger.info("  - Trying Method 1: div[contenteditable] with data-tab...")
            message_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='10']"))
            )
            logger.info("  ✓ Found message input field!")
            
            # Scroll into view
            driver.execute_script("arguments[0].scrollIntoView(true);", message_box)
            time.sleep(1)
            
            # Click the message box
            message_box.click()
            logger.info("  ✓ Clicked on message box")
            time.sleep(1)
            
            # Type the message character by character
            logger.info(f"  ✓ Typing message: {message}")
            for char in message:
                message_box.send_keys(char)
                time.sleep(0.05)  # Small delay between characters
            
            time.sleep(0.5)
            logger.info("  ✓ Message typed successfully")
            
            # Try to find and click send button
            logger.info("  - Looking for send button...")
            try:
                # Multiple XPath options for send button
                send_button = None
                send_button_xpaths = [
                    "//button[@aria-label='Send']",
                    "//button[contains(@aria-label, 'Send')]",
                    "//div[@data-tab='10']//button[last()]",
                    "//button[@type='button'][contains(@class, 'send')]",
                ]
                
                for xpath in send_button_xpaths:
                    try:
                        send_button = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, xpath))
                        )
                        logger.info(f"  ✓ Found send button using: {xpath}")
                        break
                    except:
                        continue
                
                if send_button:
                    logger.info("  ✓ Clicking send button...")
                    send_button.click()
                    logger.info("  ✓ Send button clicked!")
                    message_sent = True
                    time.sleep(2)
                else:
                    logger.warning("  ⚠ Send button not found, trying Ctrl+Enter...")
                    message_box.send_keys("\ue007")  # Enter key
                    time.sleep(2)
                    message_sent = True
                    
            except Exception as e:
                logger.warning(f"  ⚠ Send button click failed: {e}")
                logger.info("  - Trying Enter key as fallback...")
                message_box.send_keys("\ue007")  # Enter key
                time.sleep(2)
                message_sent = True
                
        except Exception as e:
            logger.warning(f"  ✗ Method 1 failed: {e}")
            logger.info("  - Trying Method 2: Generic contenteditable div...")
            
            try:
                # Method 2: More generic approach
                message_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
                )
                logger.info("  ✓ Found contenteditable element!")
                
                driver.execute_script("arguments[0].scrollIntoView(true);", message_box)
                time.sleep(1)
                message_box.click()
                time.sleep(1)
                
                logger.info(f"  ✓ Typing message: {message}")
                for char in message:
                    message_box.send_keys(char)
                    time.sleep(0.05)
                
                time.sleep(0.5)
                
                logger.info("  ✓ Pressing Enter to send...")
                message_box.send_keys("\ue007")  # Enter
                time.sleep(2)
                message_sent = True
                
            except Exception as e2:
                logger.error(f"  ✗ Method 2 also failed: {e2}")
        
        if message_sent:
            logger.info(f"✅ MESSAGE SENT successfully from {sender} to {recipient}!")
            # capture screenshot after send
            try:
                path2 = os.path.join('screenshots', f'after_{recipient.replace("+","")}_{int(time.time())}.png')
                driver.save_screenshot(path2)
                logger.info(f"🖼 Saved after-send screenshot: {path2}")
            except Exception as ee:
                logger.warning(f"Could not save after-send screenshot: {ee}")
        else:
            logger.error(f"❌ Failed to send message - both methods failed")
            try:
                path2 = os.path.join('screenshots', f'failed_{recipient.replace("+","")}_{int(time.time())}.png')
                driver.save_screenshot(path2)
                logger.info(f"🖼 Saved failure screenshot: {path2}")
            except Exception as ee2:
                logger.warning(f"Could not save failure screenshot: {ee2}")
        
    except Exception as e:
        logger.error(f"❌ Critical error sending message: {e}", exc_info=True)
    finally:
        # Close the browser
        if driver:
            try:
                logger.info("🔒 Closing browser...")
                time.sleep(1)
                driver.quit()
                logger.info("✓ Browser closed")
            except:
                pass


def schedule_message(sender: str, recipient: str, message: str, send_at: str):
    """Schedule a message to be sent at a specific time"""
    try:
        # Parse the datetime
        send_time = datetime.strptime(send_at, "%Y-%m-%d %H:%M:%S")
        
        # Check if the time is in the past
        if send_time < datetime.now():
            logger.warning(f"⚠️ Scheduled time {send_time} is in the past! Sending immediately...")
            send_message_via_whatsapp(sender, recipient, message)
            return
        
        def send_job():
            logger.info(f"📤 Executing scheduled message to {recipient}")
            send_message_via_whatsapp(sender, recipient, message)
        
        # Schedule using APScheduler
        job = scheduler.add_job(
            send_job,
            trigger=DateTrigger(run_date=send_time),
            id=f"msg_{int(time.time())}_{recipient}",
            replace_existing=False
        )
        
        logger.info(f"✅ Message scheduled for {send_time} to {recipient} [Job ID: {job.id}]")
        
    except ValueError as e:
        logger.error(f"Invalid datetime format: {send_at}. Expected format: YYYY-MM-DD HH:MM:SS")
    except Exception as e:
        logger.error(f"Error scheduling message: {e}", exc_info=True)


def parse_html_form(html_file: str) -> dict:
    """Parse HTML form for message details"""
    with open(html_file, 'r') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    data = {
        "messages": []
    }
    
    # Find form inputs
    sender_input = soup.find('input', {'name': 'sender'})
    recipient_input = soup.find('input', {'name': 'recipient'})
    message_input = soup.find('textarea', {'name': 'message'})
    datetime_input = soup.find('input', {'type': 'datetime-local'})
    
    if all([sender_input, recipient_input, message_input, datetime_input]):
        # Convert datetime-local format to standard format
        datetime_str = datetime_input.get('value', '')
        if datetime_str:
            datetime_str = datetime_str.replace('T', ' ')
        
        data["messages"].append({
            "sender": sender_input.get('value', ''),
            "recipient": recipient_input.get('value', ''),
            "message": message_input.get_text() if message_input else '',
            "send_at": datetime_str
        })
    
    return data


def process_contacts(file_path: str):
    """Process contacts from JSON or HTML file"""
    if file_path.endswith('.json'):
        with open(file_path, 'r') as f:
            data = json.load(f)
    elif file_path.endswith('.html'):
        data = parse_html_form(file_path)
    else:
        logger.error(f"Unsupported file format: {file_path}")
        return
    
    # Schedule each message
    for msg in data.get("messages", []):
        schedule_message(
            msg.get("sender", ""),
            msg.get("recipient", ""),
            msg.get("message", ""),
            msg.get("send_at", "")
        )


def create_flask_app():
    """Create Flask application"""
    app = Flask(__name__, template_folder='.')
    
    # Start scheduler if not already running
    if not scheduler.running:
        scheduler.start()
        logger.info("Background scheduler started")
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/schedule', methods=['POST'])
    def schedule_from_web():
        """Handle message scheduling from web form"""
        try:
            data = request.json
            
            sender = data.get('sender', '')
            sender_country = data.get('sender_country', '')
            recipient_country = data.get('recipient_country', '')
            recipient = data.get('recipient', '')
            message = data.get('message', '')
            send_at = data.get('send_at', '')
            
            # Validate inputs
            if not all([sender, sender_country, recipient, recipient_country, message, send_at]):
                return jsonify({"status": "error", "message": "All fields are required"}), 400
            
            # Format phone numbers with country codes
            sender = f"+{sender_country}{sender}"
            recipient = f"+{recipient_country}{recipient}"
            
            # Convert datetime format
            send_at = send_at.replace('T', ' ')
            
            logger.info(f"Received schedule request: From {sender} to {recipient} at {send_at}")
            
            schedule_message(sender, recipient, message, send_at)
            
            return jsonify({
                "status": "success",
                "message": f"Message scheduled for {send_at}",
                "details": f"From: {sender}, To: {recipient}"
            })
        except Exception as e:
            logger.error(f"Error in schedule_from_web: {e}", exc_info=True)
            return jsonify({"status": "error", "message": str(e)}), 400
    
    @app.route('/status', methods=['GET'])
    def status():
        """Get scheduler status and pending jobs"""
        try:
            jobs = []
            for job in scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "next_run_time": str(job.next_run_time),
                    "trigger": str(job.trigger)
                })
            
            return jsonify({
                "scheduler_running": scheduler.running,
                "pending_jobs": len(jobs),
                "jobs": jobs
            })
        except Exception as e:
            logger.error(f"Error in status: {e}")
            return jsonify({"error": str(e)}), 400
    
    return app


def main():
    parser = argparse.ArgumentParser(description="WhatsApp Message Scheduler")
    parser.add_argument('file', nargs='?', help='JSON or HTML file with contacts')
    parser.add_argument('--create-sample', action='store_true', help='Create sample contacts.json')
    parser.add_argument('--serve', action='store_true', help='Run Flask web server')
    
    args = parser.parse_args()
    
    if args.create_sample:
        create_sample_config()
    elif args.serve:
        if not FLASK_AVAILABLE:
            logger.error("Flask is not installed. Install it with: pip install flask")
            sys.exit(1)
        
        app = create_flask_app()
        
        # Open browser automatically
        def open_browser():
            time.sleep(2)
            webbrowser.open('http://localhost:5000')
        
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        logger.info("=" * 60)
        logger.info("Starting WhatsApp Message Scheduler")
        logger.info("=" * 60)
        logger.info("📱 Web Server starting at http://localhost:5000")
        logger.info("⏰ Keep this window open for messages to be sent")
        logger.info("=" * 60)
        
        try:
            app.run(debug=False, port=5000, use_reloader=False)
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            if scheduler.running:
                scheduler.shutdown()
    elif args.file:
        # Start scheduler in background
        if not scheduler.running:
            scheduler.start()
        
        process_contacts(args.file)
        
        logger.info("=" * 60)
        logger.info("Scheduler running... Press Ctrl+C to exit")
        logger.info("=" * 60)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
