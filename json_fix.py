# json_fix.py - Quick fix for numpy JSON serialization issues
import numpy as np
import json

def convert_numpy_types(data):
    """Convert numpy types to regular Python types for JSON serialization"""
    if isinstance(data, dict):
        return {key: convert_numpy_types(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_numpy_types(item) for item in data]
    elif isinstance(data, (np.float32, np.float64)):
        return float(data)
    elif isinstance(data, (np.int32, np.int64)):
        return int(data)
    elif isinstance(data, np.ndarray):
        return data.tolist()
    else:
        return data

def test_json_conversion():
    """Test the JSON conversion with numpy types"""
    # Create test data with numpy types
    test_data = {
        'cup_id': 'TEST_001',
        'ph': np.float32(7.2),
        'tds': np.float32(245.0),
        'temperature': np.float32(23.5),
        'salinity': np.float32(0.02),
        'cleanliness_score': np.float32(85.5)
    }
    
    print("Original data types:")
    for key, value in test_data.items():
        print(f"  {key}: {value} (type: {type(value)})")
    
    print("\nConverting numpy types...")
    clean_data = convert_numpy_types(test_data)
    
    print("Converted data types:")
    for key, value in clean_data.items():
        print(f"  {key}: {value} (type: {type(value)})")
    
    print("\nTesting JSON serialization...")
    try:
        json_string = json.dumps(clean_data)
        print("✅ JSON serialization successful!")
        print(f"JSON: {json_string}")
        return True
    except Exception as e:
        print(f"❌ JSON serialization failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Testing JSON Serialization Fix")
    print("=" * 50)
    test_json_conversion()
    
    print("\n💡 This fix has been applied to your continuous_monitoring.py")
    print("📝 The updated files should now handle numpy types correctly!")