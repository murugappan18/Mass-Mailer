import streamlit as st
import requests
import pandas as pd
import time
import sqlite3
import pathlib
import plotly.graph_objects as go

# Flask API URL
API_URL = "https://mass-mailer.onrender.com"

# Function to fetch users and return as a Pandas DataFrame
def fetch_users():
    conn = sqlite3.connect('email_management.db')
    query = "SELECT * FROM users;"  # Query to fetch all data from the users table
    df = pd.read_sql(query, conn)  # Execute the query and return the result as a DataFrame
    conn.close()
    return df

# Function to fetch email templates and return as a Pandas DataFrame
def fetch_email_templates():
    conn = sqlite3.connect('email_management.db')
    query = "SELECT * FROM email_templates;"  # Query to fetch all data from the email_templates table
    df = pd.read_sql(query, conn)  # Execute the query and return the result as a DataFrame
    conn.close()
    return df

def fetch_verified_gmails():
    conn = sqlite3.connect('email_management.db')
    query = "SELECT email, status FROM oauth_credentials_for_gmail;"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def fetch_verified_outlook():
    conn = sqlite3.connect('email_management.db')
    query = "SELECT email, status FROM oauth_credentials_for_outlook;"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Show Login Page
def show_login_page():
    def load_css(file_path):
        # Inject CSS into the Streamlit app
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    css_path = pathlib.Path("assets/styles.css")
    load_css(css_path)

    st.title("Login")
    st.markdown("Admin Login Page.")
    with st.form(key="login_form"):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        submit_button = st.form_submit_button(label="Login")
    
    if submit_button:
        if email and password:
            response = requests.post(f"{API_URL}/login", json={
                "email": email,
                "password": password,
                "role": 1,
                "status": "enabled"
            })
            if response.status_code == 200:
                st.success("Login Successful!")
                st.session_state.logged_in = True
                st.session_state.active_page = "Manage Users"
                time.sleep(1)
                st.rerun()
            else:
                st.error("You are not authorized to access admin page.")
        else:
            st.warning("Please fill in both fields.")

# Admin Interface
def manage_user_interface():
    st.title("Admin Panel")
    st.write("Manage users from this interface.")
    
    # Tabs for different functionalities
    tab1, tab2, tab3 = st.tabs(["Create User", "Delete User", "Enable/Disable User"])

    # Fetch and display users table in all tabs
    users_df = fetch_users()
    if not users_df.empty:
        st.subheader("Users Table")
        st.dataframe(users_df)  # Display users table in DataFrame format

    with tab1:
        st.header("Create New User")
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        status = st.selectbox("Status", ["Enabled", "Disabled"], key="newuser")
        role = st.selectbox("Role", ["User", "Super User"])
        if role == "Super User":
            role = 1
        else:
            role = 0
        if st.button("Create User"):
            if username and email and password:
                response = requests.post(f"{API_URL}/register", json={
                    "username": username,
                    "status": status.lower(),
                    "email": email,
                    "password": password,
                    "role": role
                })
                if response.status_code == 200:
                    st.success("User created successfully!")
                    time.sleep(1)
                    st.rerun()
                elif response.status_code == 409:
                    st.error("User already exists.")
                else:
                    st.error(f"Failed to create user. {response.text}")
            else:
                st.warning("Please fill in all fields.")

    with tab2:
        st.header("Delete User")
        user_id = st.text_input("User ID (Delete)")
        if st.button("Delete User"):
            if user_id:
                response = requests.delete(f"{API_URL}/delete_user/{user_id}")
                if response.status_code == 200:
                    st.success("User deleted successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to delete user.")
            else:
                st.warning("Please provide a User ID.")

    with tab3:
        st.header("Enable/Disable User")
        user_id = st.text_input("User ID (Enable/Disable)")
        status = st.selectbox("Status", ["Enabled", "Disabled"], key="endis")
        if st.button("Update User Status"):
            if user_id:
                response = requests.put(f"{API_URL}/update_user_status/{user_id}", json={"status": status.lower()})
                if response.status_code == 200:
                    st.success(f"User {status.lower()} successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to update user status.")
            else:
                st.warning("Please provide a User ID.")

# Function to create a circular gauge with dynamic color for the entire circle
def circular_gauge_html(value):
    # Determine the color based on the value
    if value > 70:
        color = "#28A745"  # Green for >70%
    elif 40 < value <= 70:
        color = "#FFC107"  # Orange for >40% and <=70%
    else:
        color = "#DC3545"  # Red for <=40%

    return f"""
    <div style="background-color: #F9F9F9; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: 10px;">
            <h4 style="margin: 0; color: #333;">Deliverability</h4>
            <div style="position: relative; width: 120px; height: 120px;">
                <svg viewBox="0 0 36 36" width="120" height="120" xmlns="http://www.w3.org/2000/svg">
                    <!-- Colored arc based on deliverability value -->
                    <path
                        stroke-dasharray="{value}, 100"
                        style="stroke: {color}; fill: none; stroke-width: 3.8; stroke-linecap: round;"
                        d="M18 2.0845
                        a 15.9155 15.9155 0 0 1 0 31.831
                        a 15.9155 15.9155 0 0 1 0 -31.831"
                    ></path>
                    <!-- Background arc -->
                    <path
                        stroke-dasharray="100, 100"
                        style="stroke: #E0E0E0; fill: none; stroke-width: 3.8;"
                        d="M18 2.0845
                        a 15.9155 15.9155 0 0 1 0 31.831
                        a 15.9155 15.9155 0 0 1 0 -31.831"
                    ></path>
                    <!-- Percentage text -->
                    <text
                        x="18"
                        y="20.35"
                        text-anchor="middle"
                        style="font-size: 8px; fill: {color};"
                        alignment-baseline="central"
                        font-family="Arial, Helvetica, sans-serif"
                    >
                        {value:.1f}%
                    </text>
                </svg>
            </div>
        </div>
    </div>
    """

# Show Dashboard Page
def show_dashboard_page():
    if st.session_state.logged_in:
        st.title("Dashboard")
        response = requests.get(f"{API_URL}/dashboard_statistics")

        if response.status_code == 200:
            stats = response.json()
            try:
                # Fetch statistics
                delivered_count = stats.get('delivered_count')
                spammed_count = stats.get('spammed_count')
                sent_count = stats.get('sent_count')
                failed_count = stats.get('failed_count')
                inbox_count = max(delivered_count - spammed_count - failed_count, 0)  # Ensure no negative counts
                deliverability_score = (
                    (delivered_count / sent_count) * 100 if sent_count > 0 else 0
                )

                # Performance Summary Section
                st.markdown("### Performance Summary")
                
                col1, col2, col3 = st.columns([1, 1, 1])

                # Card 1: Sent Emails
                with col1:
                    st.markdown(f"""
                        <div style="background-color: #F9F9F9; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
                            <h4 style="color: #333;">Sent</h4>
                            <h2 style="color: #007BFF;">{sent_count}</h2>
                        </div>
                    """, unsafe_allow_html=True)

                # Card 2: Delivered Emails
                with col2:
                    st.markdown(f"""
                        <div style="background-color: #F9F9F9; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
                            <h4 style="color: #333;">Delivered</h4>
                            <h2 style="color: #28A745;">{delivered_count}</h2>
                        </div>
                    """, unsafe_allow_html=True)

                # Card 3: Failed Emails               
                with col3:
                    st.markdown(f"""
                        <div style="background-color: #F9F9F9; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
                            <h4 style="color: #333;">Failed</h4>
                            <h2 style="color: #DC3545;">{failed_count}</h2>
                        </div>
                    """, unsafe_allow_html=True)

                # Add spacing between rows
                st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

                col4, col5, col6 = st.columns([1, 1, 1])

                # Card 4: Spammed Emails
                with col4:
                    st.markdown(f"""
                        <div style="background-color: #F9F9F9; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
                            <h4 style="color: #333;">Spammed</h4>
                            <h2 style="color: #f4863b;">{spammed_count}</h2>
                        </div>
                    """, unsafe_allow_html=True)

                # Card 5: Inbox Percentage
                inbox_percentage = (
                    (inbox_count / delivered_count) * 100 if delivered_count > 0 else 0
                )
                with col5:
                    st.markdown(f"""
                        <div style="background-color: #F9F9F9; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
                            <h4 style="color: #333;">Inbox (%)</h4>
                            <h2 style="color: #17A2B8;">{inbox_percentage:.1f}%</h2>
                        </div>
                    """, unsafe_allow_html=True)

                # Card 6: Spam Percentage
                spam_percentage = (
                    (spammed_count / delivered_count) * 100 if delivered_count > 0 else 0
                )
                with col6:
                    st.markdown(f"""
                        <div style="background-color: #F9F9F9; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
                            <h4 style="color: #333;">Spam (%)</h4>
                            <h2 style="color: #DC3545;">{spam_percentage:.1f}%</h2>
                        </div>
                    """, unsafe_allow_html=True)
                
                # Add spacing between rows
                st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

                # Plotly gauge chart
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=deliverability_score,
                    title={"font": {"color": "#FAFAFA", "family": "Times New Roman", "weight": "bold"},"text": "Deliverability Score"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": "green"},
                    }
                ))
                st.plotly_chart(fig, use_container_width=True)
                    
                st.markdown(circular_gauge_html(deliverability_score), unsafe_allow_html=True)

                st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
                
                # Email Management Section
                st.markdown("### Mailbox Management")
                email_response = requests.get(f"{API_URL}/oauth_emails")
                if email_response.status_code == 200:
                    emails = email_response.json()
                    if emails:
                        # Convert the email data to a DataFrame
                        email_data = []
                        for email in emails:
                            email_data.append({
                                "Email Address": email['email'],
                                "Status": email['status'],
                                "Delivery Count": f"{email['delivery_score']}",
                                "Deliverability Score (%)": f"{email['deliverability']:.2f}",
                            })

                        df = pd.DataFrame(email_data)

                        # Display the email data in a table
                        st.markdown("<style>table {margin-top: 20px;}</style>", unsafe_allow_html=True)
                        st.table(df)
                    else:
                        st.info("No email data available.")
                else:
                    st.error("Failed to load email data.")

            except Exception as e:
                st.error(f"Error loading data: {e}")

        else:
            st.error("Failed to load dashboard data.")
    else:
        st.warning("Please log in to access the Dashboard.")

# Email Templates Management Interface
def email_templates_management():
    st.title("Email Templates Management")

    # Tabs for creating, updating, and deleting email templates
    tab1, tab2, tab3 = st.tabs(["Create Template", "Update Template", "Delete Template"])

    # Fetch and display email templates in all tabs
    templates_df = fetch_email_templates()
    if not templates_df.empty:
        st.subheader("Available Email Templates")
        st.dataframe(templates_df)  # Display email templates in DataFrame format

    with tab1:
        st.header("Create New Email Template")
        template_name = st.text_input("Template Name")
        subject = st.text_input("Subject")
        body = st.text_area("Body")
        
        if st.button("Create Template"):
            if template_name and subject and body:
                response = requests.post(f"{API_URL}/create_template", json={
                    "name": template_name,
                    "subject": subject,
                    "body": body
                })
                if response.status_code == 200:
                    st.success("Template created successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Failed to create template. {response.text}")
            else:
                st.warning("Please fill in all fields.")

    with tab2:
        st.header("Update Email Template")
        template_id = st.text_input("Template ID")
        new_subject = st.text_input("New Subject")
        new_body = st.text_area("New Body")
        
        if st.button("Update Template"):
            if template_id and new_subject or new_body:
                response = requests.put(f"{API_URL}/update_template/{template_id}", json={
                    "subject": new_subject,
                    "body": new_body
                })
                if response.status_code == 200:
                    st.success("Template updated successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Failed to update template. {response.text}")
            else:
                st.warning("Please fill in all fields.")

    with tab3:
        st.header("Delete Email Template")
        template_id = st.text_input("Template ID", key="template_id_input")
        
        if st.button("Delete Template"):
            if template_id:
                response = requests.delete(f"{API_URL}/delete_template/{template_id}")
                if response.status_code == 200:
                    st.success("Template deleted successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Failed to delete template. {response.text}")
            else:
                st.warning("Please select a template to delete.")

# Send Mass Mails Interface
def send_mass_mail_interface():
    st.title("Send Mass Mails")

    # Email service selection
    send_option = st.selectbox("Choose Email Service", ["Select", "Gmail", "Outlook"], key="service")
    email = st.text_input("Sender Email")

    # Fetch email templates from the API
    try:
        template_response = requests.get(f"{API_URL}/get_templates")
        if template_response.status_code == 200:
            templates = template_response.json()  # List of templates
            template_names = ["None"] + [template["name"] for template in templates]
        else:
            templates = []
            template_names = ["None"]
            st.warning("No templates available or failed to fetch templates.")
    except Exception as e:
        templates = []
        template_names = ["None"]
        st.error(f"Failed to fetch templates: {e}")

    # Initialize default subject and body
    default_subject = ""
    default_body = ""

    # Template selection logic
    selected_template_name = st.selectbox("Choose a Template (Optional)", template_names)
    if selected_template_name != "None":
        selected_template = next((template for template in templates if template["name"] == selected_template_name), None)
        if selected_template:
            default_subject = selected_template.get("subject", "")
            default_body = selected_template.get("body", "")

    # Subject and Body with editable fields
    subject = st.text_input("Email Subject", value=default_subject, key="subject")
    body = st.text_area("Email Body", value=default_body, key="body")

    # CC and BCC fields
    cc = st.text_area("CC [Give Comma-Seperated Values] (Optional)", value="", key="cc")
    bcc = st.text_area("BCC [Give Comma-Seperated Values] (Optional)", value="", key="bcc")

    # File uploader for CSV
    csv_file = st.file_uploader("Recipient Emails - Upload CSV file", type="csv")

    # Select Date and Time (shown above the buttons)
    selected_date = st.date_input("Select Date (Optional)", value=pd.to_datetime("today").date(), key="date_option")

    # Custom manual time input in 12-hour format
    time_input = st.text_input("Select Time (Optional) (Format - HH:MM AM/PM, e.g., 02:30 PM)", value="", key="time_option")
    
    # Validate the time format
    send_time = None
    try:
        if time_input:
            # Parse time input and convert to 24-hour format for backend processing
            time_parsed = pd.to_datetime(time_input, format='%I:%M %p').time()
            send_time = f"{selected_date} {time_parsed.strftime('%H:%M:%S')}"
    except ValueError:
        st.warning("Invalid time format! Please enter time in HH:MM AM/PM format.")

    # Buttons for "Send Now" and "Schedule Later"
    col1, col2 = st.columns(2)  # Two columns for buttons
    with col1:
        send_now_button = st.button("Send Now")
    with col2:
        schedule_later_button = st.button("Schedule Later")

    # If "Send Now" is clicked, set send_time to None
    if send_now_button:
        send_time = None

    # Handling the email sending process
    if send_now_button or schedule_later_button:
        if subject and body and csv_file:
            try:
                # Prepare the data for the API request
                files = {"csv_file": csv_file}
                data = {
                    "sender_email": email,
                    "subject": subject,
                    "body": body,
                    "email_service": send_option,
                    "send_time": send_time,
                    "cc": cc,
                    "bcc": bcc
                }

                # Make the API request to send the mail
                response = requests.post(
                    f"{API_URL}/send_mass_mail",
                    data=data,
                    files=files
                )

                if response.status_code == 200:
                    st.success("Emails sent successfully!")
                    time.sleep(1)
                    st.rerun()  # Reload the page to show updated status
                elif response.status_code == 202:
                    st.success("Email Scheduled Successfully!")
                    time.sleep(1)
                    st.rerun()
                elif response.status_code == 403:
                    st.error("User Not Authenticated. Verify your Email First.")
                else:
                    st.error(f"Failed to send emails: {response.text}")
            except Exception as e:
                st.error(f"An error occurred: {e}")
        else:
            st.warning("Please fill in all required fields.")

    cred_gmails = fetch_verified_gmails()
    cred_outlook = fetch_verified_outlook()
    if not cred_gmails.empty:
        st.subheader("Available Verified Gmails")
        st.dataframe(cred_gmails)
    if not cred_outlook.empty:
        st.subheader("Available Verified Outlook Mails")
        st.dataframe(cred_outlook)

# Sidebar Navigation
def sidebar_navigation():
    st.sidebar.title("Pages")
    if st.sidebar.button("Manage Users"):
        st.session_state.active_page = "Manage Users"
        st.rerun()
    if st.sidebar.button("Send Mass Mails"):
        st.session_state.active_page = "Send Mass Mails"
        st.rerun()
    if st.sidebar.button("Manage Templates"):
        st.session_state.active_page = "Email Templates"
        st.rerun()
    if st.sidebar.button("DashBoard"):
        st.session_state.active_page = "DashBoard"
        st.rerun()
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.active_page = "Login"
        st.rerun()

# Main flow
if __name__ == "__main__":
    # Initialize session state variables
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "active_page" not in st.session_state:
        st.session_state.active_page = "Login"
    
    # Sidebar for navigation
    if st.session_state.logged_in:
        sidebar_navigation()

    # Page rendering based on session state
    if st.session_state.active_page == "Login":
        show_login_page()
    elif st.session_state.active_page == "Manage Users":
        manage_user_interface()
    elif st.session_state.active_page == "Send Mass Mails":
        send_mass_mail_interface()
    elif st.session_state.active_page == "Email Templates":
        email_templates_management()
    elif st.session_state.active_page == "DashBoard":
        show_dashboard_page()