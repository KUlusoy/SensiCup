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

# Home page - login with cup code
@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Water Quality Monitor</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 600px; margin: 0 auto; }
            input { padding: 10px; margin: 10px; font-size: 16px; }
            button { padding: 10px 20px; font-size: 16px; background: #007bff; color: white; border: none; cursor: pointer; }
            button:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Water Quality Monitor</h1>
            <p>Enter your cup code to view real-time water quality data:</p>
            <form action="/dashboard" method="POST">
                <input type="text" name="cup_code" placeholder="Enter cup code (e.g., CUP123)" required>
                <button type="submit">Connect to Cup</button>
            </form>
        </div>
    </body>
    </html>
    '''

# Dashboard - shows real-time data
@app.route('/dashboard', methods=['POST'])
def dashboard():
    cup_code = request.form['cup_code']
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard - {cup_code}</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .sensor-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
            .sensor-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff; }}
            .sensor-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
            .status {{ padding: 10px; margin: 10px 0; border-radius: 4px; }}
            .clean {{ background: #d4edda; color: #155724; }}
            .warning {{ background: #fff3cd; color: #856404; }}
            .danger {{ background: #f8d7da; color: #721c24; }}
        </style>
    </head>
    <body>
        <h1>Water Quality Dashboard - {cup_code}</h1>
        
        <div class="status" id="overall-status">
            <strong>Overall Status:</strong> <span id="status-text">Connecting...</span>
        </div>
        
        <div class="sensor-grid">
            <div class="sensor-card">
                <h3>pH Level</h3>
                <div class="sensor-value" id="ph-value">--</div>
                <p>Optimal: 6.5-8.5</p>
            </div>
            
            <div class="sensor-card">
                <h3>TDS (ppm)</h3>
                <div class="sensor-value" id="tds-value">--</div>
                <p>Good: 150-300</p>
            </div>
            
            <div class="sensor-card">
                <h3>Salinity</h3>
                <div class="sensor-value" id="salinity-value">--</div>
                <p>Fresh water: <0.5%</p>
            </div>
            
            <div class="sensor-card">
                <h3>Cleanliness Score</h3>
                <div class="sensor-value" id="cleanliness-value">--</div>
                <p>Scale: 0-100</p>
            </div>
        </div>
        
        <div style="margin-top: 30px;">
            <h3>Live Camera Feed</h3>
            <div style="background: #eee; padding: 20px; text-align: center; border-radius: 8px;">
                <p>Camera feed will appear here</p>
                <p>(Connect your OpenMV camera to Raspberry Pi)</p>
            </div>
        </div>
        
        <script>
            const socket = io();
            
            socket.on('sensor_update', function(data) {{
                if (data.cup_id === '{cup_code}') {{
                    document.getElementById('ph-value').textContent = data.ph || '--';
                    document.getElementById('tds-value').textContent = data.tds || '--';
                    document.getElementById('salinity-value').textContent = data.salinity || '--';
                    document.getElementById('cleanliness-value').textContent = data.cleanliness_score || '--';
                    
                    // Update overall status
                    let status = 'clean';
                    let statusText = 'Water Quality: Good';
                    
                    if (data.cleanliness_score < 50) {{
                        status = 'danger';
                        statusText = 'Water Quality: Poor - Do Not Drink';
                    }} else if (data.cleanliness_score < 75) {{
                        status = 'warning';
                        statusText = 'Water Quality: Fair - Use Caution';
                    }}
                    
                    const statusElement = document.getElementById('overall-status');
                    statusElement.className = 'status ' + status;
                    document.getElementById('status-text').textContent = statusText;
                }}
            }});
            
            // Request initial data
            socket.emit('get_latest_data', {{cup_id: '{cup_code}'}});
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