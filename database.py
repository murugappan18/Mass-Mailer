import sqlite3
import hashlib
import os
from google.oauth2.credentials import Credentials

class Database:
    def __init__(self, db_name="email_management.db"):
        self.db_name = db_name
        self._initialize_database()

    # Initailize Database
    def _initialize_database(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        #For App Registration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT,
                username TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT
            )
        """)
        # Create oauth_credentials_for_gmail table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_credentials_for_gmail (
                email TEXT PRIMARY KEY,
                status TEXT,
                delivery_score INTEGER,
                token TEXT,
                refresh_token TEXT,
                token_uri TEXT,
                client_id TEXT,
                client_secret TEXT,
                scopes TEXT
            )
        """)
        # Create oauth_credentials_for_outlook table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_credentials_for_outlook (
                email TEXT PRIMARY KEY,
                status TEXT,
                delivery_score INTEGER,
                access_token TEXT,
                refresh_token TEXT,
                client_id TEXT,
                client_secret TEXT,
                scopes TEXT
            )
        """)
        # Create email_status table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient TEXT NOT NULL,
                service TEXT,
                message_id TEXT,
                status TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        #Create template_management
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()

    # Hash Password with SHA-256
    def hash_password(self, password):
        # Generate a salt
        salt = os.urandom(32)  # A 32-byte salt
        # Create the SHA-256 hash with the password and salt
        password_hash = hashlib.sha256(salt + password.encode()).hexdigest()
        # Return the salt and hash as a tuple
        return salt.hex() + ':' + password_hash
    
    # Verify Password with SHA-256
    def verify_password(self, password, hashed):
        # Split the stored hash into the salt and the hash
        salt, stored_hash = hashed.split(':')
        salt = bytes.fromhex(salt)
        # Hash the provided password with the stored salt
        return stored_hash == hashlib.sha256(salt + password.encode()).hexdigest()

    # Register New User Details
    def register_user(self, username, email, password, status, role):
        password_hash = self.hash_password(password)
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, email, password_hash, status, role) VALUES (?, ?, ?, ?, ?)", 
                           (username, email, password_hash, status, role))
            conn.commit()
            return {"message": "User registered successfully!"}, 200
        except sqlite3.IntegrityError:
            return {"error": "Username or email already exists!"}, 409
        finally:
            conn.close()

    # Verify Login User Details
    def verify_user(self, email, password, role, status):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE email = ? AND role = ? AND status = ?", (email, role, status))
        result = cursor.fetchone()
        conn.close()
        if result and self.verify_password(password, result[0]):
            return {"message": "Login successful!"}, 200
        return {"error": "Incorrect email or password."}, 401
    
    #Store the Status of Mail
    def insert_email_status(self, recipient, service, message_id, status):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO email_status (recipient, service, message_id, status)
                VALUES (?, ?, ?, ?)
            """, (recipient, service, message_id, status))
            conn.commit()
        except Exception as e:
            return {f"Error updating email status for message ID {message_id}: {e}"}
        finally:
            conn.close()

    # Get Dashboard Statistics
    def get_dashboard_statistics(self):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            #delivered mail count
            cursor.execute("SELECT COUNT(*) FROM email_status WHERE status = 'DELIVERED' ")
            delivered_count = cursor.fetchone()[0]
            #spammed mail count
            cursor.execute("SELECT COUNT(*) FROM email_status WHERE status = 'SPAMMED' ")
            spammed_count = cursor.fetchone()[0]
            #failed mail count
            cursor.execute("SELECT COUNT(*) FROM email_status WHERE status = 'FAILED' ")
            failed_count = cursor.fetchone()[0]

            sent_count = delivered_count + spammed_count + failed_count
            # Sample statistics; in a real scenario, store and retrieve these values properly
            stats = {
                "sent_count": sent_count,
                "delivered_count": delivered_count,
                "spammed_count": spammed_count,
                "failed_count": failed_count
            }
            return stats
        except Exception as e:
            return {"error": f"Database query failed due to following Error - {e}"}
        finally:
            conn.close()

    #Get Verified Emails in Database
    def get_oauth_emails(self):
        try:
            db = Database()
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Query for Gmail credentials
            cursor.execute("""
                SELECT email, status, delivery_score FROM oauth_credentials_for_gmail GROUP BY email
            """)
            gmail_emails = cursor.fetchall()

            # Query for Outlook credentials
            cursor.execute("""
                SELECT email, status, delivery_score FROM oauth_credentials_for_outlook GROUP BY email
            """)
            outlook_emails = cursor.fetchall()

            # Get the dashboard statistics
            stats = db.get_dashboard_statistics()
            sent_count = stats.get('sent_count')

            # Process Gmail emails
            gmail_email_data = [{"email": row[0], "status": row[1], "delivery_score": row[2], "deliverability": (row[2] / sent_count) * 100} for row in gmail_emails]

            # Process Outlook emails
            outlook_email_data = [{"email": row[0], "status": row[1], "delivery_score": row[2], "deliverability": (row[2] / sent_count) * 100} for row in outlook_emails]

            # Combine Gmail and Outlook email data
            emails = gmail_email_data + outlook_email_data

            return emails
        except Exception as e:
            return {"error": f"Database query failed: {e}"}
        finally:
            conn.close()
    
    #Put Delivery Score
    def put_delivery_score(self, sender_email, final):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE oauth_credentials_for_gmail SET delivery_score = ? WHERE email = ?
            """, (final, sender_email,))
            conn.commit()
            conn.close()
            return {"message": "Successfully Updated."}, 200
        except Exception as e:
            return {"error": f"Error Occured. {e}"}, 400
    
    # Store Credentials
    def store_credentials_for_gmail(self, email, credentials, status, delivery_score):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Check if the email already exists in the database
        cursor.execute("""
            SELECT email FROM oauth_credentials_for_gmail WHERE email = ?
        """, (email,))
        existing_email = cursor.fetchone()

        if existing_email:
            # If email exists, update only non-email and non-delivery_score fields
            cursor.execute("""
                UPDATE oauth_credentials_for_gmail 
                SET status = ?, token = ?, refresh_token = ?, token_uri = ?, client_id = ?, client_secret = ?, scopes = ?
                WHERE email = ?
            """, (
                status,
                credentials.token,
                credentials.refresh_token,
                credentials.token_uri,
                credentials.client_id,
                credentials.client_secret,
                ",".join(credentials.scopes),
                email
            ))
        else:
            # If email doesn't exist, insert a new record
            cursor.execute("""
                INSERT INTO oauth_credentials_for_gmail (email, status, delivery_score, token, refresh_token, token_uri, client_id, client_secret, scopes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                email,
                status,
                delivery_score,  # The delivery_score is kept intact here
                credentials.token,
                credentials.refresh_token,
                credentials.token_uri,
                credentials.client_id,
                credentials.client_secret,
                ",".join(credentials.scopes),
            ))

        conn.commit()
        conn.close()

    # Store Outlook Credentials
    def store_credentials_for_outlook(self, user_email, access_token, refresh_token, client_id, client_secret, scopes, status, delivery_score):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Check if the email already exists in the database
        cursor.execute("""
            SELECT email FROM oauth_credentials_for_outlook WHERE email = ?
        """, (user_email,))
        existing_email = cursor.fetchone()

        if existing_email:
            # If email exists, update only non-email and non-delivery_score fields
            cursor.execute("""
                UPDATE oauth_credentials_for_outlook 
                SET status = ?, access_token = ?, refresh_token = ?, client_id = ?, client_secret = ?, scopes = ?
                WHERE email = ?
            """, (
                status,
                access_token,
                refresh_token,
                client_id,
                client_secret,
                ",".join(scopes),
                user_email
            ))
        else:
            # If email doesn't exist, insert a new record
            cursor.execute("""
                INSERT INTO oauth_credentials_for_outlook (email, status, delivery_score, access_token, refresh_token, client_id, client_secret, scopes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_email,
                status,
                delivery_score,  # The delivery_score is kept intact here
                access_token,
                refresh_token,
                client_id,
                client_secret,
                ",".join(scopes)
            ))

        conn.commit()
        conn.close()

    # Retrieve credentials
    def get_credentials_from_db_for_gmail(self, email):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row  # Enable dictionary-like row access
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT token, refresh_token, token_uri, client_id, client_secret, scopes
                FROM oauth_credentials_for_gmail WHERE email = ? AND status = 'enabled'
            """, (email,))
            result = cursor.fetchone()

            # Handle the case where no credentials are found
            if not result:
                conn.close()
                return None, None

            cursor.execute("""
                SELECT delivery_score FROM oauth_credentials_for_gmail WHERE email = ? AND status = 'enabled'
            """, (email,))
            
            delivery_score_result = cursor.fetchone()

            # Handle the case where no delivery score is found
            final_value = delivery_score_result[0] if delivery_score_result else 0
            conn.close()

            return final_value, Credentials(
                token=result["token"],
                refresh_token=result["refresh_token"],
                token_uri=result["token_uri"],
                client_id=result["client_id"],
                client_secret=result["client_secret"],
                scopes=result["scopes"].split(","),
            )
        except Exception as e:
            print(f"Database error: {e}")
            conn.close()
            return None, None
    
    # Retrieve credentials for Outlook
    def get_credentials_from_db_for_outlook(self, email):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT delivery_score, access_token, refresh_token, client_id, client_secret, scopes FROM oauth_credentials_for_outlook WHERE email = ? AND status = 'enabled'
        """, (email,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return result
        else:
            return None
    
    #Update Tokens in Outlook
    def update_tokens_for_outlook(self, email, delivery_score, access_token, refresh_token):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE oauth_credentials_for_outlook SET delivery_score = ?, access_token = ?, refresh_token = ? WHERE email=?
            """, (delivery_score, access_token, refresh_token, email,))
            conn.commit()
            conn.close()
            return {"message": "Successfully Updated."}, 200
        except Exception as e:
            return {"error": f"Error Occured. {e}"}, 400
    
    def delete_user(self, user_id):
        try:
            conn = sqlite3.connect(self.db_name)
            query = "DELETE FROM users WHERE id = ?;"
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            conn.commit()
            
            if cursor.rowcount == 0:  # Check if any rows were deleted
                return {"message": "User ID not found. No deletion occurred."}, 404
            else:
                return {"message": "User Deleted Successfully!"}, 200
        except Exception as e:
            return {"error": f"Error Occured. {e}"}, 400
        finally:
            conn.close()
    
    def update_user_status(self, user_id, status):
        try:
            conn = sqlite3.connect(self.db_name)
            query = "UPDATE users SET status = ? WHERE id = ?;"
            cursor = conn.cursor()
            cursor.execute(query, (status, user_id))
            conn.commit()  # Commit the changes to the database
            
            if cursor.rowcount == 0:  # Check if any rows were updated
                return {"message": "User ID not found. No update occurred."}, 404
            else:
                return {"message": "User Status Updated Successfully!"}, 200
        except Exception as e:
            return {"error": f"Error Occurred. {e}"}, 400
        finally:
            conn.close()
        
    def create_email_template(self, name, subject, body):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO email_templates (name, subject, body)
            VALUES (?, ?, ?)
            """, (name, subject, body))
            conn.commit()
            conn.close()
            return {"message": "Template created successfully!"}, 200
        except Exception as e:
            return {"error": str(e)}, 500
        
    def delete_email_template(self, template_id):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM email_templates WHERE id = ?", (template_id,))
            conn.commit()
            conn.close()

            if cursor.rowcount == 0:
                return {"error": "Template not found!"}, 404

            return {"message": "Template deleted successfully!"}, 200
        except Exception as e:
            return {"error": str(e)}, 500
    
    def update_email_template(self, template_id, subject, body):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            query = "UPDATE email_templates SET timestamp = CURRENT_TIMESTAMP"
            params = []
            if subject:
                query += ", subject = ?"
                params.append(subject)
            if body:
                query += ", body = ?"
                params.append(body)

            query += " WHERE id = ?"
            params.append(template_id)

            cursor.execute(query, tuple(params))
            conn.commit()
            conn.close()

            if cursor.rowcount == 0:
                return {"error": "Template not found!"}, 404

            return {"message": "Template updated successfully!"}, 200
        except Exception as e:
            return {"error": str(e)}, 500
        
    def get_email_templates(self):
        try:
            conn = sqlite3.connect(self.db_name)
            conn.row_factory = sqlite3.Row  # Enables dictionary-like access
            cursor = conn.cursor()

            cursor.execute("SELECT id, name, subject, body FROM email_templates")
            templates = [dict(row) for row in cursor.fetchall()]

            conn.close()
            return templates
        except Exception as e:
            return {f"Database error: {e}"}, 500

    def close(self):
        self.conn.close()