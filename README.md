[![Author](https://img.shields.io/badge/author-%40Tajouri213-blue.svg)](https://github.com/Tajouri213)
[![Gmail](https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:medaminetajouri@gmail.com)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/med-amine-tajouri/)

# Incident Webhook Uptime Receiver

## Overview
This is a Flask-based webhook receiver that integrates with GitLab and Microsoft Graph API to create and manage incidents based on [UptimeRobot](https://uptimerobot.com/) alerts.

## Features
- Receives webhook alerts from UptimeRobot.
- Creates incidents in GitLab with relevant details.
- Assigns incidents to responsible users based on Microsoft Teams shifts.
- Closes incidents when services are restored.

## Requirements
- Python 3.8+
- Flask
- Requests

## Installation

### 1. Clone the repository:
```sh
git clone https://github.com/Tajouri213/incident-uptimeRobot.git
cd incident-uptimeRobot
```

### 2. Set up a virtual environment:
```sh
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### 3. Install dependencies:
```sh
pip install -r requirements.txt
```

### 4. Set up environment variables:
Create a `.env` file with the following:
```ini
GITLAB_URL=<your_gitlab_url>
API_TOKEN=<your_gitlab_api_token>
PROJECT_ID=<your_gitlab_project_id>

CLIENT_ID=<your_azure_client_id> # portal.azure.com / Home > App registrations > app-overview
CLIENT_SECRET=<your_azure_client_secret> # portal.azure.com / Home > App registrations > app-Certificates & secrets
TENANT_ID=<your_azure_tenant_id> # portal.azure.com / Home > App registrations > app-overview
TEAM_ID=<your_azure_team_id> # portal.azure.com / Home > Groups > IT team-overview
MS-APP-ACTS-AS=<your_azure_app_acts_as> # portal.azure.com / Home > Users > user-overview
```

## Running the Application

### Locally:
```sh
python create_incident.py
```
The application will start on port `5000`.

You can expose your port for outside and to generate a `https` url using `ngrok`.
```sh
ngrok http 5000
```

### Using docker-compose:
```sh
docker-compose up -d
```

## API Endpoints

### Webhook Receiver
#### `GET /webhook`
Receives webhook alerts from UptimeRobot.
- **Down Alert** → Creates an incident in GitLab.
- **Up Alert** → Closes the related incident.

**Query Parameters:**
| Parameter       | Type   | Description |
|---------------|------|-------------|
| `monitorID`   | int  | ID of the monitor from UptimeRobot |
| `alertTypeFriendlyName` | string | "Down" or "Up" alert type |

## Deployment

This app can be deployed using `traefik` with the following labels:
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.incident-webhook.rule=Host(`exemple.com`)"
  - "traefik.http.routers.incident-webhook.entrypoints=websecure"
```

## Logging
Logs are stored in `flask_app.log` and can be accessed from the container:
```sh
docker logs incident-webhook
```

## Security Considerations
- Ensure `.env` file is not committed to the repository.
- API tokens should be securely stored and rotated periodically.
