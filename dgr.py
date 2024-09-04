import time
import requests
from flask import Flask, jsonify, render_template_string
import threading
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
CODESPACE_NAME = os.getenv('CODESPACE_NAME')
OWNER = os.getenv('OWNER')
REPO = os.getenv('REPO')

headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github+json'
}

app = Flask(__name__)

script_running = False

def get_codespace_status():
    url = f'https://api.github.com/user/codespaces/{CODESPACE_NAME}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f'Codespace Status Response: {data}')  # Debugging output
        return data.get('state')
    elif response.status_code == 404:
        print('Codespace not found.')
        return None
    else:
        print(f'Error fetching codespace status: {response.status_code} - {response.text}')
        return None

def start_codespace():
    url = f'https://api.github.com/user/codespaces/{CODESPACE_NAME}/start'
    response = requests.post(url, headers=headers)
    if response.status_code == 202:
        print('Codespace starting...')
    elif response.status_code == 409:
        print('Codespace is already starting or running.')
    else:
        print(f'Error starting codespace: {response.status_code} - {response.text}')

@app.route('/alive', methods=['GET'])
def alive():
    return jsonify({"status": "I'm alive"}), 200

@app.route('/')
def home():
    global script_running
    status = "I'm alive" if script_running else "I'm not running"
    html_content = f"""
    <html>
        <head>
            <title>Script Status</title>
        </head>
        <body>
            <h1>{status}</h1>
        </body>
    </html>
    """
    return render_template_string(html_content)

def monitor_codespace():
    global script_running

    while True:
        status = get_codespace_status()
        if status == 'Available':
            print('Codespace is already running.')
            script_running = True
        elif status in ['Stopped', 'Shutdown']:
            print('Codespace is not running. Starting...')
            start_codespace()
            script_running = False
        elif status is None:
            print('Unable to determine codespace status.')
            script_running = False
        else:
            print(f'Unhandled codespace status: {status}')
            script_running = False

        # Wait for 2 seconds before checking again
        time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=monitor_codespace).start()
    app.run(host='0.0.0.0', port=10000)  # Render exposes on port 10000
