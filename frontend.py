import streamlit as st
import requests
import time
import pandas as pd
import altair as alt
import plotly.express as px
import pathlib
import re

# Flask API URL
API_URL = "http://127.0.0.1:5000"

# Define functions to handle each page's content
def show_home_page():
    st.title("Mass Mailer")
    st.header("Welcome to Mass Mailing Application")

# Show Register Page
def show_register_page():
    def load_css(file_path):
        # Inject CSS into the Streamlit app
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    css_path = pathlib.Path("assets/styles.css")
    load_css(css_path)

    st.title("Register")
    st.markdown("Please create a new account below.")

    def is_strong_password(password):
        # Check if the password contains at least one capital letter, one number, and one special symbol
        if (len(password) >= 8 and
                re.search(r'[A-Z]', password) and
                re.search(r'\d', password) and
                re.search(r'[!@#$%^&*(),.?":{}|<>]', password)):
            return True
        return False

    def is_valid_email(email):
        # Validate email format
        import re
        if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            return True
        return False

    # Initialize variables to store error states
    email_error = ""
    password_error = ""

    with st.form(key="register_form"):
        # Username
        st.markdown("""<div style="color: black; font-weight: bold; font-size: 16px; margin-bottom: 10px;">Username</div>""", unsafe_allow_html=True)
        username = st.text_input(label="Username", label_visibility="collapsed", placeholder="Enter your username", key="username_input")
        
        # Email
        st.markdown("""<div style="color: black; font-weight: bold; font-size: 16px; margin-bottom: 10px;">Email</div>""", unsafe_allow_html=True)
        email = st.text_input(label="Email", label_visibility="collapsed", placeholder="Enter your email", key="email_input")
        
        # Password
        st.markdown("""<div style="color: black; font-weight: bold; font-size: 16px; margin-bottom: 10px;">Password</div>""", unsafe_allow_html=True)
        password = st.text_input(label="Password", label_visibility="collapsed", type="password", placeholder="Enter your password", key="password_input")

        # Create columns for the button and the register link
        col1, col2 = st.columns([2, 1])
        with col1:
            submit_button = st.form_submit_button(label="Register")
        with col2:
            st.markdown(
                """
                <div style="text-align: right; padding-top: 5px; color: black; font-weight: bold;">
                    Already have an account?<br>
                    <a href="http://localhost:8501/?page=login" target="_self" style="color: rgb(0, 0, 0); text-decoration: underline;">
                        Login here
                    </a>
                </div>
                """,
                unsafe_allow_html=True
            )

    if submit_button:
        # Validate email
        if not is_valid_email(email):
            email_error = "Invalid email format. Please enter a valid email."
        else:
            email_error = ""

        # Validate password
        if not is_strong_password(password):
            password_error = "Password must be at least 8 characters long and include at least one uppercase letter, one number, and one special character."
        else:
            password_error = ""

        # Display errors if any
        if email_error:
            st.error(email_error)
        if password_error:
            st.error(password_error)

        # Proceed with registration if no errors
        if not email_error and not password_error and username:
            response = requests.post(f"{API_URL}/register", json={
                "username": username,
                "status": "enabled",
                "email": email,
                "password": password,
                "role": 0
            })
            if response.status_code == 200:
                st.success("User registered successfully!")
                time.sleep(1)
                set_page("login")
                st.rerun()
            elif response.status_code == 409:
                st.error("Username or email already exists!")
            else:
                st.error("Registration failed.")
        elif not username:
            st.warning("Please fill in all fields.")

# Show Login Page
def show_login_page():
    def load_css(file_path):
        # Inject CSS into the Streamlit app
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    css_path = pathlib.Path("assets/styles.css")
    load_css(css_path)

    # Add a title and description to enhance the page UI
    st.title("Login")
    st.markdown("Please log in to access your account.")

    # # Create styled login form    
    with st.form(key="login_form"):
        # Email
        st.markdown("""<div style="color: black; font-weight: bold; font-size: 16px; margin-bottom: 10px;">Email</div>""", unsafe_allow_html=True)
        email = st.text_input(label="Email", label_visibility="collapsed", placeholder="Enter your email", key="login_email")
        
        # Password
        st.markdown("""<div style="color: black; font-weight: bold; font-size: 16px; margin-bottom: 10px;">Password</div>""", unsafe_allow_html=True)
        password = st.text_input(label="Password", label_visibility="collapsed", type="password", placeholder="Enter your password", key="login_password")

        # Create columns for the button and the register link
        col1, col2 = st.columns([2, 1])
        with col1:
            submit_button = st.form_submit_button(label="Login")
        with col2:
            st.markdown(
                """
                <div style="text-align: right; padding-top: 5px; color: black; font-weight: bold;">
                    Don't have an account?<br>
                    <a href="http://localhost:8501/?page=register" target="_self" style="color: rgb(0, 0, 0); text-decoration: underline;">
                        Register here
                    </a>
                </div>
                """,
                unsafe_allow_html=True
            )

    # Login action
    if submit_button:
        if email and password:
            response = requests.post(f"{API_URL}/login", json={
                "email": email,
                "password": password,
                "role": 0,
                "status": "enabled"
            })
            if response.status_code == 200:
                st.session_state.logged_in = True
                st.success("Login Successful!")
                time.sleep(1)
                set_page("home")
                st.rerun()
            else:
                st.error("Incorrect email or password.")
        else:
            st.warning("Please fill in both fields.")

#Show Mail Page
def show_send_mass_mail_page():
    if st.session_state.logged_in:
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
                        time.sleep(1)
                        set_page("email_verification")
                        st.rerun()
                    else:
                        st.error(f"Failed to send emails: {response.text}")
                except Exception as e:
                    st.error(f"An error occurred: {e}")
            else:
                st.warning("Please fill in all required fields.")
    else:
        st.warning("Please log in to access the Send Mass Mail Page.")

#Show Dashboard Page
def show_dashboard_page():
    if st.session_state.logged_in:
        st.subheader("Dashboard")
        response = requests.get(f"{API_URL}/dashboard_statistics")
        if response.status_code == 200:
            stats = response.json()
            try:
                sent_count = stats.get('sent_count')
                delivered_count = stats.get('delivered_count')
                spammed_count = stats.get('spammed_count')
                failed_count = stats.get('failed_count')

                # Prepare data for Altair
                bar_data = pd.DataFrame({
                    "Email Type": ["Sent", "Delivered", "Landed in Spam", "Failed"],
                    "Count": [sent_count, delivered_count, spammed_count, failed_count]
                })

                # Create Altair bar chart
                bar_chart = alt.Chart(bar_data).mark_bar().encode(
                    x=alt.X("Email Type", sort=None, title="Email Type", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y(
                        "Count",
                        title="Count",
                        axis=alt.Axis(format="d", tickCount=stats.get('sent_count', 10)),  # Control tick count
                        scale=alt.Scale(domainMin=0, nice=True)  # Use proper scaling
                    ),
                    color=alt.Color("Email Type", scale=alt.Scale(scheme="category10"))
                ).properties(
                    title="Email Statistics",
                    width=600,
                    height=400
                )

                # Display bar chart
                st.altair_chart(bar_chart, use_container_width=True)

                # Pie Chart for Email Status
                pie_fig = px.pie(
                    values=[sent_count, delivered_count, spammed_count],
                    names=['Sent', 'Delivered', 'Spam'],
                    title="Email Landing Status"
                )

                # Display the pie chart
                st.plotly_chart(pie_fig)

            except Exception as e:
                st.error("Data not available to Load Dashboard")

            st.write("### Statistics")
            st.write(f"Total Emails Sent: {stats.get('sent_count', 'N/A')}")
            st.write(f"Total Emails Successfully Delivered: {stats.get('delivered_count', 'N/A')}")
            st.write(f"Total Emails Spammed: {stats.get('spammed_count', 'N/A')}")
            st.write(f"Total Emails Failed: {stats.get('failed_count', 'N/A')}")
        else:
            st.error("Failed to load dashboard data.")
    else:
        st.warning("Please log in to access the Dashboard.")

# Show Verification Page
def email_verification_page():
    if st.session_state.logged_in:
        st.title("Email Verification")
        
        # Add some guiding text for the user
        st.write(
            """
            To verify your email and gain access to the full features of the application, 
            please choose one of the following options:
            
            1. **Verify Gmail**: If you are using Gmail, click the button below to authenticate your Gmail account.
            2. **Verify Outlook**: If you are using Outlook, click the button below to authenticate your Outlook account.
            """
        )
        
        # Add space for clarity
        st.write("###")

        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Verify Gmail"):
                st.write("Redirecting to Google OAuth...")
                st.markdown(
                    f'<a href="{API_URL}/verify_email" target="_self">Click here to continue</a>',
                    unsafe_allow_html=True
                )
                
        with col2:
            if st.button("Verify Outlook"):
                st.write("Redirecting to Outlook OAuth...")
                st.markdown(
                    f'<a href="{API_URL}/verify_outlook" target="_self">Click here to continue</a>',
                    unsafe_allow_html=True
                )
                
    else:
        st.warning("Please log in to access the Email Verification.")

# Define a dictionary to map pages to their functions
page_functions = {
    "home": show_home_page,
    "register": show_register_page,
    "login": show_login_page,
    "send_mass_mail": show_send_mass_mail_page,
    "dashboard": show_dashboard_page,
    "email_verification": email_verification_page
}

# Helper functions to manage query params
def set_page(page_name):
    st.session_state.page = page_name
    st.query_params.update({"page": page_name})

def get_page_from_query_params():
    return st.query_params.get("page", "home")

# Initialize session state for login and page if not already set
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
st.session_state.page = get_page_from_query_params()

# Sidebar for navigation
st.sidebar.title("Pages")

if st.sidebar.button("Home"):
    set_page("home")

if not st.session_state.logged_in:
    if st.sidebar.button("Register"):
        set_page("register")
    if st.sidebar.button("Login"):
        set_page("login")
else:
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        set_page("home")
        st.rerun()

if st.sidebar.button("Send Mass Mail"):
    set_page("send_mass_mail")

if st.sidebar.button("Dashboard"):
    set_page("dashboard")

if st.sidebar.button("Verify Email"):
    set_page("email_verification")

# Display the correct page based on session state
page_functions[st.session_state.page]()