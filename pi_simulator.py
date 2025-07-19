import requests
import json
import time
import random

# Configuration
WEB_APP_URL = "http://localhost:5000"  # Your web app URL
CUP_ID = "CUP123"  # Your cup's unique identifier

def read_ph_sensor():
    """Simulate reading pH sensor"""
    return round(random.uniform(6.0, 8.0), 2)

def read_tds_sensor():
    """Simulate reading TDS sensor"""
    return round(random.uniform(100, 400), 1)

def read_salinity_sensor():
    """Simulate reading salinity sensor"""
    return round(random.uniform(0.1, 0.8), 2)

def analyze_image():
    """Simulate OpenMV camera analysis"""
    return round(random.uniform(60, 95), 1)

def send_sensor_data():
    """Send all sensor data to web app"""
    try:
        data = {
            'cup_id': CUP_ID,
            'ph': read_ph_sensor(),
            'tds': read_tds_sensor(),
            'salinity': read_salinity_sensor(),
            'cleanliness_score': analyze_image(),
            'timestamp': time.time()
        }
        
        print(f"Sending data: {data}")
        
        response = requests.post(
            f"{WEB_APP_URL}/api/sensor-data",
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            print("✓ Data sent successfully!")
        else:
            print(f"✗ Error sending data: {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error: {e}")

def main():
    print("Starting Water Quality Sensor System...")
    print(f"Cup ID: {CUP_ID}")
    print(f"Web App URL: {WEB_APP_URL}")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            send_sensor_data()
            time.sleep(5)  # Send data every 5 seconds
            
    except KeyboardInterrupt:
        print("\nStopping sensor system...")

if __name__ == "__main__":
    main()