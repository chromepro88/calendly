import requests
from datetime import datetime, timedelta
from pytz import timezone
from flask import Flask, Response  # Add Flask for web server
import os

app = Flask(__name__)

# Replace with your new personal access token
token = os.environ.get("CALENDLY_TOKEN")  # Get token from environment
headers = {"Authorization": f"Bearer {token}"}

# Define SGT timezone
sgt = timezone('Asia/Singapore')

# Step 1: Get user UUID and verify token
def get_user_uuid():
    url = "https://api.calendly.com/users/me"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["resource"]["uri"]
    return None

# Step 2: Get the correct event type URI for "propupsg/new"
def get_event_type_uri(token, slug, user_uri):
    url = "https://api.calendly.com/event_types"
    params = {"user": user_uri}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200 or "collection" not in response.json():
        return None
    for event in response.json()["collection"]:
        if event["slug"] == slug and event["profile"]["owner"] == user_uri:
            return event["uri"]
    return None

# Step 3: Fetch and format available times
def get_available_times(event_type_uri, start_time, end_time):
    url = "https://api.calendly.com/event_type_available_times"
    params = {
        "event_type": event_type_uri,
        "start_time": start_time,
        "end_time": end_time
    }
    response = requests.get(url, headers=headers, params=params)
    if "collection" not in response.json():
        return []
    available_times = [
        datetime.strptime(slot["start_time"], "%Y-%m-%dT%H:%M:%SZ")
        .replace(tzinfo=timezone('UTC'))
        .astimezone(sgt)
        .strftime("%B %d, %Y at %I:%M %p SGT")
        for slot in response.json()["collection"] if slot["status"] == "available"
    ]
    return available_times

# Web endpoint
@app.route('/get-dates')
def get_dates():
    user_uri = get_user_uuid()
    if not user_uri:
        return Response("Failed to fetch user info. Check token.", mimetype='text/plain', status=500)
    
    event_type_uri = get_event_type_uri(token, "new", user_uri)
    if not event_type_uri:
        return Response("Failed to retrieve event type URI.", mimetype='text/plain', status=500)
    
    # Set future date range in SGT (7 days starting tomorrow)
    now_sgt = datetime.now(sgt)
    start_sgt = (now_sgt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_sgt = (now_sgt + timedelta(days=14)).replace(hour=23, minute=59, second=59, microsecond=0)
    
    # Convert to UTC for API
    start_time = start_sgt.astimezone(timezone('UTC')).isoformat().replace("+00:00", "Z")
    end_time = end_sgt.astimezone(timezone('UTC')).isoformat().replace("+00:00", "Z")
    
    available_times = get_available_times(event_type_uri, start_time, end_time)
    if available_times:
        text_output = "\n".join(available_times)
        return Response(text_output, mimetype='text/plain')
    else:
        return Response("No available times found in the specified range.", mimetype='text/plain')

# Run the app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)