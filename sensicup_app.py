from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit
import sqlite3
import json
from datetime import datetime
import cv2 # Import OpenCV

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app)

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
    conn.commit()
    conn.close()

# --- Camera Stream Functions ---
# This generator function captures frames from the webcam
# and encodes them as JPEG images to be streamed.
def gen_frames():
    # Use 0 for default webcam. If you have multiple, try 1, 2, etc.
    cap = cv2.VideoCapture(0)
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


# Home page - modern landing page design
@app.route('/')
def home():
    # This route also returns a hardcoded HTML string.
    # For consistency and best practice, you might consider moving this
    # into a template file as well (e.g., templates/index.html)
    # and returning render_template('index.html').
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SensiCup - Smart Water Quality Monitor</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                overflow-x: hidden;
            }
            
            /* Header */
            .header {
                position: fixed;
                top: 0;
                width: 100%;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 1rem 2rem;
                z-index: 1000;
                box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1);
            }
            
            .nav {
                display: flex;
                justify-content: space-between;
                align-items: center;
                max-width: 1200px;
                margin: 0 auto;
            }
            
            .logo {
                font-size: 1.5rem;
                font-weight: bold;
                color: #2c5aa0;
            }
            
            .nav-links {
                display: flex;
                list-style: none;
                gap: 2rem;
            }
            
            .nav-links a {
                text-decoration: none;
                color: #333;
                font-weight: 500;
                transition: color 0.3s ease;
            }
            
            .nav-links a:hover {
                color: #2c5aa0;
            }
            
            /* Hero Section */
            .hero {
                height: 100vh;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                text-align: center;
                color: white;
                position: relative;
                overflow: hidden;
            }
            
            .hero::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 200"><path d="M0,100 C150,200 350,0 500,100 C650,200 850,0 1000,100 L1000,200 L0,200 Z" fill="rgba(255,255,255,0.1)"/></svg>') repeat-x;
                animation: wave 20s infinite linear;
            }
            
            @keyframes wave {
                0% { transform: translateX(0); }
                100% { transform: translateX(-1000px); }
            }
            
            .hero-content {
                max-width: 800px;
                padding: 2rem;
                z-index: 1;
                position: relative;
            }
            
            .hero h1 {
                font-size: 3.5rem;
                margin-bottom: 1rem;
                font-weight: 700;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            
            .hero p {
                font-size: 1.25rem;
                margin-bottom: 2rem;
                opacity: 0.9;
            }
            
            .cta-form {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                padding: 2rem;
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                max-width: 400px;
                margin: 0 auto;
            }
            
            .cta-form input {
                width: 100%;
                padding: 15px;
                border: none;
                border-radius: 50px;
                font-size: 1rem;
                margin-bottom: 1rem;
                outline: none;
                background: rgba(255, 255, 255, 0.9);
            }
            
            .cta-form button {
                width: 100%;
                padding: 15px;
                background: linear-gradient(135deg, #ff6b6b, #ee5a52);
                color: white;
                border: none;
                border-radius: 50px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            
            .cta-form button:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 30px rgba(238, 90, 82, 0.4);
            }
            
            /* About Section */
            .about {
                padding: 5rem 2rem;
                background: #f8f9fa;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            
            .about-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 4rem;
                align-items: center;
            }
            
            .about-content h2 {
                font-size: 2.5rem;
                margin-bottom: 1rem;
                color: #2c5aa0;
            }
            
            .about-content p {
                color: #666;
                font-size: 1.1rem;
                line-height: 1.8;
            }
            
            .about-image {
                background: #ddd;
                height: 300px;
                border-radius: 15px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #888;
                font-size: 1.1rem;
            }
            
            /* Story Section */
            .story {
                padding: 5rem 2rem;
                background: white;
            }
            
            .story-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 4rem;
                align-items: center;
            }
            
            .story-image {
                background: #ddd;
                height: 300px;
                border-radius: 15px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #888;
                font-size: 1.1rem;
            }
            
            .story-content h2 {
                font-size: 2.5rem;
                margin-bottom: 1rem;
                color: #2c5aa0;
            }
            
            .story-content p {
                color: #666;
                font-size: 1.1rem;
                line-height: 1.8;
            }
            
            /* Team Section */
            .team {
                padding: 5rem 2rem;
                background: #f8f9fa;
            }
            
            .team h2 {
                text-align: center;
                font-size: 2.5rem;
                margin-bottom: 3rem;
                color: #2c5aa0;
            }
            
            .team-image {
                background: #ddd;
                height: 400px;
                border-radius: 15px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #888;
                font-size: 1.1rem;
                margin-bottom: 2rem;
            }
            
            .team-info {
                text-align: center;
                color: #666;
                line-height: 1.6;
            }
            
            /* Responsive Design */
            @media (max-width: 768px) {
                .hero h1 {
                    font-size: 2.5rem;
                }
                
                .about-grid,
                .story-grid {
                    grid-template-columns: 1fr;
                    gap: 2rem;
                }
                
                .nav-links {
                    display: none;
                }
                
                .hero {
                    padding: 2rem 1rem;
                }
                
                .about, .story, .team {
                    padding: 3rem 1rem;
                }
            }
        </style>
    </head>
    <body>
        <header class="header">
            <nav class="nav">
                <div class="logo">SensiCup</div>
                <ul class="nav-links">
                    <li><a href="#home">Home</a></li>
                    <li><a href="#about">About</a></li>
                    <li><a href="#story">Story</a></li>
                    <li><a href="#team">Team</a></li>
                </ul>
            </nav>
        </header>

        <section id="home" class="hero">
            <div class="hero-content">
                <h1>SensiCup</h1>
                <p>Smart Water Quality Monitoring</p>
                <form class="cta-form" action="/dashboard" method="POST">
                    <input type="text" name="cup_code" placeholder="Enter your cup code here" required>
                    <button type="submit">Connect to Your Cup</button>
                </form>
            </div>
        </section>

        <section id="about" class="about">
            <div class="container">
                <div class="about-grid">
                    <div class="about-content">
                        <h2>About SensiCup</h2>
                        <p>SensiCup brings you the perfect blend of cutting-edge technology and everyday convenience. Our smart water monitoring system provides real-time insights into your water quality, ensuring you always know what you're drinking. With advanced sensors and intelligent analysis, SensiCup delivers professional-grade water testing right in your hands.</p>
                    </div>
                    <div class="about-image">
                        Smart Cup Prototype Image Here
                    </div>
                </div>
            </div>
        </section>

        <section id="story" class="story">
            <div class="container">
                <div class="story-grid">
                    <div class="story-image">
                        Smart Badge of Your Water Here from SensiCup
                    </div>
                </div>
            </div>
        </section>

        <section id="team" class="team">
            <div class="container">
                <h2>Our Team</h2>
                <div class="team-image">
                    Smart Group Image Here
                </div>
                <div class="team-info">
                    <p><strong>Kubra Ulusoy:</strong> Team Lead/Software Engineer, <strong>Jasmine Algama:</strong> Hardware Engineer, <strong>Samuel Baxter:</strong> Hardware Engineer, <strong>Nafrin Neha:</strong> 3D CAD Designer, and <strong>Stephanie Yang:</strong> Software Engineer </p>
                    <br>
                    <p><em>The SensiCup</em></p>
                </div>
            </div>
        </section>
    </body>
    </html>
    '''

# Enhanced Dashboard with modern design
@app.route('/dashboard', methods=['POST'])
def dashboard():
    cup_code = request.form['cup_code']
    # Use render_template to serve the dashboard.html file
    return render_template('dashboard.html', cup_code=cup_code)


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
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, debug=False, host='0.0.0.0', port=port)
