from flask import Flask, request, jsonify, redirect, session
from database import Database
from email.mime.text import MIMEText
from flask_cors import CORS
import csv
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import base64
import os
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from oauthlib.oauth2 import WebApplicationClient
import json
import requests

app = Flask(__name__)
CORS(app)

# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

db = Database()

# Google OAuth2 configuration
CLIENT_SECRETS_FILE = "google_credentials.json"
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
    "https://www.googleapis.com/auth/gmail.modify",
]
REDIRECT_URI = "https://mass-mailer.onrender.com/callback"

# Outlook OAuth2 Configuration
OUTLOOK_CLIENT_SECRETS_FILE = "outlook_credentials.json"
OUTLOOK_SCOPES = [
    "https://graph.microsoft.com/User.Read",
    "https://graph.microsoft.com/Mail.Send",
    "offline_access",
]
OUTLOOK_REDIRECT_URI = "https://mass-mailer.onrender.com/outlook_callback"

# Scheduler Setup (Using APScheduler for scheduling email sending)
scheduler = BackgroundScheduler()
scheduler.start()

# Add or Register the User
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    status = data.get("status")
    role = data.get("role")
    response, status_code = db.register_user(username, email, password, status, role)
    return jsonify(response), status_code

# Login User
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")
    status = data.get("status")
    result, status_code = db.verify_user(email, password, role, status)
    return jsonify(result), status_code

# Google OAuth Flow
@app.route("/verify_email")
def gmail_login():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES
    )
    flow.redirect_uri = REDIRECT_URI
    authorization_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true"
    )
    return redirect(authorization_url)

#Verify Outlook Email
@app.route("/verify_outlook")
def outlook_login():
    # Load client secrets
    with open(OUTLOOK_CLIENT_SECRETS_FILE, "r") as f:
        outlook_creds = json.load(f)

    client_id = outlook_creds["client_id"]
    auth_uri = outlook_creds["auth_uri"]

    # Prepare the authorization URL
    client = WebApplicationClient(client_id)
    authorization_url = client.prepare_request_uri(
        auth_uri,
        redirect_uri=OUTLOOK_REDIRECT_URI,
        scope=" ".join(OUTLOOK_SCOPES),
    )

    return redirect(authorization_url)

# Google OAuth Callback
@app.route("/callback")
def callback():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI
    
    # CSRF protection check
    if "oauth_state" in session and session["oauth_state"] != request.args["state"]:
        return "State mismatch error", 400

    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    service = build("oauth2", "v2", credentials=credentials)
    user_info = service.userinfo().get().execute()
    
    user_email = user_info["email"]

    # Store credentials in the database
    db.store_credentials_for_gmail(user_email, credentials, "enabled", 0)

    return redirect(f'http://localhost:8501/?page=send_mass_mail')

#Callback for Outlook
@app.route("/outlook_callback")
def outlook_callback():
    # Load client secrets
    with open(OUTLOOK_CLIENT_SECRETS_FILE, "r") as f:
        outlook_creds = json.load(f)

    client_id = outlook_creds["client_id"]
    client_secret = outlook_creds["client_secret"]
    token_uri = outlook_creds["token_uri"]
    
    # Validate state (optional, for CSRF protection)
    if "oauth_state" in session and session["oauth_state"] != request.args.get("state"):
        return "State mismatch error", 400
    
    # Exchange authorization code for tokens
    code = request.args.get("code")
    
    token_request_body = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": OUTLOOK_REDIRECT_URI,
    }
    
    token_response = requests.post(token_uri, data=token_request_body)
    token_response_data = token_response.json()

    if "access_token" not in token_response_data:
        return "Failed to obtain token", 400
    
    # Use the access token to get user info
    access_token = token_response_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    user_info_response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
    user_info = user_info_response.json()
    
    user_email = user_info.get("userPrincipalName", "Unknown")

    scopes = token_response_data.get("scope", "").split()
    
    # Store credentials in the database
    db.store_credentials_for_outlook(user_email, token_response_data['access_token'], token_response_data['refresh_token'], client_id, client_secret, scopes, "enabled", 0)

    return redirect(f"http://localhost:8501/?page=send_mass_mail")

# For Select Email Service
@app.route("/send_mass_mail", methods=["POST"])
def send_mass_mail():
    email_service = request.form.get("email_service")
    sender_email = request.form.get("sender_email")
    subject = request.form.get("subject")
    body = request.form.get("body")
    csv_file = request.files.get("csv_file")
    send_time = request.form.get("send_time")  # Add schedule time (optional)
    cc = request.form.get("cc", "")
    bcc = request.form.get("bcc", "")

    # Parse send_time (if provided)
    schedule_time = None
    if send_time:
        try:
            schedule_time = datetime.strptime(send_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return jsonify({"error": "Invalid date format. Please use 'YYYY-MM-DD HH:MM:SS'."}), 400

    recipients = []
    if csv_file:
        try:
            csv_file.seek(0)  # Reset file pointer to the beginning
            csv_reader = csv.reader(csv_file.read().decode("utf-8").splitlines())  # Decode binary to text and split into lines
            for row in csv_reader:
                if row:  # Ensure the row is not empty
                    recipients.append(row[0])  # Assuming emails are in the first column
        except Exception as e:
            return jsonify({"error": f"Error processing CSV file: {e}"}), 400

    try:
        if email_service == "Gmail":
            if schedule_time:
                # Schedule email sending
                scheduler.add_job(
                    send_gmail,
                    DateTrigger(run_date=schedule_time),
                    args=[sender_email, recipients, subject, body, cc, bcc],
                    id=f"email_{sender_email}_{time.time()}"
                )
                return jsonify({"message": f"Email scheduled for {schedule_time}"}), 202
            else:
                # Send email immediately
                mail_response, mail_response_code = send_gmail(sender_email, recipients, subject, body, cc, bcc)
        elif email_service == "Outlook":
            if schedule_time:
                # Schedule email sending
                scheduler.add_job(
                    send_outlook,
                    DateTrigger(run_date=schedule_time),
                    args=[sender_email, recipients, subject, body, cc, bcc],
                    id=f"email_{sender_email}_{time.time()}"
                )
                return jsonify({"message": f"Email scheduled for {schedule_time}"}), 202
            else:
                # Send email immediately
                mail_response, mail_response_code = send_outlook(sender_email, recipients, subject, body, cc, bcc)
        else:
            return jsonify({"error": "Invalid email service selected"}), 400

        return jsonify(mail_response), mail_response_code
    except Exception as e:
        return jsonify({"error": f"Error sending emails: {e}"}), 500

# For send email via Gmail API
def send_gmail(sender_email, recipients, subject, body, cc="", bcc=""):
    final, credentials = db.get_credentials_from_db_for_gmail(sender_email)
    
    if not credentials:
        return {"message": "User not Authenticated or Email Disabled"}, 403
    
    try:
        service = build("gmail", "v1", credentials=credentials)
        for i in range(len(recipients)):
            message = create_message("me", recipients[i], subject, body, cc, bcc)
            try:
                # Attempt to send the email
                sent_message = service.users().messages().send(userId="me", body=message).execute()
                message_id = sent_message.get("id")  # Extract the message ID

                # Poll Gmail API to check for delivery status
                status = poll_email_status(service, message_id)
                if status == "DELIVERED":
                    final+=1
                db.insert_email_status(recipients[i], "gmail", message_id, status)  # Update status in the database

            except Exception as e:
                # Log 'Failed' status if there's an error
                db.insert_email_status(recipients[i], "gmail", None, "FAILED")
        db.put_delivery_score(sender_email, final)
        return {"message": "Email sent successfully!"}, 200
    
    except Exception as e:
        return {"message": f"Failed to send email: {str(e)}"}, 400

# Poll Gmail API to get the delivery status of an email.
def poll_email_status(service, message_id, max_attempts=5, delay=5):
    for attempt in range(max_attempts):
        try:
            message = service.users().messages().get(userId="me", id=message_id).execute()
            label_ids = message.get("labelIds", [])
            if "SENT" in label_ids:
                return "DELIVERED"
            elif "INBOX" in label_ids:
                return "INBOXED"
            elif "SPAM" in label_ids:
                return "SPAMMED"
        except Exception as e:
            print(f"Error polling message status: {e}")
        time.sleep(delay)  # Wait before the next attempt
    return "UNKNOWN"

# Create Message for Gmail
def create_message(sender, to, subject, body, cc="", bcc=""):
    message = MIMEText(body)
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    if cc:
        message["cc"] = cc
    if bcc:
        message["bcc"] = bcc
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"raw": raw_message}

#Send Outlook Mail
def send_outlook(sender_email, recipients, subject, body, cc="", bcc=""):
    try:
        delivery_score, access_token, refresh_token, client_id, client_secret, scopes = db.get_credentials_from_db_for_outlook(sender_email)
        # Convert comma-separated scopes back to a space-separated string
        scopes = " ".join(scopes.split(",")) if scopes else ""
        new_access_token, new_refresh_token = refresh_outlook_access_token(client_id, client_secret, refresh_token, scopes)
        
        access_token = new_access_token

        for i in range(len(recipients)):
            headers = {
                'Authorization': 'Bearer ' + access_token
            }
            
             # Initialize the message structure
            message = {
                'toRecipients': [
                    {
                        'emailAddress': {
                            'address': recipients[i],
                            'name': 'CrowdMail'
                        }
                    }
                ],
                'subject': subject,
                'body': {
                    'contentType': 'text',
                    'content': body
                }
                # 'importance': 'low'
            }

            # Add CC if available
            if cc:
                cc_recipients = [{'emailAddress': {'address': email}} for email in cc.split(",")]
                message['ccRecipients'] = cc_recipients
            
            # Add BCC if available
            if bcc:
                bcc_recipients = [{'emailAddress': {'address': email}} for email in bcc.split(",")]
                message['bccRecipients'] = bcc_recipients
            
            request_body = {'message': message}
            
            requests.post('https://graph.microsoft.com/v1.0/me/sendMail', headers=headers, json=request_body)
            message_id = None
            status = "DELIVERED" #Assuming all the emails are delivered. because outlook api doesn't provide these informations.
            delivery_score += 1
            db.insert_email_status(recipients[i], "outlook", message_id, status)
        db.update_tokens_for_outlook(sender_email, delivery_score, new_access_token, new_refresh_token)
        return {"message": "Email Sent Successfully!"}, 200
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}, 500
    
#Refresh Access Token
def refresh_outlook_access_token(client_id, client_secret, refresh_token, scopes):
    url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    # Ensure required scopes are included
    mandatory_scopes = "openid profile offline_access"
    combined_scopes = f"{mandatory_scopes} {scopes}" if scopes else mandatory_scopes

    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'scope': combined_scopes
    }
    
    response = requests.post(url, data=data)
    
    if response.status_code == 200:
        tokens = response.json()
        # Update both access and refresh tokens
        new_access_token = tokens['access_token']
        new_refresh_token = tokens.get('refresh_token', refresh_token)  # Fallback to old if not rotated
        return new_access_token, new_refresh_token
    else:
        raise Exception(f"Failed to refresh token: {response.json()}")

#Delete the User
@app.route("/delete_user/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    result, status_code = db.delete_user(user_id)
    return jsonify(result), status_code

#Update Status of the User
@app.route("/update_user_status/<user_id>", methods=["PUT"])
def update_user_status(user_id):
    data = request.json
    status = data.get("status")
    if status not in ["enabled", "disabled"]:
        return jsonify({"error": "Invalid status"}), 400
    result, status_code = db.update_user_status(user_id, status)
    return jsonify(result), status_code

#Create Email Template
@app.route("/create_template", methods=["POST"])
def create_template():
    data = request.get_json()
    name = data.get('name')
    subject = data.get('subject')
    body = data.get('body')

    if not name or not subject or not body:
        return jsonify({"error": "All fields (name, subject, body) are required!"}), 400
    
    result, status_code = db.create_email_template(name, subject, body)
    return jsonify(result), status_code

#Delete Email Template
@app.route('/delete_template/<int:template_id>', methods=['DELETE'])
def delete_template(template_id):
    try:
        result, status_code = db.delete_email_template(template_id)
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#Update Email Template
@app.route('/update_template/<int:template_id>', methods=['PUT'])
def update_template(template_id):
    data = request.get_json()
    subject = data.get('subject')
    body = data.get('body')

    if not (subject or body):
        return jsonify({"error": "At least one field (name, subject, body) must be provided!"}), 400
    
    result, status_code = db.update_email_template(template_id, subject, body)
    return jsonify(result), status_code

#Get All Email Templates Available
@app.route('/get_templates', methods=['GET'])
def get_templates():
    try:
        response = db.get_email_templates()
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#Get Dashboard Statistics
@app.route("/dashboard_statistics", methods=["GET"])
def dashboard_statistics():
    stats = db.get_dashboard_statistics()
    return jsonify(stats), 200

#Get Verified Emails
@app.route("/oauth_emails", methods=["GET"])
def oauth_emails():
    try:
        emails = db.get_oauth_emails()
        return jsonify(emails), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000)