import requests
import os
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace these with your Azure AD app credentials
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")  # App ID from Azure
MS_APP_ACTS_AS = os.getenv("MS_APP_ACTS_AS")
TEAM_ID = os.getenv("TEAM_ID")  # Team Id for shift
SHIFTS_ENDPOINT = f'https://graph.microsoft.com/v1.0/teams/{TEAM_ID}/schedule/shifts'
GRAPH_API_URL = 'https://graph.microsoft.com/v1.0/users/{user_id}'

# Get an access token for Microsoft Graph API
def get_access_token():
    url = f'https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': 'https://graph.microsoft.com/.default'
    }
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json().get('access_token')
    except requests.exceptions.HTTPError as err:
        logger.error(f"Error getting access token: {err}")
        return None

# Fetch user ID from shifts endpoint
def get_user_id():
    access_token = get_access_token()
    if not access_token:
        return None

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = today + timedelta(days=2)  # 2 days later
    query = f"sharedShift/startDateTime ge {today.isoformat()}Z and sharedShift/endDateTime le {end_date.isoformat()}Z"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'MS-APP-ACTS-AS': MS_APP_ACTS_AS
    }
    params = {
        '$filter': query
    }
    try:
        response = requests.get(SHIFTS_ENDPOINT, headers=headers, params=params)
        response.raise_for_status()
        shifts_data = response.json()
        if shifts_data.get('value'):
            return shifts_data['value'][0]['userId']
        else:
            logger.warning("No shifts found.")
            return None
    except requests.exceptions.HTTPError as err:
        logger.error(f"Error fetching user ID: {err}")
        return None

# Get user details from Microsoft Graph API
def get_user_email(user_id):
    access_token = get_access_token()
    if not access_token:
        return None

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    try:
        response = requests.get(GRAPH_API_URL.format(user_id=user_id), headers=headers)
        response.raise_for_status()
        user_data = response.json()
        return user_data.get('mail')  # or 'userPrincipalName' if mail is not available
    except requests.exceptions.HTTPError as err:
        logger.error(f"Error fetching user email: {err}")
        return None

# Main function
def get_username():
    try:
        user_id = get_user_id()
        if not user_id:
            logger.error("No user ID found.")
            return None

        email = get_user_email(user_id)
        if not email:
            logger.error("No email found for the user.")
            return None

        username = email.split('@')[0]  # Extract the part before the '@'
        return username
    except Exception as err:
        logger.error(f"Unexpected error: {err}")
        return None

# Allow the script to be run independently
if __name__ == '__main__':
    username = get_username()
    if username:
        print(username)
    else:
        logger.error("Failed to retrieve username.")