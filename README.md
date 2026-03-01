# Time Your Messages

A simple project that lets you schedule WhatsApp messages from the command line or through a tiny local web page.

## Requirements
- Python 3.8+
- Windows (tested) but should work elsewhere
- Chrome/Chromium or Opera installed for browser automation

## Setup
```cmd
cd "d:\GitHub\Digital Ocean Projects\time-your-messages"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Browser configuration
Keep WhatsApp Web logged in and open; the script will schedule messages via your browser.

**Browser support:**
- Designed for Chrome/Chromium by default. A valid Chrome/Chromium binary must be available.
- Opera is also supported because it’s Chromium-based. If you use Opera, set one of these environment variables before running the script:
  ```cmd
  set WA_CHROME_PATH="C:\Path\To\Opera\launcher.exe"
  set CHROME_PATH="C:\Path\To\Opera\launcher.exe"
  ```
  (use `export` on Unix)

## Command-line Usage
- Create a sample configuration:
  ```cmd
  python Files\whatsapp_sender_cli.py --create-sample
  ```
- Send messages defined in JSON or HTML:
  ```cmd
  python Files\whatsapp_sender_cli.py contacts.json
  python Files\whatsapp_sender_cli.py login_page.html
  ```
  HTML pages are parsed for phone numbers, message text, and a `<input type="datetime-local">` value.

## Web Interface
Run a tiny Flask site, fill in fields, and hit submit:
```cmd
python Files\whatsapp_sender_cli.py --serve
```
The browser opens automatically to `http://localhost:5000`.

...
