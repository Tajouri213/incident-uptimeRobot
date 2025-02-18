from flask import Flask, request, jsonify
import requests
import time
import logging
import os
from get_username import get_username

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set log level to DEBUG to capture all logs
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("flask_app.log"),  # Log to a file
        logging.StreamHandler()  # Also log to console
    ]
)

# GitLab service configuration
GITLAB_URL = os.getenv("GITLAB_URL")
API_TOKEN = os.getenv("API_TOKEN")
PROJECT_ID = os.getenv("PROJECT_ID")


# In-memory storage for incident mapping (monitor_id -> issue_iid)
incident_map = {}

# Function to get the assignee ID from GitLab
def get_assignee_id(username):
    url = f"{GITLAB_URL}/api/v4/users"
    headers = {
        "Private-Token": API_TOKEN
    }
    params = {
        "username": username
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        users = response.json()
        if users:
            return users[0]["id"]  # Return the ID of the first matching user
        else:
            logging.error(f"No user found with username: {username}")
            return None
    except Exception as e:
        logging.error(f"Error fetching assignee ID: {e}")
        return None

# Function to create an incident in GitLab
def create_incident(alert_data):
    # Fetch the username dynamically for each incident
    username = get_username()
    gitlab_user_id = get_assignee_id(username)

    if not gitlab_user_id:
        logging.error("Failed to fetch assignee ID. Incident will not be assigned.")
        return {"error": "Failed to fetch assignee ID"}

    url = f"{GITLAB_URL}/api/v4/projects/{PROJECT_ID}/issues"
    headers = {
        "Private-Token": API_TOKEN
    }
    payload = {
        "title": f"Incident: {alert_data['alert_name']}",
        "description": (
            f"UptimeRobot reported an alert:\n\n"
            f"- **Status**: {alert_data['status']}\n"
            f"- **Monitor**: {alert_data['monitor_name']}\n"
            f"- **URL**: {alert_data['monitor_url']}\n"
            f"- **Time**: {alert_data['time']}\n"
            f"- **Alert Details**: {alert_data.get('details', 'N/A')}\n"
        ),
        "labels": "incident,prio:urgent,uptime",
        "issue_type": "incident",  # Set issue_type to 'incident'
        "assignee_id": gitlab_user_id  # Assign the incident to the user
    }

    # Log the payload being sent
    logging.info("Sending request to GitLab API: %s", payload)

    try:
        response = requests.post(url, headers=headers, json=payload)

        # Log the response details
        logging.info("Response status code: %d", response.status_code)
        logging.info("Response body: %s", response.text)

        if response.status_code == 201:
            issue = response.json()
            issue_iid = issue["iid"]
            logging.info("Incident created successfully with ID: %d", issue_iid)

            # Add a comment to the issue mentioning the assignee
            comment_url = f"{GITLAB_URL}/api/v4/projects/{PROJECT_ID}/issues/{issue_iid}/notes"
            comment_payload = {
                "body": f"Hey @{username}, Please fetch logs from the server, investigate the root cause, and update your timeline accordingly. Let us know your findings."
            }
            comment_response = requests.post(comment_url, headers=headers, json=comment_payload)

            if comment_response.status_code == 201:
                logging.info("Comment added successfully!")
            else:
                logging.error("Failed to add comment: %s", comment_response.text)

            return issue
        else:
            return {"error": "Failed to create incident", "details": response.json()}
    except Exception as e:
        logging.error("Error during GitLab API request: %s", str(e))
        return {"error": "Failed to create incident"}

# Function to close a GitLab issue
def close_incident(issue_iid):
    url = f"{GITLAB_URL}/api/v4/projects/{PROJECT_ID}/issues/{issue_iid}"
    headers = {
        "Private-Token": API_TOKEN
    }
    payload = {
        "state_event": "close",  # Close the issue
        "labels": "resolved"
    }

    try:
        response = requests.put(url, headers=headers, json=payload)
        response.raise_for_status()
        logging.info(f"Issue {issue_iid} closed successfully.")
        return True
    except Exception as e:
        logging.error(f"Error closing issue {issue_iid}: {e}")
        return False

# Flask app
app = Flask(__name__)

@app.route('/webhook', methods=['GET'])
def webhook():
    try:
        # Parse incoming query parameters
        data = request.args.to_dict()

        # Log the incoming data for debugging
        logging.info("Received webhook data: %s", data)

        # Extract monitor_id and alert type
        monitor_id = data.get("monitorID")
        alert_type = data.get("alertTypeFriendlyName")

        if not monitor_id:
            logging.error("Monitor ID not found in webhook data.")
            return jsonify({"error": "Monitor ID not found"}), 400

        # Handle "Down" alerts
        if alert_type == "Down":
            # Transform webhook data to match create_incident requirements
            alert_data = {
                "alert_name": data.get("monitorFriendlyName", "Unknown Alert"),
                "status": "Down",
                "monitor_name": data.get("monitorFriendlyName", "Unknown Monitor"),
                "monitor_url": data.get("monitorURL", "Unknown URL"),
                "time": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime(int(data.get("alertDateTime", time.time())))
                ),
                "details": data.get("alertDetails", "N/A"),
                "contacts": data.get("monitorAlertContacts", "N/A"),
            }

            # Create a GitLab issue
            incident_response = create_incident(alert_data)
            if "iid" in incident_response:
                # Save the monitor_id and issue_iid mapping
                incident_map[monitor_id] = incident_response["iid"]
                logging.info(f"Incident created for monitor {monitor_id}. Issue IID: {incident_response['iid']}")
                return jsonify({
                    "message": "Incident created successfully!",
                    "incident_response": incident_response
                }), 200
            else:
                logging.error("Failed to create incident.")
                return jsonify({"error": "Failed to create incident"}), 500

        # Handle "Up" alerts
        elif alert_type == "Up":
            if monitor_id in incident_map:
                issue_iid = incident_map[monitor_id]
                # Close the issue
                if close_incident(issue_iid):
                    # Remove the monitor_id from the incident map
                    del incident_map[monitor_id]
                    logging.info(f"Issue {issue_iid} closed for monitor {monitor_id}.")
                    return jsonify({"message": f"Issue {issue_iid} closed successfully."}), 200
                else:
                    logging.error(f"Failed to close issue {issue_iid} for monitor {monitor_id}.")
                    return jsonify({"error": f"Failed to close issue {issue_iid}"}), 500
            else:
                logging.info(f"No open issue found for monitor {monitor_id}.")
                return jsonify({"message": "No open issue found."}), 200

        else:
            logging.info("Alert type is neither 'Down' nor 'Up'. Ignoring webhook.")
            return jsonify({"message": "Alert type not recognized."}), 200

    except Exception as e:
        logging.error("Error processing webhook: %s", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)