# continuous_monitoring.py
import time
import json
import requests
import sqlite3
import numpy as np  # Add this import for numpy type checking
from water_quality_model import WaterQualityPredictor, send_to_webapp
from datetime import datetime
import schedule
import os

class ContinuousMonitor:
    def __init__(self, webapp_url='http://localhost:5004/api/sensor-data'):
        self.predictor = WaterQualityPredictor()
        self.webapp_url = webapp_url
        self.monitoring = False
        
        # Try to load existing model
        if not self.predictor.load_model():
            print("🔄 No existing model found. Training new model...")
            self.predictor.train_model()
            self.predictor.save_model()
            print("✅ New model trained and saved!")
    
    def get_sensor_data_from_db(self, db_path='water_quality.db'):
        """Get the latest sensor data from your Flask app's database"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get the most recent sensor reading
            cursor.execute('''
                SELECT cup_id, ph, tds, temperature, salinity, timestamp
                FROM sensor_readings
                ORDER BY timestamp DESC
                LIMIT 1
            ''')
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'cup_id': result[0],
                    'ph': result[1],
                    'tds': result[2],
                    'temperature': result[3],
                    'salinity': result[4],
                    'timestamp': result[5]
                }
            else:
                print("⚠️  No sensor data found in database")
                return None
                
        except Exception as e:
            print(f"❌ Error reading from database: {e}")
            return None
    
    def get_sensor_data_from_json(self, json_file='sensor_data.json'):
        """Read sensor data from a JSON file"""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            print(f"⚠️  JSON file {json_file} not found")
            return None
        except Exception as e:
            print(f"❌ Error reading JSON file: {e}")
            return None
    
    def process_and_send_data(self, source='database'):
        """Get sensor data, predict cleanliness, and send to webapp"""
        print(f"\n🔍 Checking for new sensor data... ({datetime.now().strftime('%H:%M:%S')})")
        
        # Get sensor data based on source
        if source == 'database':
            raw_data = self.get_sensor_data_from_db()
        elif source == 'json':
            raw_data = self.get_sensor_data_from_json()
        else:
            print(f"❌ Unknown data source: {source}")
            return False
        
        if not raw_data:
            print("⚠️  No sensor data available")
            return False
        
        # Process the data through ML model
        result = self.predictor.process_sensor_data(raw_data)
        
        if result:
            # Add cup_id from original data if available
            if 'cup_id' in raw_data:
                result['cup_id'] = raw_data['cup_id']
            
            # Convert all values to regular Python types (not numpy)
            clean_result = {}
            for key, value in result.items():
                if isinstance(value, (np.float32, np.float64, np.int32, np.int64)):
                    clean_result[key] = float(value) if 'float' in str(type(value)) else int(value)
                else:
                    clean_result[key] = value
            
            print(f"📊 Processed sensor data:")
            print(f"   pH: {clean_result['ph']}")
            print(f"   TDS: {clean_result['tds']} ppm")
            print(f"   Salinity: {clean_result['salinity_ppt']} ppt")
            print(f"   Temperature: {clean_result['temperature']}°C")
            print(f"   🎯 ML Predicted Cleanliness Score: {clean_result['cleanliness_score']}/100")
            
            # Determine arrow position for the web app
            score = clean_result['cleanliness_score']
            if score >= 85:
                position = "green zone"
            elif score >= 70:
                position = "yellow-green zone"
            elif score >= 50:
                position = "yellow zone"
            elif score >= 30:
                position = "orange zone"
            else:
                position = "red zone"
            
            print(f"   📍 Arrow position: {position}")
            
            # Send to webapp
            success = send_to_webapp(clean_result, self.webapp_url)
            return success
        else:
            print("❌ Failed to process sensor data")
            return False
    
    def start_continuous_monitoring(self, interval_seconds=10, source='database'):
        """Start continuous monitoring"""
        self.monitoring = True
        print(f"🚀 Starting continuous monitoring...")
        print(f"📡 Data source: {source}")
        print(f"⏱️  Check interval: {interval_seconds} seconds")
        print(f"🌐 Webapp URL: {self.webapp_url}")
        print(f"Press Ctrl+C to stop monitoring\n")
        
        try:
            while self.monitoring:
                self.process_and_send_data(source)
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print(f"\n🛑 Monitoring stopped by user")
            self.monitoring = False
        except Exception as e:
            print(f"❌ Monitoring error: {e}")
            self.monitoring = False
    
    def schedule_monitoring(self):
        """Schedule monitoring to run at specific times"""
        # Run every 30 seconds
        schedule.every(30).seconds.do(self.process_and_send_data, source='database')
        
        print("📅 Scheduled monitoring started (every 30 seconds)")
        print("Press Ctrl+C to stop...")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Scheduled monitoring stopped")

def create_sample_json():
    """Create a sample JSON file for testing"""
    sample_data = {
        "cup_id": "TEST_CUP_001",
        "ph": 7.2,
        "tds": 245,
        "temperature": 23.5,
        "salinity": 0.02
    }
    
    with open('sensor_data.json', 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    print("📄 Sample JSON file created: sensor_data.json")

def main():
    print("="*60)
    print("🌊 WATER QUALITY CONTINUOUS MONITORING SYSTEM")
    print("="*60)
    
    # Create monitor instance
    monitor = ContinuousMonitor()
    
    print("\nChoose monitoring mode:")
    print("1. Continuous monitoring from database (recommended)")
    print("2. Continuous monitoring from JSON file")
    print("3. One-time test from database")
    print("4. One-time test from JSON file")
    print("5. Create sample JSON file for testing")
    print("6. Scheduled monitoring (every 30 seconds)")
    
    try:
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            interval = input("Enter check interval in seconds (default 10): ").strip()
            interval = int(interval) if interval else 10
            monitor.start_continuous_monitoring(interval, source='database')
            
        elif choice == '2':
            interval = input("Enter check interval in seconds (default 10): ").strip()
            interval = int(interval) if interval else 10
            monitor.start_continuous_monitoring(interval, source='json')
            
        elif choice == '3':
            print("🧪 Running one-time test from database...")
            success = monitor.process_and_send_data(source='database')
            print(f"Result: {'✅ Success' if success else '❌ Failed'}")
            
        elif choice == '4':
            print("🧪 Running one-time test from JSON file...")
            success = monitor.process_and_send_data(source='json')
            print(f"Result: {'✅ Success' if success else '❌ Failed'}")
            
        elif choice == '5':
            create_sample_json()
            
        elif choice == '6':
            monitor.schedule_monitoring()
            
        else:
            print("❌ Invalid choice")
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()