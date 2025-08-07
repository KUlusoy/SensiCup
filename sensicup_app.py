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

# Initialize database with proper schema
def init_db():
    conn = sqlite3.connect('water_quality.db')
    cursor = conn.cursor()
    
    # Check if temperature column exists, add it if it doesn't
    cursor.execute("PRAGMA table_info(sensor_readings)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'sensor_readings' not in [table[0] for table in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        # Create table if it doesn't exist
        cursor.execute('''
            CREATE TABLE sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cup_id TEXT,
                ph REAL,
                tds REAL,
                temperature REAL,
                salinity REAL,
                cleanliness_score REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    elif 'temperature' not in columns:
        # Add temperature column if table exists but column doesn't
        cursor.execute('ALTER TABLE sensor_readings ADD COLUMN temperature REAL DEFAULT 25.0')
    
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
def gen_frames():
    """Generate frames from available camera with fallback"""
    cap = None
    
    # Try different camera indices (0, 1, 2) to find an available camera
    for camera_index in range(3):
        try:
            cap = cv2.VideoCapture(camera_index)
            if cap.isOpened():
                print(f"Successfully opened camera at index {camera_index}")
                break
            else:
                cap.release()
        except Exception as e:
            print(f"Failed to open camera {camera_index}: {e}")
            continue
    
    if cap is None or not cap.isOpened():
        print("Error: No camera available. Serving placeholder image.")
        # Return a placeholder frame instead of failing
        placeholder_frame = generate_placeholder_frame()
        while True:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + placeholder_frame + b'\r\n')

    # Set camera properties for better performance
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 15)

    frame_count = 0
    while True:
        success, frame = cap.read()
        if not success:
            print("Error: Could not read frame from camera.")
            break
        
        try:
            # Process every nth frame to reduce CPU usage
            frame_count += 1
            if frame_count % 2 == 0:  # Skip every other frame
                continue
                
            # Resize frame to reduce bandwidth
            frame = cv2.resize(frame, (320, 240))
            
            # Encode frame as JPEG with lower quality for better performance
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            ret, buffer = cv2.imencode('.jpg', frame, encode_param)
            
            if not ret:
                print("Error: Could not encode frame.")
                continue
                
            frame_bytes = buffer.tobytes()
            
            # Yield the frame in a multipart response format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                   
        except Exception as e:
            print(f"Error processing frame: {e}")
            break
            
    if cap:
        cap.release()

def generate_placeholder_frame():
    """Generate a placeholder image when no camera is available"""
    import numpy as np
    
    # Create a simple placeholder image
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    img.fill(128)  # Gray background
    
    # Add text (this is basic, you might want to use PIL for better text)
    font = cv2.FONT_HERSHEY_SIMPLEX
    text = "Camera Not Available"
    text_size = cv2.getTextSize(text, font, 0.7, 2)[0]
    text_x = (img.shape[1] - text_size[0]) // 2
    text_y = (img.shape[0] + text_size[1]) // 2
    cv2.putText(img, text, (text_x, text_y), font, 0.7, (255, 255, 255), 2)
    
    # Encode as JPEG
    ret, buffer = cv2.imencode('.jpg', img)
    return buffer.tobytes()

# This endpoint serves the live video feed
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
# --- End Camera Stream Functions ---

# Home page
@app.route('/')
def home():
    return render_template("home.html")

# Your Cup page
@app.route('/your-cup')
def your_cup():
    return render_template("your-cup.html")

# Database page
@app.route('/database')
def database():
    return render_template("database.html")

# Contact page
@app.route('/contact')
def contact():
    return render_template("contact.html")

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

# Handle contact form submission
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

# API endpoint for ESP32 to send sensor data
@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.json
        print(f"Received raw data: {data}")  # Debug print
        
        # Extract sensor values with fallback defaults
        cup_id = data.get('cup_id', 'UNKNOWN')
        ph = float(data.get('ph', 7.0))
        tds = float(data.get('tds', 0.0))
        temperature = float(data.get('temperature', 25.0))
        salinity = float(data.get('salinity', 0.0))
        cleanliness_score = float(data.get('cleanliness_score', 85))
        
        print(f"Processed sensor data:")
        print(f"Cup ID: {cup_id}")
        print(f"pH: {ph}")
        print(f"TDS: {tds} ppm")
        print(f"Temperature: {temperature}°C")
        print(f"Salinity: {salinity}")
        print(f"Cleanliness Score: {cleanliness_score}")
        
        # Store in database
        conn = sqlite3.connect('water_quality.db')
        cursor = conn.cursor()
        
        # Insert the data
        cursor.execute('''
            INSERT INTO sensor_readings (cup_id, ph, tds, temperature, salinity, cleanliness_score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (cup_id, ph, tds, temperature, salinity, cleanliness_score))
        conn.commit()
        conn.close()
        
        # Prepare data for WebSocket broadcast
        sensor_data = {
            'cup_id': cup_id,
            'ph': ph,
            'tds': tds,
            'temperature': temperature,
            'salinity': salinity,
            'cleanliness_score': cleanliness_score,
            'timestamp': datetime.now().isoformat()
        }
        
        # Send real-time update to all connected clients
        socketio.emit('sensor_update', sensor_data)
        
        return jsonify({
            'status': 'success', 
            'message': 'Sensor data received successfully',
            'data': sensor_data
        }), 200
        
    except Exception as e:
        print(f"Error processing sensor data: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': str(e)
        }), 400

# Handle client connections and requests for latest data
@socketio.on('get_latest_data')
def handle_latest_data(data):
    cup_id = data['cup_id']
    print(f"Client requesting latest data for cup: {cup_id}")
    
    try:
        # Get latest reading from database
        conn = sqlite3.connect('water_quality.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ph, tds, temperature, salinity, cleanliness_score
            FROM sensor_readings
            WHERE cup_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (cup_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            print(f"Found data for {cup_id}: {result}")
            emit('sensor_update', {
                'cup_id': cup_id,
                'ph': result[0],
                'tds': result[1],
                'temperature': result[2],
                'salinity': result[3],
                'cleanliness_score': result[4]
            })
        else:
            print(f"No data found for {cup_id}, sending defaults")
            # Send default values if no data found
            emit('sensor_update', {
                'cup_id': cup_id,
                'ph': 7.0,
                'tds': 0.0,
                'temperature': 25.0,
                'salinity': 0.0,
                'cleanliness_score': 85
            })
    except Exception as e:
        print(f"Error handling latest data request: {e}")
        # Send default values on error
        emit('sensor_update', {
            'cup_id': cup_id,
            'ph': 7.0,
            'tds': 0.0,
            'temperature': 25.0,
            'salinity': 0.0,
            'cleanliness_score': 85
        })

# Test endpoint to manually send data (for debugging)
@app.route('/test-data/<cup_id>')
def test_data(cup_id):
    """Send test data for debugging"""
    test_sensor_data = {
        'cup_id': cup_id,
        'ph': 7.2,
        'tds': 245,
        'temperature': 23.5,
        'salinity': 0.02,
        'cleanliness_score': 85
    }
    
    # Store in database
    conn = sqlite3.connect('water_quality.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sensor_readings (cup_id, ph, tds, temperature, salinity, cleanliness_score)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (cup_id, 7.2, 245, 23.5, 0.02, 85))
    conn.commit()
    conn.close()
    
    # Send via WebSocket
    socketio.emit('sensor_update', test_sensor_data)
    
    return jsonify({'status': 'success', 'message': f'Test data sent for {cup_id}'})

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5001))
    print(f"Starting SensiCup app on port {port}")
    socketio.run(app, debug=True, host='0.0.0.0', port=port)