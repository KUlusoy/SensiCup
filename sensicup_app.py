from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
from flask_socketio import SocketIO, emit
import sqlite3
import json
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import cv2 # Import OpenCV

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app)

# Email configuration
EMAIL_ADDRESS = "sensicupteam@gmail.com"
EMAIL_PASSWORD = "rbie ebnn phut acnd"  # Use app password, not regular password

# Initialize database
def init_db():
    conn = sqlite3.connect('water_quality.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cup_id TEXT,
            ph REAL,
            tds REAL,
            salinity REAL,
            cleanliness_score REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cup_id TEXT,
            description TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# --- Camera Stream Functions ---
# This generator function captures frames from the webcam
# and encodes them as JPEG images to be streamed.
def gen_frames():
    # Use 0 for default webcam. If you have multiple, try 1, 2, etc.
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Error: Could not open video device.")
        return

    while True:
        success, frame = cap.read()
        if not success:
            print("Error: Could not read frame from camera.")
            break
        try:
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                print("Error: Could not encode frame.")
                continue
            frame = buffer.tobytes()
            # Yield the frame in a multipart response format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except Exception as e:
            print(f"Error processing frame: {e}")
            break
    cap.release() # Release the camera when done

# This new endpoint will serve the live video feed.
@app.route('/video_feed')
def video_feed():
    # Return a multipart response with the generated frames
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
# --- End Camera Stream Functions ---

# Home page - updated design (removed about route)
@app.route('/')
def home():
    return render_template("home.html")

# Your Cup page - updated with info popups
@app.route('/your-cup')
def your_cup():
    return render_template("your-cup.html")

# Database page - updated with "Database Section" instead of "Related Products"
@app.route('/database')
def database():
    return render_template("database.html")

# Function to send actual email
def send_email(to_email, subject, body, from_name, from_email):
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add body to email
        msg.attach(MIMEText(body, 'plain'))
        
        # Gmail SMTP configuration
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_ADDRESS, to_email, text)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

# Handle contact form submission with actual email sending
@app.route('/send-contact', methods=['POST'])
def send_contact():
    try:
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        message = request.form['message']
        
        # Create email content
        subject = f"Contact Form Submission from {first_name} {last_name}"
        body = f"""
New contact form submission from SensiCup website:

Name: {first_name} {last_name}
Email: {email}
Message: 
{message}

---
This message was sent from the SensiCup contact form.
        """
        
        # Send email to your team
        email_sent = send_email(
            to_email="sensicupteam@gmail.com",
            subject=subject,
            body=body,
            from_name=f"{first_name} {last_name}",
            from_email=email
        )
        
        # Store in database
        conn = sqlite3.connect('water_quality.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT,
                last_name TEXT,
                email TEXT,
                message TEXT,
                email_sent BOOLEAN,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            INSERT INTO contact_messages (first_name, last_name, email, message, email_sent)
            VALUES (?, ?, ?, ?, ?)
        ''', (first_name, last_name, email, message, email_sent))
        conn.commit()
        conn.close()
        
        # Return success page
        if email_sent:
            return '''
            <div style="text-align: center; padding: 5rem; font-family: 'Segoe UI', sans-serif;">
                <h1 style="color: #4CAF50; margin-bottom: 2rem;">✅ Message Sent Successfully!</h1>
                <p style="font-size: 1.2rem; margin-bottom: 2rem;">Thank you for contacting us. We've received your message and will get back to you soon!</p>
                <a href="/" style="background: #1976d2; color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px;">Return to Home</a>
            </div>
            '''
        else:
            return '''
            <div style="text-align: center; padding: 5rem; font-family: 'Segoe UI', sans-serif;">
                <h1 style="color: #ff9800; margin-bottom: 2rem;">⚠️ Message Saved</h1>
                <p style="font-size: 1.2rem; margin-bottom: 2rem;">Your message has been saved to our database, but email delivery failed. We'll still review your message!</p>
                <a href="/contact" style="background: #1976d2; color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px;">Back to Contact</a>
            </div>
            '''
        
    except Exception as e:
        return f'''
        <div style="text-align: center; padding: 5rem; font-family: 'Segoe UI', sans-serif;">
                <h1 style="color: #4CAF50; margin-bottom: 2rem;">✅ Message Sent Successfully!</h1>
                <p style="font-size: 1.2rem; margin-bottom: 2rem;">Thank you for contacting us. We've received your message and will get back to you soon!</p>
                <a href="/" style="background: #1976d2; color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px;">Return to Home</a>
            </div>
        '''

# Handle photo submission
@app.route('/submit-photo', methods=['POST'])
def submit_photo():
    try:
        description = request.form['description']
        cup_id = request.form.get('cup_id', 'unknown')
        
        # Store in database
        conn = sqlite3.connect('water_quality.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_photos (cup_id, description)
            VALUES (?, ?)
        ''', (cup_id, description))
        conn.commit()
        conn.close()
        
        return '''
        <div style="text-align: center; padding: 5rem; font-family: 'Segoe UI', sans-serif;">
            <h1 style="color: #4CAF50; margin-bottom: 2rem;">✅ Photo Submitted Successfully!</h1>
            <p style="font-size: 1.2rem; margin-bottom: 2rem;">Thank you for contributing to our database!</p>
            <a href="/database" style="background: #1976d2; color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px;">Back to Database</a>
        </div>
        '''
        
    except Exception as e:
        return '''
        <div style="text-align: center; padding: 5rem; font-family: 'Segoe UI', sans-serif;">
                <h1 style="color: #4CAF50; margin-bottom: 2rem;">✅ Message Sent Successfully!</h1>
                <p style="font-size: 1.2rem; margin-bottom: 2rem;">Thank you for contacting us. We've received your message and will get back to you soon!</p>
                <a href="/" style="background: #1976d2; color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px;">Return to Home</a>
            </div>
        '''

# API endpoint for Raspberry Pi to send data
@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.json
        
        # Store in database
        conn = sqlite3.connect('water_quality.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sensor_readings (cup_id, ph, tds, salinity, cleanliness_score)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['cup_id'], data['ph'], data['tds'], data['salinity'], data['cleanliness_score']))
        conn.commit()
        conn.close()
        
        # Send real-time update to all connected clients
        socketio.emit('sensor_update', data)
        
        return jsonify({'status': 'success', 'message': 'Data received'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

# Handle client connections
@socketio.on('get_latest_data')
def handle_latest_data(data):
    cup_id = data['cup_id']
    
    # Get latest reading from database
    conn = sqlite3.connect('water_quality.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ph, tds, salinity, cleanliness_score
        FROM sensor_readings
        WHERE cup_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
    ''', (cup_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        emit('sensor_update', {
            'cup_id': cup_id,
            'ph': result[0],
            'tds': result[1],
            'salinity': result[2],
            'cleanliness_score': result[3]
        })

if __name__ == '__main__':
    init_db()
    import os
    port = int(os.environ.get('PORT', 5002))
    socketio.run(app, debug=False, host='0.0.0.0', port=port)