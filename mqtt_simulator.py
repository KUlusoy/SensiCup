import paho.mqtt.client as mqtt
import json
import time
import random

# MQTT Configuration
MQTT_BROKER = "localhost"  # Your Mosquitto broker
MQTT_PORT = 1883
MQTT_TOPIC_BASE = "sensicup/sensors/"

# Cup configurations for testing
CUPS = ["CUP123", "CUP456", "CUP789"]

def simulate_sensors():
    """Generate simulated sensor readings"""
    return {
        'ph': round(random.uniform(6.0, 8.5), 2),
        'tds': round(random.uniform(100, 400), 1),
        'salinity': round(random.uniform(0.01, 0.1), 3),
        'cleanliness_score': round(random.uniform(60, 95), 1),
        'temperature': round(random.uniform(18, 25), 1),  # Extra sensor
        'timestamp': time.time()
    }

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✓ Connected to MQTT Broker!")
    else:
        print(f"✗ Failed to connect, return code {rc}")

def on_disconnect(client, userdata, rc):
    print("📡 Disconnected from MQTT Broker")

def main():
    print("🚀 Starting MQTT Sensor Simulator...")
    print(f"📡 Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"🔧 Simulating cups: {CUPS}")
    
    # Create MQTT client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    
    try:
        # Connect to broker
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        
        print("📊 Starting sensor simulation...")
        print("Press Ctrl+C to stop")
        
        while True:
            for cup_id in CUPS:
                # Generate sensor data
                sensor_data = simulate_sensors()
                
                # Create topic for this cup
                topic = f"{MQTT_TOPIC_BASE}{cup_id}"
                
                # Publish data
                result = client.publish(topic, json.dumps(sensor_data))
                
                if result.rc == 0:
                    print(f"📤 Sent data for {cup_id}: pH={sensor_data['ph']}, "
                          f"TDS={sensor_data['tds']}, Salinity={sensor_data['salinity']}")
                else:
                    print(f"❌ Failed to send data for {cup_id}")
                
                # Wait a bit between cups
                time.sleep(1)
            
            # Wait before next round of readings
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping simulator...")
        client.loop_stop()
        client.disconnect()
        print("✅ Simulator stopped")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()