#sensicup_app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response, send_from_directory, send_file
from flask_socketio import SocketIO, emit
import sqlite3
import json
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import cv2
import logging
import requests
import threading
import time
import zipfile
import io
import shutil

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Create static folder if it doesn't exist
if not os.path.exists('static'):
    os.makedirs('static')

socketio = SocketIO(app)

# Email configuration
EMAIL_ADDRESS = "sensicupteam@gmail.com"
EMAIL_PASSWORD = "rbie ebnn phut acnd"  # Use app password, not regular password

# Initialize database with proper schema
def init_db():
    conn = sqlite3.connect('water_quality.db')
    cursor = conn.cursor()
    
    # Create the uploads directory if it doesn't exist
    UPLOAD_FOLDER = 'uploads'
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        print(f"Created upload directory: {UPLOAD_FOLDER}")
    
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
    
    # Create a table for user databases
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_databases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            date_created DATE DEFAULT CURRENT_DATE
        )
    ''')
    
    # Create a new table to store paths for photos associated with each database
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS database_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            database_id INTEGER,
            file_path TEXT NOT NULL,
            FOREIGN KEY (database_id) REFERENCES user_databases(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

# Define the directory to store uploaded files
app.config['UPLOAD_FOLDER'] = 'uploads'

def fetch_sensicup_snapshot():
    """Fetch a single snapshot from Raspberry Pi stream and save as static/sensicup.jpg"""
    SNAPSHOT_URL = "http://10.83.4.104:8081/get_snapshot"
    try:
        response = requests.get(SNAPSHOT_URL, timeout=10)  # Increased timeout
        if response.status_code == 200:
            save_path = os.path.join('static', 'sensicup.jpg')  # Simplified path
            with open(save_path, "wb") as f:
                f.write(response.content)
            print(f"✅ Snapshot saved to {save_path} ({len(response.content)} bytes)")
            return True
        else:
            print(f"❌ Error: Received status code {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Error fetching snapshot: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def snapshot_loop():
    """Continuously fetch snapshots every 2 seconds"""
    consecutive_failures = 0
    max_failures = 10
    
    while True:
        try:
            if fetch_sensicup_snapshot():
                consecutive_failures = 0  # Reset failure counter on success
                time.sleep(2)
            else:
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    print(f"⚠️ Too many consecutive failures ({consecutive_failures}), waiting longer...")
                    time.sleep(10)  # Wait longer after repeated failures
                else:
                    time.sleep(5)  # Wait a bit longer on failure
        except Exception as e:
            print(f"❌ Error in snapshot loop: {e}")
            time.sleep(5)

def gen_frames():
    """Generate frames from Raspberry Pi camera stream"""
    import cv2

    # Raspberry Pi's IP and stream URL
    PI_STREAM_URL = "http://10.83.4.104:8081/get_snapshot"

    # Connect to the Raspberry Pi's MJPEG stream
    cap = cv2.VideoCapture(PI_STREAM_URL)

    if not cap.isOpened():
        print(f"Error: Could not connect to Raspberry Pi camera stream at {PI_STREAM_URL}")
        return

    frame_count = 0
    while True:
        success, frame = cap.read()
        if not success:
            print("Error: Could not read frame from Raspberry Pi stream.")
            break

        try:
            # Process every other frame to reduce load
            frame_count += 1
            if frame_count % 2 == 0:
                continue

            # Resize to save bandwidth
            frame = cv2.resize(frame, (320, 240))

            # Encode frame as JPEG (lower quality = faster streaming)
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            ret, buffer = cv2.imencode('.jpg', frame, encode_param)
            if not ret:
                print("Error: Could not encode frame.")
                continue

            frame_bytes = buffer.tobytes()
            # Save to file as static/sensicup.jpg
            with open("static/sensicup.jpg", "wb") as f:
                f.write(frame_bytes)

        except Exception as e:
            print(f"Error processing frame: {e}")
            break

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

# Add this function to handle ML-generated scores
def update_cleanliness_with_ml(cup_id, ph, tds, temperature, salinity):
    """
    This function can be called when new sensor data arrives
    to update the cleanliness score using the ML model
    """
    try:
        # Try to import and use the ML model
        from water_quality_model import WaterQualityPredictor
        
        # Create predictor and load model
        predictor = WaterQualityPredictor()
        if predictor.load_model():
            # Create sensor data dict
            sensor_data = {
                'ph': ph,
                'tds': tds,
                'temperature': temperature,
                'salinity': salinity
            }
            
            # Get ML prediction
            result = predictor.process_sensor_data(sensor_data)
            
            if result:
                ml_score = result['cleanliness_score']
                print(f"🤖 ML Model predicted cleanliness score: {ml_score}")
                return ml_score
            else:
                print("⚠️ ML model failed to predict, using fallback calculation")
                return calculate_fallback_score(ph, tds, salinity)
        else:
            print("⚠️ ML model not available, using fallback calculation")
            return calculate_fallback_score(ph, tds, salinity)
            
    except ImportError:
        print("⚠️ ML model files not found, using fallback calculation") 
        return calculate_fallback_score(ph, tds, salinity)
    except Exception as e:
        print(f"❌ Error using ML model: {e}, using fallback calculation")
        return calculate_fallback_score(ph, tds, salinity)

def calculate_fallback_score(ph, tds, salinity):
    """
    Updated fallback calculation with same strict thresholds
    """
    score = 0
    
    # pH scoring (45 points max - higher weight in fallback)
    if 6.8 <= ph <= 8.2:
        score += 45
    elif 6.5 <= ph < 6.8 or 8.2 < ph <= 8.5:
        score += 35
    elif 6.0 <= ph < 6.5 or 8.5 < ph <= 9.0:
        score += 20
    elif 5.5 <= ph < 6.0 or 9.0 < ph <= 9.5:
        score += 8
    else:
        score += 0
        
    # TDS scoring (40 points max)
    if 50 <= tds <= 150:
        score += 40
    elif 150 < tds <= 250:
        score += 32
    elif tds < 50:
        score += 25
    elif 250 < tds <= 400:
        score += 15
    elif 400 < tds <= 600:
        score += 6
    else:  # >600 - dirty water
        score += 0
        
    # Salinity scoring (15 points max)
    if salinity < 0.3:
        score += 15
    elif salinity < 0.8:
        score += 10
    elif salinity < 1.5:
        score += 6
    elif salinity < 3.0:
        score += 3
    else:
        score += 0
    
    return min(score, 100)

# Serve static files (especially images)
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

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

@app.route('/database')
def database():
    conn = sqlite3.connect('water_quality.db')
    cursor = conn.cursor()
    
    # Query for all databases, also getting the path of the first photo for the cover
    cursor.execute('''
        SELECT 
            ud.id, 
            ud.name, 
            ud.description, 
            ud.date_created,
            (SELECT file_path FROM database_photos WHERE database_id = ud.id ORDER BY id ASC LIMIT 1) as first_photo,
            (SELECT COUNT(*) FROM database_photos WHERE database_id = ud.id) as photo_count
        FROM user_databases ud
        ORDER BY ud.date_created DESC
    ''')
    
    databases = []
    for row in cursor.fetchall():
        databases.append({
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'date_created': row[3],
            'first_photo_path': row[4] if row[4] else None, # Pass the path or None if no photos
            'photo_count': row[5]
        })

    conn.close()
    return render_template('database.html', databases=databases)

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

# Handle database creation and photo submission
@app.route('/submit-photo', methods=['POST'])
def submit_photo():
    try:
        database_name = request.form['database_name']
        description = request.form['description']
        photos = request.files.getlist('photos')
        
        if not photos or len(photos) == 0 or not database_name or not description:
            return '''... (error message)'''
        
        conn = sqlite3.connect('water_quality.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_databases (name, description)
            VALUES (?, ?)
        ''', (database_name, description))
        
        database_id = cursor.lastrowid
        db_upload_path = os.path.join(app.config['UPLOAD_FOLDER'], str(database_id))
        if not os.path.exists(db_upload_path):
            os.makedirs(db_upload_path)

        for photo in photos:
            if photo.filename != '':
                filename = photo.filename
                file_path = os.path.join(db_upload_path, filename)
                photo.save(file_path)
                
                cursor.execute('''
                    INSERT INTO database_photos (database_id, file_path)
                    VALUES (?, ?)
                ''', (database_id, file_path))
        
        conn.commit()
        conn.close()
        
        return '''
        <div style="text-align: center; padding: 5rem; font-family: 'Segoe UI', sans-serif;">
            <h1 style="color: #4CAF50; margin-bottom: 2rem;">✅ Database Created Successfully!</h1>
            <p style="font-size: 1.2rem; margin-bottom: 2rem;">Your database has been created with {} photos!</p>
            <a href="/database" style="background: #1976d2; color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px;">Back to Database</a>
        </div>
        '''.format(len(photos))
        
    except Exception as e:
        return f'''... (error message)'''

# Handle database deletion
@app.route('/delete-database', methods=['POST'])
def delete_database():
    try:
        database_id = request.form['database_id']
        
        conn = sqlite3.connect('water_quality.db')
        cursor = conn.cursor()
        
        db_upload_path = os.path.join(app.config['UPLOAD_FOLDER'], str(database_id))
        
        cursor.execute('DELETE FROM user_databases WHERE id = ?', (database_id,))
        conn.commit()
        conn.close()
        
        if os.path.exists(db_upload_path):
            shutil.rmtree(db_upload_path)
        
        return redirect('/database')
        
    except Exception as e:
        print(f"Error deleting database: {e}")
        return redirect('/database')
    
# Handle database download
@app.route('/download_database/<int:database_id>')
def download_database(database_id):
    conn = sqlite3.connect('water_quality.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT name FROM user_databases WHERE id = ?', (database_id,))
    db_name = cursor.fetchone()[0]
    cursor.execute('SELECT file_path FROM database_photos WHERE database_id = ?', (database_id,))
    photo_paths = [row[0] for row in cursor.fetchall()]
    conn.close()

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for photo_path in photo_paths:
            zipf.write(photo_path, os.path.basename(photo_path))
    memory_file.seek(0)
    
    return send_file(memory_file, 
                     download_name=f"{db_name}.zip",
                     as_attachment=True,
                     mimetype='application/zip')

# New route to serve images from the uploads folder
@app.route('/display_photo/<path:filename>')
def display_photo(filename):
    return send_file(filename)

# New route to get all photo paths for a specific database as JSON
@app.route('/get_photos/<int:database_id>')
def get_photos(database_id):
    conn = sqlite3.connect('water_quality.db')
    cursor = conn.cursor()
    cursor.execute('SELECT file_path FROM database_photos WHERE database_id = ?', (database_id,))
    photos = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(photos)

# Update your existing API endpoint
@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.json
        print(f"Received raw data: {data}")
        
        # Extract sensor values with fallback defaults
        cup_id = data.get('cup_id', 'UNKNOWN')
        ph = float(data.get('ph', 7.0))
        tds = float(data.get('tds', 0.0))
        temperature = float(data.get('temperature', 25.0))
        salinity = float(data.get('salinity', 0.0))
        
        # Try to get cleanliness score from the request first
        cleanliness_score = data.get('cleanliness_score')
        
        # If no cleanliness score provided, calculate it
        if cleanliness_score is None:
            print("🤖 No cleanliness score provided, generating with ML model...")
            cleanliness_score = update_cleanliness_with_ml(cup_id, ph, tds, temperature, salinity)
        else:
            cleanliness_score = float(cleanliness_score)
            print(f"✅ Using provided cleanliness score: {cleanliness_score}")
        
        print(f"Final processed sensor data:")
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
            'data': sensor_data,
            'ml_generated': cleanliness_score != data.get('cleanliness_score')
        }), 200
        
    except Exception as e:
        print(f"Error processing sensor data: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': str(e)
        }), 400

# Add a new endpoint to manually trigger ML prediction
@app.route('/api/predict-cleanliness', methods=['POST'])
def predict_cleanliness():
    """Manual endpoint to get ML prediction for given sensor values"""
    try:
        data = request.json
        
        ph = float(data.get('ph', 7.0))
        tds = float(data.get('tds', 200.0))
        temperature = float(data.get('temperature', 25.0))
        salinity = float(data.get('salinity', 0.5))
        cup_id = data.get('cup_id', 'MANUAL_TEST')
        
        # Get ML prediction
        ml_score = update_cleanliness_with_ml(cup_id, ph, tds, temperature, salinity)
        
        result = {
            'cup_id': cup_id,
            'ph': ph,
            'tds': tds,
            'temperature': temperature,
            'salinity': salinity,
            'cleanliness_score': ml_score,
            'prediction_method': 'ML_MODEL',
            'timestamp': datetime.now().isoformat()
        }
        
        # Determine quality level for display
        if ml_score >= 85:
            quality_level = "Excellent"
            color_zone = "green"
        elif ml_score >= 70:
            quality_level = "Very Good"
            color_zone = "light-green"
        elif ml_score >= 55:
            quality_level = "Good"
            color_zone = "yellow"
        elif ml_score >= 40:
            quality_level = "Fair"
            color_zone = "orange"
        else:
            quality_level = "Poor"
            color_zone = "red"
        
        result['quality_level'] = quality_level
        result['color_zone'] = color_zone
        
        return jsonify({
            'status': 'success',
            'prediction': result
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    
# Add a test route to generate sample data with ML scores
@app.route('/test-ml/<cup_id>')
def test_ml_data(cup_id):
    """Generate test data and get ML prediction"""
    import random
    
    # Generate random but realistic sensor values
    ph = round(random.uniform(6.0, 8.5), 1)
    tds = round(random.uniform(100, 400), 0)
    temperature = round(random.uniform(18, 30), 1)
    salinity = round(random.uniform(0.01, 0.1), 3)
    
    # Get ML prediction
    ml_score = update_cleanliness_with_ml(cup_id, ph, tds, temperature, salinity)
    
    test_data = {
        'cup_id': cup_id,
        'ph': ph,
        'tds': tds,
        'temperature': temperature,
        'salinity': salinity,
        'cleanliness_score': ml_score
    }
    
    # Store in database
    conn = sqlite3.connect('water_quality.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sensor_readings (cup_id, ph, tds, temperature, salinity, cleanliness_score)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (cup_id, ph, tds, temperature, salinity, ml_score))
    conn.commit()
    conn.close()
    
    # Send via WebSocket
    socketio.emit('sensor_update', test_data)
    
    return jsonify({
        'status': 'success', 
        'message': f'ML test data generated for {cup_id}',
        'data': test_data
    })

# Add logging configuration for better debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sensicup.log'),
        logging.StreamHandler()
    ]
)

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
    # Initialize database
    init_db()
    
    # Try to initialize ML model
    try:
        from water_quality_model import WaterQualityPredictor
        predictor = WaterQualityPredictor()
        if predictor.load_model():
            print("✅ ML model loaded successfully!")
        else:
            print("⚠️ ML model not found, will train on first use")
    except ImportError:
        print("⚠️ ML model files not available, using fallback calculations")
    except Exception as e:
        print(f"⚠️ ML model initialization error: {e}")

    # Start snapshot loop in a separate thread
    print("🚀 Starting camera snapshot thread...")
    threading.Thread(target=snapshot_loop, daemon=True).start()

    port = int(os.environ.get('PORT', 5004))
    print(f"🚀 Starting SensiCup app on port {port}")
    print(f"🤖 ML-powered cleanliness scoring enabled!")
    print(f"🌐 Access your app at: http://localhost:{port}")
    print(f"📷 Camera feed will be available at: /static/sensicup.jpg")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=port)