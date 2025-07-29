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
                background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
                min-height: 100vh;
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
                color: #1976d2;
                text-decoration: none;
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
                padding: 0.5rem 1rem;
                border-radius: 20px;
                transition: all 0.3s ease;
            }
            
            .nav-links a:hover {
                background: #1976d2;
                color: white;
            }
            
            .nav-links a.active {
                background: #333;
                color: white;
            }
            
            /* Hero Section */
            .hero {
                height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                text-align: center;
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
                background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 200"><path d="M0,100 C150,200 350,0 500,100 C650,200 850,0 1000,100 L1000,200 L0,200 Z" fill="rgba(25,118,210,0.1)"/></svg>') repeat-x;
                animation: wave 20s infinite linear;
            }
            
            @keyframes wave {
                0% { transform: translateX(0); }
                100% { transform: translateX(-1000px); }
            }
            
            .hero-content {
                max-width: 600px;
                padding: 2rem;
                z-index: 1;
                position: relative;
            }
            
            .hero h1 {
                font-size: 4rem;
                margin-bottom: 1rem;
                font-weight: 700;
                color: #1976d2;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
            }
            
            .hero .tagline {
                font-size: 1.5rem;
                margin-bottom: 3rem;
                color: #666;
                font-weight: 300;
            }
            
            .cta-button {
                background: #1976d2;
                color: white;
                padding: 15px 40px;
                font-size: 1.2rem;
                font-weight: 600;
                border: none;
                border-radius: 50px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                transition: all 0.3s ease;
                box-shadow: 0 10px 30px rgba(25, 118, 210, 0.3);
            }
            
            .cta-button:hover {
                transform: translateY(-3px);
                box-shadow: 0 15px 40px rgba(25, 118, 210, 0.4);
                background: #1565c0;
            }
            
            /* Content Sections */
            .content-section {
                padding: 5rem 2rem;
                max-width: 1200px;
                margin: 0 auto;
            }
            
            .section-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 4rem;
                align-items: center;
                margin-bottom: 5rem;
            }
            
            .section-content h2 {
                font-size: 2.5rem;
                margin-bottom: 1.5rem;
                color: #1976d2;
            }
            
            .section-content p {
                color: #666;
                font-size: 1.1rem;
                line-height: 1.8;
                margin-bottom: 1.5rem;
            }
            
            .prototype-image {
                background: #f5f5f5;
                border-radius: 15px;
                padding: 2rem;
                text-align: center;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            
            .prototype-image img {
                max-width: 100%;
                height: auto;
                border-radius: 10px;
            }
            
            .team-section {
                background: white;
                border-radius: 20px;
                padding: 3rem;
                margin-top: 5rem;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                text-align: center;
            }
            
            .team-section h2 {
                font-size: 2.5rem;
                margin-bottom: 2rem;
                color: #1976d2;
            }
            
            .team-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 2rem;
                margin-top: 2rem;
            }
            
            .team-member {
                text-align: center;
            }
            
            .team-member h4 {
                color: #1976d2;
                margin-bottom: 0.5rem;
            }
            
            .team-member p {
                color: #666;
                font-size: 0.9rem;
            }
            
            /* Footer */
            .footer {
                background: #333;
                color: white;
                text-align: center;
                padding: 2rem;
                margin-top: 5rem;
            }
            
            /* Responsive Design */
            @media (max-width: 768px) {
                .hero h1 {
                    font-size: 2.5rem;
                }
                
                .section-grid {
                    grid-template-columns: 1fr;
                    gap: 2rem;
                }
                
                .nav-links {
                    display: none;
                }
                
                .team-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <!-- Header -->
        <header class="header">
            <nav class="nav">
                <a href="/" class="logo">SensiCup</a>
                <ul class="nav-links">
                    <li><a href="/" class="active">Home</a></li>
                    <li><a href="/your-cup">Your Cup</a></li>
                    <li><a href="/database">Database</a></li>
                    <li><a href="/contact">Contact Us</a></li>
                </ul>
            </nav>
        </header>

        <!-- Hero Section -->
        <section class="hero">
            <div class="hero-content">
                <h1>SensiCup</h1>
                <p class="tagline">A health check for your water.</p>
                <a href="/your-cup" class="cta-button">Enter your cup code now!</a>
            </div>
        </section>

        <!-- Content Section -->
        <div class="content-section">
            <div class="section-grid">
                <div class="section-content">
                    <h2>About SensiCup</h2>
                    <p>SensiCup was designed to be a practical tool for measuring your water's life quality without having to purchase different counterparts or sending water to laboratories.</p>
                </div>
                <div class="prototype-image">
                    <p>Insert Final Prototype Image Here</p>
                </div>
            </div>
            
            <div class="section-grid">
                <div class="prototype-image">
                    <p>Insert Image of Poor Water Pipes from Schools Here</p>
                </div>
                <div class="section-content">
                    <h2>Our Story</h2>
                    <p>After studying in schools with poor water quality, we were determined to take action and measure the water quality in our schools in a friendly and convenient manner. SensiCup provides an affordable</p>
                </div>
            </div>
            
            <div class="team-section">
                <h2>Our Team</h2>
                <p>Insert Group Image Here</p>
                <div class="team-grid">
                    <div class="team-member">
                        <h4>Kubra Ulusoy</h4>
                        <p>Team Lead/Software Engineer</p>
                    </div>
                    <div class="team-member">
                        <h4>Jasmine Algama</h4>
                        <p>Hardware Engineer</p>
                    </div>
                    <div class="team-member">
                        <h4>Samuel Baxter</h4>
                        <p>Software/Hardware Engineer</p>
                    </div>
                    <div class="team-member">
                        <h4>Nafrin Neha</h4>
                        <p>3D CAD Designer</p>
                    </div>
                    <div class="team-member">
                        <h4>Stephanie Yang</h4>
                        <p>Software Engineer</p>
                    </div>
                </div>
                <p style="margin-top: 2rem; font-style: italic;">Body text for whatever you'd like to add more to the subheading.</p>
            </div>
        </div>

        <!-- Footer -->
        <footer class="footer">
            <p>&copy; 2025 SensiCup. All rights reserved.</p>
        </footer>
    </body>
    </html>
    '''

# Your Cup page - updated with info popups
@app.route('/your-cup')
def your_cup():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your Cup - SensiCup</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #f8f9fa;
                min-height: 100vh;
                padding-top: 80px;
            }
            
            /* Header */
            .header {
                position: fixed;
                top: 0;
                width: 100%;
                background: white;
                padding: 1rem 2rem;
                z-index: 1000;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
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
                color: #333;
                text-decoration: none;
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
                padding: 0.5rem 1rem;
                border-radius: 20px;
                transition: all 0.3s ease;
            }
            
            .nav-links a:hover {
                background: #333;
                color: white;
            }
            
            .nav-links a.active {
                background: #333;
                color: white;
            }
            
            /* Main Content */
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 3rem 2rem;
                text-align: center;
            }
            
            .page-title {
                font-size: 3rem;
                margin-bottom: 2rem;
                color: #333;
            }
            
            .cup-code-section {
                background: white;
                border-radius: 15px;
                padding: 3rem;
                margin-bottom: 3rem;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            
            .cup-code-input {
                padding: 15px 30px;
                font-size: 1.2rem;
                border: 2px solid #ddd;
                border-radius: 50px;
                width: 300px;
                margin-bottom: 2rem;
                outline: none;
                transition: border-color 0.3s ease;
            }
            
            .cup-code-input:focus {
                border-color: #1976d2;
            }
            
            .connect-btn {
                background: #1976d2;
                color: white;
                padding: 15px 40px;
                font-size: 1.2rem;
                border: none;
                border-radius: 50px;
                cursor: pointer;
                margin-top: 1rem;
                transition: all 0.3s ease;
            }
            
            .connect-btn:hover {
                background: #1565c0;
                transform: translateY(-2px);
            }
            
            /* Hidden content that shows after entering cup code */
            .hidden-content {
                display: none;
                animation: fadeIn 0.5s ease-in;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .status-section {
                margin: 3rem 0;
            }
            
            .status-text {
                font-size: 2rem;
                margin-bottom: 1rem;
                color: #333;
            }
            
            .status-bar {
                height: 30px;
                background: linear-gradient(to right, #ff4444, #ffaa00, #00aa00);
                border-radius: 15px;
                margin: 0 auto;
                width: 300px;
                position: relative;
            }
            
            .status-indicator {
                position: absolute;
                top: -5px;
                width: 0;
                height: 0;
                border-left: 10px solid transparent;
                border-right: 10px solid transparent;
                border-top: 20px solid #333;
                left: 75%;
                transform: translateX(-50%);
            }
            
            /* Cup Diagram Section */
            .diagram-section {
                background: white;
                border-radius: 15px;
                padding: 3rem;
                margin: 3rem 0;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            
            .diagram-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 3rem;
                align-items: center;
            }
            
            .cup-diagram {
                text-align: center;
            }
            
            .cup-diagram img {
                max-width: 100%;
                height: auto;
                border-radius: 10px;
            }
            
            .sensor-info {
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }
            
            .sensor-card {
                background: #1976d2;
                color: white;
                padding: 1rem 2rem;
                border-radius: 10px;
                text-align: left;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.3s ease;
                position: relative;
            }
            
            .sensor-card:hover {
                background: #1565c0;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(25, 118, 210, 0.3);
            }
            
            .sensor-card::after {
                content: '📊 Click for more info';
                position: absolute;
                right: 10px;
                top: 50%;
                transform: translateY(-50%);
                font-size: 0.8rem;
                opacity: 0.7;
            }
            
            /* Live Feed Section */
            .live-feed-section {
                background: white;
                border-radius: 15px;
                padding: 3rem;
                margin: 3rem 0;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            
            .live-feed-title {
                font-size: 2rem;
                margin-bottom: 2rem;
                color: #333;
            }
            
            .feed-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 3rem;
                align-items: center;
            }
            
            .camera-feed {
                background: #f0f0f0;
                border-radius: 50%;
                width: 300px;
                height: 300px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #666;
                margin: 0 auto;
                border: 3px solid #ddd;
            }
            
            .particles-section {
                text-align: center;
            }
            
            .particles-title {
                font-size: 1.5rem;
                margin-bottom: 1rem;
                color: #333;
            }
            
            .particles-display {
                background: #f0f0f0;
                border-radius: 10px;
                padding: 2rem;
                color: #666;
                min-height: 200px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            /* Modal Styles */
            .modal {
                display: none;
                position: fixed;
                z-index: 2000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.5);
                animation: modalFadeIn 0.3s ease;
            }
            
            @keyframes modalFadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            .modal-content {
                background-color: #fefefe;
                margin: 5% auto;
                padding: 0;
                border-radius: 15px;
                width: 90%;
                max-width: 800px;
                max-height: 80vh;
                overflow-y: auto;
                animation: modalSlideIn 0.3s ease;
                box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            }
            
            @keyframes modalSlideIn {
                from { transform: translateY(-50px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
            
            .modal-header {
                background: #1976d2;
                color: white;
                padding: 2rem;
                border-radius: 15px 15px 0 0;
            }
            
            .modal-title {
                font-size: 2rem;
                margin: 0;
            }
            
            .modal-body {
                padding: 2rem;
                line-height: 1.6;
            }
            
            .modal-body h3 {
                color: #333;
                margin-bottom: 1rem;
            }
            
            .modal-body p {
                color: #666;
                margin-bottom: 1rem;
            }
            
            .info-table {
                width: 100%;
                border-collapse: collapse;
                margin: 1rem 0;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            
            .info-table th,
            .info-table td {
                padding: 1rem;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            
            .info-table th {
                background: #1976d2;
                color: white;
                font-weight: 600;
            }
            
            .info-table tr:last-child td {
                border-bottom: none;
            }
            
            .close {
                position: absolute;
                right: 20px;
                top: 20px;
                color: white;
                font-size: 28px;
                font-weight: bold;
                cursor: pointer;
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                background: rgba(255,255,255,0.2);
                transition: background 0.3s ease;
            }
            
            .close:hover {
                background: rgba(255,255,255,0.3);
            }
            
            .citation {
                font-size: 0.9rem;
                color: #888;
                font-style: italic;
                margin-top: 1rem;
                padding: 1rem;
                background: #f9f9f9;
                border-radius: 8px;
                border-left: 4px solid #1976d2;
            }
            
            /* Footer */
            .footer {
                background: #333;
                color: white;
                text-align: center;
                padding: 2rem;
                margin-top: 5rem;
            }
            
            .footer-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 2rem;
                max-width: 1200px;
                margin: 0 auto;
            }
            
            .footer-section h4 {
                margin-bottom: 1rem;
            }
            
            .footer-section p {
                color: #ccc;
                font-size: 0.9rem;
            }
            
            .footer-section h5 a {
                color: #BEBEBE;
                text-decoration: none;
                font-weight: thin;
            }
            
            .footer-section h5 a:hover {
                text-decoration: underline;
                color: #B5D5F4;
                font-weight: thin;
            }
            
            /* Responsive Design */
            @media (max-width: 768px) {
                .diagram-grid,
                .feed-grid {
                    grid-template-columns: 1fr;
                    gap: 2rem;
                }
                
                .nav-links {
                    display: none;
                }
                
                .page-title {
                    font-size: 2rem;
                }
                
                .cup-code-input {
                    width: 100%;
                    max-width: 300px;
                }
                
                .camera-feed {
                    width: 250px;
                    height: 250px;
                }
                
                .footer-grid {
                    grid-template-columns: 1fr;
                }
                
                .modal-content {
                    width: 95%;
                    margin: 10% auto;
                }
                
                .sensor-card::after {
                    display: none;
                }
            }
        </style>
    </head>
    <body>
        <!-- Header -->
        <header class="header">
            <nav class="nav">
                <a href="/" class="logo">SensiCup</a>
                <ul class="nav-links">
                    <li><a href="/">Home</a></li>
                    <li><a href="/your-cup" class="active">Your Cup</a></li>
                    <li><a href="/database">Database</a></li>
                    <li><a href="/contact">Contact Us</a></li>
                </ul>
            </nav>
        </header>

        <div class="container">
            <h1 class="page-title">Enter Your Cup Code Here:</h1>
            
            <div class="cup-code-section">
                <input type="text" id="cup_code" class="cup-code-input" placeholder="Cup Code" required>
                <br>
                <button type="button" class="connect-btn" onclick="connectToCup()">Connect</button>
            </div>
            
            <!-- Hidden content that appears after entering cup code -->
            <div id="hidden-content" class="hidden-content">
                <div class="status-section">
                    <p class="status-text">Your water is <span id="water-status">Good</span></p>
                    <div class="status-bar">
                        <div class="status-indicator"></div>
                    </div>
                </div>
                
                <div class="diagram-section">
                    <div class="diagram-grid">
                        <div class="cup-diagram">
                            <div style="background: #f0f0f0; min-height: 400px; width: 100%; display: flex; align-items: center; justify-content: center; border-radius: 10px;">
                                <img src="/static/SensiCup_Final_Sketch.png" alt="SensiCup Sketch" ... />                            </div>
                        </div>
                        <div class="sensor-info">
                            <div class="sensor-card" onclick="openModal('ph-modal')">pH Level: <span id="ph-display">7.2</span></div>
                            <div class="sensor-card" onclick="openModal('tds-modal')">TDS Level: <span id="tds-display">245 ppm</span></div>
                            <div class="sensor-card" onclick="openModal('salinity-modal')">Salinity Level: <span id="salinity-display">0.02%</span></div>
                        </div>
                    </div>
                </div>
                
                <div class="live-feed-section">
                    <h2 class="live-feed-title">Water Image in Real Time</h2>
                    <div class="feed-grid">
                        <div class="camera-feed">
                            <img id="live-video" src="/video_feed" alt="Live Water Feed" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" />
                        </div>
                        <div class="particles-section">
                            <h3 class="particles-title">Particles Found</h3>
                            <div class="particles-display">
                                <div>
                                    <p>✅ No harmful particles detected</p>
                                    <p>🔬 Cleanliness Score: <span id="cleanliness-display">85</span>/100</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- pH Modal -->
        <div id="ph-modal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <span class="close" onclick="closeModal('ph-modal')">&times;</span>
                    <h2 class="modal-title">What Does My Water's pH Level Mean?</h2>
                </div>
                <div class="modal-body">
                    <p>In simple terms, pH level in water indicates how acidic or basic (also called alkaline) the water is. It is a scale from 0 to 14, where 7 is neutral. A pH below 7 is acidic, and a pH above 7 is basic. While a pH of around 6.5 to 8.5 is often considered safe for drinking water, extreme pH levels can affect taste and potentially cause corrosion or scaling in pipes. Please check the chart given to see if the pH level is outside the range of safe drinking water for reference.</p>
                    
                    <table class="info-table">
                        <thead>
                            <tr>
                                <th>pH Range</th>
                                <th>Water Quality</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td>0 - 6.4</td><td>Acidic (Poor)</td></tr>
                            <tr><td>6.5 - 8.5</td><td>Safe (Good)</td></tr>
                            <tr><td>8.6 - 14</td><td>Basic (Poor)</td></tr>
                        </tbody>
                    </table>
                    
                    <div class="citation">
                        Vanstone, Emma. "What Is the pH Scale?" Science Experiments for Kids, 16 Oct. 2023, www.science-sparks.com/what-is-the-ph-scale.
                    </div>
                </div>
            </div>
        </div>

        <!-- TDS Modal -->
        <div id="tds-modal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <span class="close" onclick="closeModal('tds-modal')">&times;</span>
                    <h2 class="modal-title">What Does My Water's TDS Level Mean?</h2>
                </div>
                <div class="modal-body">
                    <p>TDS (Total Dissolved Solids) will help measure your water quality by seeing the total amount of dissolved materials you can drink and materials you cannot such as salts, minerals, metals, etc. If your TDS level is under 300 milligrams per liter, then your water quality is excellent and most of the dissolved materials you have in your water is consumable! Please check the graph to see if the TDS level is your water is above 300 milligrams per liter for reference.</p>
                    
                    <table class="info-table">
                        <thead>
                            <tr>
                                <th>Level of TDS (milligrams per litre)</th>
                                <th>Rating</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td>Less than 300</td><td>Excellent</td></tr>
                            <tr><td>300 - 600</td><td>Good</td></tr>
                            <tr><td>600 - 900</td><td>Fair</td></tr>
                            <tr><td>900 - 1,200</td><td>Poor</td></tr>
                            <tr><td>Above 1,200</td><td>Unacceptable</td></tr>
                        </tbody>
                    </table>
                    
                    <div class="citation">
                        "Taste of Water with Different TDS Concentrations," https://cdn.who.int/media/docs/default-source/wash-documents/wash-chemicals/tds.pdf?sfvrsn=3e6d651e_4
                    </div>
                </div>
            </div>
        </div>

        <!-- Salinity Modal -->
        <div id="salinity-modal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <span class="close" onclick="closeModal('salinity-modal')">&times;</span>
                    <h2 class="modal-title">What Does My Water's Salinity Level Mean?</h2>
                </div>
                <div class="modal-body">
                    <p>Salinity levels in your water measure how much salt there is in your water. This will help you understand how much salinity can influence the drinking water you have as it strongly contributes to the content of the water you drink. If the salinity level in your water is 600 milligrams per liter or less, then your water quality is excellent with low salinity and you can drink it! For the higher salinity levels, the least likely it is healthy for you to drink it. Please check the chart given to see if the salinity level is higher than 600 milligrams per liter for reference.</p>
                    
                    <table class="info-table">
                        <thead>
                            <tr>
                                <th>Salinity (mg/L)</th>
                                <th>Quality</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td>0 - 600</td><td>Good</td></tr>
                            <tr><td>600 - 900</td><td>Fair</td></tr>
                            <tr><td>900 - 1,200</td><td>Poor</td></tr>
                            <tr><td>> 1,200</td><td>Unacceptable (unpalatable)</td></tr>
                        </tbody>
                    </table>
                    
                    <div class="citation">
                        "River Water Salinity Impact on Drinking Water Treatment Plant Performance Using Artificial Neural Network." Journal of Engineering, vol. 25, no. 8, July 2019, pp. 149–59. https://doi.org/10.31026/j.eng.2019.08.10.
                    </div>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <footer class="footer">
            <div class="footer-grid">
                <div class="footer-section">
                    <h4>SensiCup</h4>
                    <h5><a href="/">Home</a></h5>
                    <h5><a href="/contact">Contact Us</a></h5>
                </div>
                <div class="footer-section">
                    <h4>Information</h4>
                    <h5><a href="/your-cup">Your Cup</a></h5>
                    <h5><a href="/database">Database</a></h5>
                </div>
            </div>
        </footer>

        <script>
            function connectToCup() {
                const cupCode = document.getElementById('cup_code').value.trim();
                
                if (!cupCode) {
                    alert('Please enter a cup code');
                    return;
                }
                
                // Show the hidden content with animation
                const hiddenContent = document.getElementById('hidden-content');
                hiddenContent.style.display = 'block';
                
                // Scroll to the revealed content
                setTimeout(() => {
                    hiddenContent.scrollIntoView({ 
                        behavior: 'smooth',
                        block: 'start'
                    });
                }, 100);
                
                // Update status based on cup code
                updateStatusBasedOnCupCode(cupCode);
            }
            
            function updateStatusBasedOnCupCode(cupCode) {
                // Hardcoded values for demo - you can customize this
                let status = 'Good';
                let ph = '7.2';
                let tds = '245 ppm';
                let salinity = '0.02%';
                let cleanliness = '85';
                
                // Example: different values for different cup codes
                if (cupCode.toUpperCase() === 'CUP123') {
                    status = 'Excellent';
                    ph = '7.4';
                    tds = '220 ppm';
                    salinity = '0.01%';
                    cleanliness = '92';
                } else if (cupCode.toUpperCase() === 'CUP456') {
                    status = 'Fair';
                    ph = '6.8';
                    tds = '350 ppm';
                    salinity = '0.05%';
                    cleanliness = '68';
                } else if (cupCode.toUpperCase() === 'CUP789') {
                    status = 'Poor';
                    ph = '5.9';
                    tds = '450 ppm';
                    salinity = '0.08%';
                    cleanliness = '42';
                }
                
                // Update the display
                document.getElementById('water-status').textContent = status;
                document.getElementById('ph-display').textContent = ph;
                document.getElementById('tds-display').textContent = tds;
                document.getElementById('salinity-display').textContent = salinity;
                document.getElementById('cleanliness-display').textContent = cleanliness;
            }
            
            // Modal functions
            function openModal(modalId) {
                document.getElementById(modalId).style.display = 'block';
                document.body.style.overflow = 'hidden'; // Prevent background scrolling
            }
            
            function closeModal(modalId) {
                document.getElementById(modalId).style.display = 'none';
                document.body.style.overflow = 'auto'; // Restore scrolling
            }
            
            // Close modal when clicking outside of it
            window.onclick = function(event) {
                const modals = document.querySelectorAll('.modal');
                modals.forEach(modal => {
                    if (event.target === modal) {
                        modal.style.display = 'none';
                        document.body.style.overflow = 'auto';
                    }
                });
            }
            
            // Allow Enter key to connect
            document.getElementById('cup_code').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    connectToCup();
                }
            });
            
            // Close modal with Escape key
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    const openModal = document.querySelector('.modal[style*="block"]');
                    if (openModal) {
                        openModal.style.display = 'none';
                        document.body.style.overflow = 'auto';
                    }
                }
            });
        </script>
    </body>
    </html>
    '''

# Database page - updated with "Database Section" instead of "Related Products"
@app.route('/database')
def database():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Database - SensiCup</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #f8f9fa;
                min-height: 100vh;
                padding-top: 80px;
            }
            
            /* Header */
            .header {
                position: fixed;
                top: 0;
                width: 100%;
                background: white;
                padding: 1rem 2rem;
                z-index: 1000;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
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
                color: #333;
                text-decoration: none;
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
                padding: 0.5rem 1rem;
                border-radius: 20px;
                transition: all 0.3s ease;
            }
            
            .nav-links a:hover {
                background: #333;
                color: white;
            }
            
            .nav-links a.active {
                background: #333;
                color: white;
            }
            
            /* Main Content */
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 3rem 2rem;
            }
            
            .upload-section {
                background: white;
                border-radius: 15px;
                padding: 3rem;
                margin-bottom: 3rem;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 3rem;
                align-items: center;
            }
            
            .upload-area {
                background: #f0f0f0;
                border: 2px dashed #ccc;
                border-radius: 15px;
                padding: 3rem;
                text-align: center;
                color: #666;
                min-height: 300px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .upload-content h2 {
                font-size: 2rem;
                margin-bottom: 1rem;
                color: #333;
            }
            
            .upload-content p {
                color: #666;
                line-height: 1.6;
                margin-bottom: 2rem;
            }
            
            .upload-form {
                margin-top: 2rem;
            }
            
            .upload-form input[type="text"] {
                width: 100%;
                padding: 15px;
                border: 2px solid #ddd;
                border-radius: 10px;
                font-size: 1rem;
                margin-bottom: 1rem;
                outline: none;
                transition: border-color 0.3s ease;
            }
            
            .upload-form input[type="text"]:focus {
                border-color: #1976d2;
            }
            
            .submit-btn {
                width: 100%;
                background: #333;
                color: white;
                padding: 15px;
                border: none;
                border-radius: 10px;
                font-size: 1rem;
                cursor: pointer;
                transition: background 0.3s ease;
            }
            
            .submit-btn:hover {
                background: #555;
            }
            
            .disclaimer {
                font-size: 0.9rem;
                color: #666;
                margin-top: 1rem;
                font-style: italic;
            }
            
            /* Database Section */
            .database-section {
                margin-top: 4rem;
            }
            
            .database-section h2 {
                font-size: 2rem;
                margin-bottom: 2rem;
                color: #333;
            }
            
            .database-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 2rem;
            }
            
            .database-card {
                background: white;
                border-radius: 15px;
                padding: 2rem;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                text-align: center;
            }
            
            .database-image {
                background: #f0f0f0;
                height: 200px;
                border-radius: 10px;
                margin-bottom: 1rem;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #666;
            }
            
            .database-card h3 {
                margin-bottom: 0.5rem;
                color: #333;
            }
            
            .database-card p {
                color: #666;
                font-size: 0.9rem;
            }
            
            /* Footer */
            .footer {
                background: #333;
                color: white;
                text-align: center;
                padding: 2rem;
                margin-top: 5rem;
            }
            
            .footer-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 2rem;
                max-width: 1200px;
                margin: 0 auto;
            }
            
            .footer-section h4 {
                margin-bottom: 1rem;
            }
            
            .footer-section p {
                color: #ccc;
                font-size: 0.9rem;
            }
            
            .footer-section h5 a {
                color: #BEBEBE;
                text-decoration: none;
                font-weight: thin;
            }
            
            .footer-section h5 a:hover {
                text-decoration: underline;
                color: #B5D5F4;
                font-weight: thin;
            }
            
            /* Responsive Design */
            @media (max-width: 768px) {
                .upload-section {
                    grid-template-columns: 1fr;
                    gap: 2rem;
                }
                
                .nav-links {
                    display: none;
                }
                
                .database-grid {
                    grid-template-columns: 1fr;
                }
                
                .footer-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <!-- Header -->
        <header class="header">
            <nav class="nav">
                <a href="/" class="logo">SensiCup</a>
                <ul class="nav-links">
                    <li><a href="/">Home</a></li>
                    <li><a href="/your-cup">Your Cup</a></li>
                    <li><a href="/database" class="active">Database</a></li>
                    <li><a href="/contact">Contact Us</a></li>
                </ul>
            </nav>
        </header>

        <div class="container">
            <div class="upload-section">
                <div class="upload-area">
                    Upload area placeholder
                </div>
                <div class="upload-content">
                    <h2>Upload photos from your SensiCup!</h2>
                    <p>Currently, datasets that label bacteria in the water to monitor water quality are scarce. By adding your photos, you can contribute to crowdsourcing and creating collections of photos for others to download, which is helpful to make machine learning models better or the science community in general.</p>
                    
                    <form class="upload-form" action="/submit-photo" method="POST">
                        <input type="text" placeholder="Add a description" name="description" required>
                        <button type="submit" class="submit-btn">Submit Photos</button>
                    </form>
                    
                    <p class="disclaimer">(Please do not upload any private information and we are not liable for any information disclosure.)</p>
                </div>
            </div>
            
            <div class="database-section">
                <h2>Database Section</h2>
                <div class="database-grid">
                    <div class="database-card">
                        <div class="database-image">Database Image</div>
                        <h3>____'s Database</h3>
                        <p>Small Description</p>
                        <p><strong>(Anything else)</strong></p>
                    </div>
                    <div class="database-card">
                        <div class="database-image">Database Image</div>
                        <h3>____'s Database</h3>
                        <p>Small Description</p>
                        <p><strong>(Anything else)</strong></p>
                    </div>
                    <div class="database-card">
                        <div class="database-image">Database Image</div>
                        <h3>____'s Database</h3>
                        <p>Small Description</p>
                        <p><strong>(Anything else)</strong></p>
                    </div>
                    <div class="database-card">
                        <div class="database-image">Database Image</div>
                        <h3>____'s Database</h3>
                        <p>Small Description</p>
                        <p><strong>(Anything else)</strong></p>
                    </div>
                    <div class="database-card">
                        <div class="database-image">Database Image</div>
                        <h3>____'s Database</h3>
                        <p>Small Description</p>
                        <p><strong>(Anything else)</strong></p>
                    </div>
                    <div class="database-card">
                        <div class="database-image">Database Image</div>
                        <h3>____'s Database</h3>
                        <p>Small Description</p>
                        <p><strong>(Anything else)</strong></p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <footer class="footer">
            <div class="footer-grid">
                <div class="footer-section">
                    <h4>SensiCup</h4>
                    <h5><a href="/">Home</a></h5>
                    <h5><a href="/contact">Contact Us</a></h5>
                </div>
                <div class="footer-section">
                    <h4>Information</h4>
                    <h5><a href="/your-cup">Your Cup</a></h5>
                    <h5><a href="/database">Database</a></h5>
                </div>
            </div>
        </footer>
    </body>
    </html>
    '''

# Contact page - updated design with working email functionality
@app.route('/contact')
def contact():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Contact Us - SensiCup</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #f8f9fa;
                min-height: 100vh;
                padding-top: 80px;
            }
            
            /* Header */
            .header {
                position: fixed;
                top: 0;
                width: 100%;
                background: white;
                padding: 1rem 2rem;
                z-index: 1000;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
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
                color: #333;
                text-decoration: none;
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
                padding: 0.5rem 1rem;
                border-radius: 20px;
                transition: all 0.3s ease;
            }
            
            .nav-links a:hover {
                background: #333;
                color: white;
            }
            
            .nav-links a.active {
                background: #333;
                color: white;
            }
            
            /* Main Content */
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 3rem 2rem;
            }
            
            .page-title {
                font-size: 3rem;
                margin-bottom: 3rem;
                color: #333;
            }
            
            .contact-section {
                background: white;
                border-radius: 15px;
                padding: 3rem;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 4rem;
                align-items: start;
            }
            
            .contact-info h3 {
                color: #666;
                margin-bottom: 2rem;
                line-height: 1.6;
            }
            
            .contact-form {
                display: flex;
                flex-direction: column;
                gap: 1.5rem;
            }
            
            .form-group {
                display: flex;
                flex-direction: column;
            }
            
            .form-group label {
                margin-bottom: 0.5rem;
                color: #333;
                font-weight: 500;
            }
            
            .form-group input,
            .form-group textarea {
                padding: 15px;
                border: 2px solid #ddd;
                border-radius: 10px;
                font-size: 1rem;
                outline: none;
                transition: border-color 0.3s ease;
                font-family: inherit;
            }
            
            .form-group input:focus,
            .form-group textarea:focus {
                border-color: #1976d2;
            }
            
            .form-group textarea {
                min-height: 120px;
                resize: vertical;
            }
            
            .submit-btn {
                background: #333;
                color: white;
                padding: 15px 30px;
                border: none;
                border-radius: 10px;
                font-size: 1rem;
                cursor: pointer;
                transition: background 0.3s ease;
                margin-top: 1rem;
            }
            
            .submit-btn:hover {
                background: #555;
            }
            
            .logo-section {
                background: #999;
                border-radius: 15px;
                height: 400px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 1.2rem;
            }
            
            /* Footer */
            .footer {
                background: #333;
                color: white;
                text-align: center;
                padding: 2rem;
                margin-top: 5rem;
            }
            
            .footer-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 2rem;
                max-width: 1200px;
                margin: 0 auto;
            }
            
            .footer-section h4 {
                margin-bottom: 1rem;
            }
            
            .footer-section p {
                color: #ccc;
                font-size: 0.9rem;
            }
            
            .footer-section h5 a {
                color: #BEBEBE;
                text-decoration: none;
                font-weight: thin;
            }
            
            .footer-section h5 a:hover {
                text-decoration: underline;
                color: #B5D5F4;
                font-weight: thin;
            }
            
            /* Success/Error Messages */
            .message {
                padding: 1rem;
                border-radius: 10px;
                margin-bottom: 2rem;
                text-align: center;
            }
            
            .message.success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            
            .message.error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            
            /* Responsive Design */
            @media (max-width: 768px) {
                .contact-section {
                    grid-template-columns: 1fr;
                    gap: 2rem;
                }
                
                .nav-links {
                    display: none;
                }
                
                .page-title {
                    font-size: 2rem;
                }
                
                .footer-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <!-- Header -->
        <header class="header">
            <nav class="nav">
                <a href="/" class="logo">SensiCup</a>
                <ul class="nav-links">
                    <li><a href="/">Home</a></li>
                    <li><a href="/your-cup">Your Cup</a></li>
                    <li><a href="/database">Database</a></li>
                    <li><a href="/contact" class="active">Contact Us</a></li>
                </ul>
            </nav>
        </header>

        <div class="container">
            <h1 class="page-title">Contact Us</h1>
            
            <div class="contact-section">
                <div class="contact-info">
                    <h3>Have any questions or comments? We would love to get in contact! Please use the contact us form below for us to receive your message.</h3>
                    
                    <form class="contact-form" action="/send-contact" method="POST">
                        <div class="form-group">
                            <label for="first_name">First name</label>
                            <input type="text" id="first_name" name="first_name" placeholder="Jane" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="last_name">Last name</label>
                            <input type="text" id="last_name" name="last_name" placeholder="Smitherton" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="email">Email address</label>
                            <input type="email" id="email" name="email" placeholder="email@janesfakedomain.net" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="message">Your message</label>
                            <textarea id="message" name="message" placeholder="Enter your question or message" required></textarea>
                        </div>
                        
                        <button type="submit" class="submit-btn">Submit</button>
                    </form>
                </div>
                
            <div class="logo-section">
                <img src="/static/SensiCup_Logo.jpg" alt="SensiCup Logo" style="max-width: 80%; max-height: 80%; border-radius: 15px;" />            </div>
            </div>
        </div>

        <!-- Footer -->
        <footer class="footer">
            <div class="footer-grid">
                <div class="footer-section">
                    <h4>SensiCup</h4>
                    <h5><a href="/">Home</a></h5>
                    <h5><a href="/contact">Contact Us</a></h5>
                </div>
                <div class="footer-section">
                    <h4>Information</h4>
                    <h5><a href="/your-cup">Your Cup</a></h5>
                    <h5><a href="/database">Database</a></h5>
                </div>
            </div>
        </footer>
    </body>
    </html>
    '''

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