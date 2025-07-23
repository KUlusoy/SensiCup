from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import sqlite3
import json
from datetime import datetime

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

# Home page - modern landing page design
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
        <!-- Header -->
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

        <!-- Hero Section -->
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

        <!-- About Section -->
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

        <!-- Story Section -->
        <section id="story" class="story">
            <div class="container">
                <div class="story-grid">
                    <div class="story-image">
                        Smart Badge of Your Water Here from SensiCup
                    </div>
                    <div class="story-content">
                        <h2>Our Story</h2>
                        <p>Born from a passion for clean water and innovative technology, SensiCup was created to democratize water quality testing. We saw a world where people needed better access to water quality information, and we built a solution that puts laboratory-grade analysis in everyone's hands. Our journey started with a simple question: "What if everyone could know their water quality instantly?" Today, SensiCup provides that answer.</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Team Section -->
        <section id="team" class="team">
            <div class="container">
                <h2>Our Team</h2>
                <div class="team-image">
                    Smart Group Image Here
                </div>
                <div class="team-info">
                    <p><strong>Kubra Ulusoy:</strong> Team Lead/Software Engineer, <strong>Jasmine Algama:</strong> Hardware Engineer, <strong>Samuel Baxter:</strong> Hardware Engineer, <strong>Nafrin Neha:</strong> 3D CAD Designer,                          and <strong>Stephanie Yang:</strong> Software Engineer </p>
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
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard - {cup_code}</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 2rem;
            }}
            
            .dashboard-container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            
            .dashboard-header {{
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 2rem;
                margin-bottom: 2rem;
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: white;
                text-align: center;
            }}
            
            .dashboard-header h1 {{
                font-size: 2.5rem;
                margin-bottom: 0.5rem;
            }}
            
            .cup-id {{
                font-size: 1.2rem;
                opacity: 0.8;
            }}
            
            .status-card {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 1.5rem;
                margin-bottom: 2rem;
                border: 1px solid rgba(255, 255, 255, 0.2);
                text-align: center;
            }}
            
            .status-card.clean {{
                background: linear-gradient(135deg, #4CAF50, #45a049);
                color: white;
            }}
            
            .status-card.warning {{
                background: linear-gradient(135deg, #ff9800, #f57c00);
                color: white;
            }}
            
            .status-card.danger {{
                background: linear-gradient(135deg, #f44336, #d32f2f);
                color: white;
            }}
            
            .sensor-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 2rem;
                margin-bottom: 3rem;
            }}
            
            .sensor-card {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 2rem;
                border: 1px solid rgba(255, 255, 255, 0.2);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }}
            
            .sensor-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            }}
            
            .sensor-card h3 {{
                color: #2c5aa0;
                margin-bottom: 1rem;
                font-size: 1.3rem;
            }}
            
            .sensor-value {{
                font-size: 3rem;
                font-weight: bold;
                color: #333;
                margin-bottom: 0.5rem;
            }}
            
            .sensor-info {{
                color: #666;
                font-size: 0.9rem;
            }}
            
            .camera-section {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 2rem;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
            
            .camera-section h3 {{
                color: #2c5aa0;
                margin-bottom: 1rem;
                font-size: 1.5rem;
            }}
            
            .camera-placeholder {{
                background: linear-gradient(135deg, #eee, #ddd);
                height: 300px;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #888;
                font-size: 1.1rem;
                text-align: center;
                border: 2px dashed #ccc;
            }}
            
            .loading-spinner {{
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid rgba(255,255,255,.3);
                border-radius: 50%;
                border-top-color: #fff;
                animation: spin 1s ease-in-out infinite;
            }}
            
            @keyframes spin {{
                to {{ transform: rotate(360deg); }}
            }}
            
            @media (max-width: 768px) {{
                body {{
                    padding: 1rem;
                }}
                
                .dashboard-header h1 {{
                    font-size: 2rem;
                }}
                
                .sensor-grid {{
                    grid-template-columns: 1fr;
                    gap: 1rem;
                }}
                
                .sensor-value {{
                    font-size: 2.5rem;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="dashboard-container">
            <div class="dashboard-header">
                <h1>Water Quality Dashboard</h1>
                <div class="cup-id">Connected to: {cup_code}</div>
            </div>
            
            <div class="status-card" id="overall-status">
                <div class="loading-spinner"></div>
                <strong>Overall Status:</strong> <span id="status-text">Connecting to sensor...</span>
            </div>
            
            <div class="sensor-grid">
                <div class="sensor-card">
                    <h3>pH Level</h3>
                    <div class="sensor-value" id="ph-value">--</div>
                    <div class="sensor-info">Optimal range: 6.5-8.5</div>
                </div>
                
                <div class="sensor-card">
                    <h3>TDS</h3>
                    <div class="sensor-value" id="tds-value">--</div>
                    <div class="sensor-info">Good range: 150-300 ppm</div>
                </div>
                
                <div class="sensor-card">
                    <h3>Salinity</h3>
                    <div class="sensor-value" id="salinity-value">--</div>
                    <div class="sensor-info">Fresh water: &lt;0.5%</div>
                </div>
                
                <div class="sensor-card">
                    <h3>Cleanliness Score</h3>
                    <div class="sensor-value" id="cleanliness-value">--</div>
                    <div class="sensor-info">Scale: 0-100 (higher is better)</div>
                </div>
            </div>
            
            <div class="camera-section">
                <h3>Live Camera Feed</h3>
                <div class="camera-placeholder">
                    <div>
                        <p>📹 Camera feed will appear here</p>
                        <p>(Connect your OpenMV camera to Raspberry Pi)</p>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            const socket = io();
            
            socket.on('sensor_update', function(data) {{
                if (data.cup_id === '{cup_code}') {{
                    // Update sensor values
                    document.getElementById('ph-value').textContent = data.ph ? data.ph.toFixed(1) : '--';
                    document.getElementById('tds-value').textContent = data.tds ? data.tds.toFixed(0) : '--';
                    document.getElementById('salinity-value').textContent = data.salinity ? data.salinity.toFixed(2) + '%' : '--';
                    document.getElementById('cleanliness-value').textContent = data.cleanliness_score ? data.cleanliness_score.toFixed(0) : '--';
                    
                    // Update overall status
                    let status = 'clean';
                    let statusText = '✅ Water Quality: Excellent - Safe to Drink';
                    
                    if (data.cleanliness_score < 50) {{
                        status = 'danger';
                        statusText = '⚠️ Water Quality: Poor - Do Not Drink';
                    }} else if (data.cleanliness_score < 75) {{
                        status = 'warning';
                        statusText = '⚡ Water Quality: Fair - Use Caution';
                    }}
                    
                    const statusElement = document.getElementById('overall-status');
                    statusElement.className = 'status-card ' + status;
                    document.getElementById('status-text').textContent = statusText;
                }}
            }});
            
            // Request initial data
            socket.emit('get_latest_data', {{cup_id: '{cup_code}'}});
            
            // Add some demo data after 2 seconds if no real data comes in
            setTimeout(() => {{
                const currentValues = document.getElementById('ph-value').textContent;
                if (currentValues === '--') {{
                    // Simulate some demo data
                    socket.emit('sensor_update', {{
                        cup_id: '{cup_code}',
                        ph: 7.2,
                        tds: 245,
                        salinity: 0.02,
                        cleanliness_score: 85
                    }});
                }}
            }}, 2000);
        </script>
    </body>
    </html>
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
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, debug=False, host='0.0.0.0', port=port)