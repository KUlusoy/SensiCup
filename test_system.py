# test_system.py - Test the complete system
import requests
import json
import time
import random

def test_ml_model():
    """Test the ML model directly"""
    print("🧪 Testing ML Model...")
    try:
        from water_quality_model import WaterQualityPredictor
        
        predictor = WaterQualityPredictor()
        
        # Try to load model, train if needed
        if not predictor.load_model():
            print("Training new model...")
            predictor.train_model()
            predictor.save_model()
        
        # Test with sample data
        test_data = {
            "ph": 7.2,
            "tds": 245,
            "temperature": 23.5,
            "salinity": 0.02
        }
        
        result = predictor.process_sensor_data(test_data)
        
        if result:
            print(f"✅ ML Model Test Passed!")
            print(f"   Input: pH={test_data['ph']}, TDS={test_data['tds']}, Temp={test_data['temperature']}, Salinity={test_data['salinity']}")
            print(f"   Output: Cleanliness Score = {result['cleanliness_score']}/100")
            return True
        else:
            print("❌ ML Model Test Failed!")
            return False
            
    except Exception as e:
        print(f"❌ ML Model Error: {e}")
        return False

def test_flask_api():
    """Test the Flask API endpoints"""
    print("\n🌐 Testing Flask API...")
    
    try:
        # Test basic connection
        response = requests.get("http://localhost:5004/", timeout=5)
        if response.status_code == 200:
            print("✅ Flask app is running!")
        else:
            print(f"⚠️  Flask app responded with status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Flask app is not running! Start it first with: python sensicup_app.py")
        return False
    except Exception as e:
        print(f"❌ Flask API Error: {e}")
        return False
    
    # Test sensor data API
    try:
        test_sensor_data = {
            "cup_id": "TEST_CUP_API",
            "ph": 7.4,
            "tds": 180,
            "temperature": 21.0,
            "salinity": 0.01
        }
        
        response = requests.post(
            "http://localhost:5004/api/sensor-data", 
            json=test_sensor_data,
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Sensor data API test passed!")
            print(f"   Sent: {test_sensor_data}")
            print(f"   Response: {result.get('status')}")
            return True
        else:
            print(f"❌ Sensor data API failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Sensor data API Error: {e}")
        return False

def test_ml_prediction_api():
    """Test the ML prediction API endpoint"""
    print("\n🤖 Testing ML Prediction API...")
    
    try:
        test_data = {
            "cup_id": "TEST_ML_API",
            "ph": 6.8,
            "tds": 320,
            "temperature": 26.0,
            "salinity": 0.05
        }
        
        response = requests.post(
            "http://localhost:5004/api/predict-cleanliness",
            json=test_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            prediction = result.get('prediction', {})
            print("✅ ML Prediction API test passed!")
            print(f"   Input: pH={test_data['ph']}, TDS={test_data['tds']}")
            print(f"   Predicted Score: {prediction.get('cleanliness_score')}/100")
            print(f"   Quality Level: {prediction.get('quality_level')}")
            print(f"   Color Zone: {prediction.get('color_zone')}")
            return True
        else:
            print(f"❌ ML Prediction API failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ ML Prediction API Error: {e}")
        return False

def send_realistic_test_data():
    """Send several realistic test cases to see the system in action"""
    print("\n🎯 Sending Realistic Test Data...")
    
    test_cases = [
        {"name": "Excellent Water", "ph": 7.2, "tds": 150, "temperature": 22.0, "salinity": 0.01},
        {"name": "Good Tap Water", "ph": 7.6, "tds": 250, "temperature": 24.0, "salinity": 0.02},
        {"name": "Fair Quality", "ph": 6.8, "tds": 380, "temperature": 26.5, "salinity": 0.06},
        {"name": "Poor Quality", "ph": 5.9, "tds": 550, "temperature": 29.0, "salinity": 0.12},
        {"name": "Very Basic Water", "ph": 9.1, "tds": 420, "temperature": 31.0, "salinity": 0.08}
    ]
    
    for i, case in enumerate(test_cases):
        try:
            test_data = {
                "cup_id": f"REALISTIC_TEST_{i+1}",
                "ph": case["ph"],
                "tds": case["tds"],
                "temperature": case["temperature"],
                "salinity": case["salinity"]
            }
            
            response = requests.post(
                "http://localhost:5004/api/sensor-data",
                json=test_data,
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"✅ {case['name']}: Sent successfully")
            else:
                print(f"❌ {case['name']}: Failed to send")
                
            time.sleep(2)  # Wait 2 seconds between requests
            
        except Exception as e:
            print(f"❌ Error sending {case['name']}: {e}")

def main():
    print("="*60)
    print("🧪 SENSICUP SYSTEM COMPREHENSIVE TEST")
    print("="*60)
    
    # Test 1: ML Model
    ml_test = test_ml_model()
    
    # Test 2: Flask API
    flask_test = test_flask_api()
    
    # Test 3: ML Prediction API (only if Flask is running)
    ml_api_test = False
    if flask_test:
        ml_api_test = test_ml_prediction_api()
    
    # Test 4: Send realistic data (only if API is working)
    if flask_test:
        send_realistic_test_data()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"🤖 ML Model: {'✅ PASS' if ml_test else '❌ FAIL'}")
    print(f"🌐 Flask API: {'✅ PASS' if flask_test else '❌ FAIL'}")
    print(f"🔮 ML Prediction API: {'✅ PASS' if ml_api_test else '❌ FAIL'}")
    
    if ml_test and flask_test and ml_api_test:
        print("\n🎉 ALL TESTS PASSED! Your system is ready!")
        print("🌐 Visit http://localhost:5004/your-cup to see it in action!")
        print("🤖 Start continuous monitoring with: python continuous_monitoring.py")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        if not flask_test:
            print("💡 Make sure to start your Flask app first: python sensicup_app.py")

if __name__ == "__main__":
    main()