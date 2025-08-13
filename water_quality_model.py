# water_quality_model.py
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import json
import requests
import time
from datetime import datetime

class WaterQualityPredictor:
    def __init__(self):
        self.model = None
        self.is_trained = False
        
    def calculate_quality_score(self, ph, tds, salinity_ppt, temperature):
        """
        Calculate quality score based on thresholds you provided
        Returns score from 0-100 (higher is better)
        """
        score = 0
        
        # pH scoring (30 points max)
        if 6.5 <= ph <= 8.5:  # Safe (Good)
            score += 30
        elif 6.0 <= ph < 6.5 or 8.5 < ph <= 9.0:  # Slightly outside range
            score += 20
        elif 5.5 <= ph < 6.0 or 9.0 < ph <= 9.5:  # More outside range
            score += 10
        else:  # Poor (very acidic or basic)
            score += 0
            
        # TDS scoring (25 points max)
        if 50 <= tds <= 150:  # Excellent
            score += 25
        elif 150 < tds <= 300:  # Good
            score += 20
        elif tds < 50:  # Ultra-pure (might lack minerals)
            score += 15
        elif 300 < tds <= 500:  # Acceptable
            score += 10
        else:  # Potentially unsafe (>500)
            score += 0
            
        # Salinity scoring (25 points max)
        if salinity_ppt < 0.5:  # Fresh
            score += 25
        elif 0.5 <= salinity_ppt < 1.0:  # Marginal
            score += 20
        elif 1.0 <= salinity_ppt < 2.0:  # Brackish
            score += 10
        elif 2.0 <= salinity_ppt < 10.0:  # Saline
            score += 5
        else:  # Highly saline or brine
            score += 0
            
        # Temperature scoring (20 points max)
        # Ideal drinking water temperature is around 15-25°C
        if 15 <= temperature <= 25:  # Ideal range
            score += 20
        elif 10 <= temperature < 15 or 25 < temperature <= 30:  # Good range
            score += 15
        elif 5 <= temperature < 10 or 30 < temperature <= 35:  # Acceptable
            score += 10
        elif 0 <= temperature < 5 or 35 < temperature <= 40:  # Poor
            score += 5
        else:  # Very poor
            score += 0
            
        return min(score, 100)  # Cap at 100
    
    def generate_training_data(self, n_samples=1000):
        """Generate synthetic training data based on real-world patterns"""
        np.random.seed(42)  # For reproducible results
        
        data = []
        for _ in range(n_samples):
            # Generate realistic sensor values
            ph = np.random.normal(7.2, 1.0)  # Normal around neutral
            ph = np.clip(ph, 3.0, 11.0)  # Keep in realistic range
            
            tds = np.random.exponential(200) + 50  # Exponential distribution
            tds = np.clip(tds, 10, 1000)
            
            salinity_ppt = np.random.exponential(0.5)  # Most water is fresh
            salinity_ppt = np.clip(salinity_ppt, 0, 40)
            
            temperature = np.random.normal(22, 8)  # Normal around room temp
            temperature = np.clip(temperature, 0, 50)
            
            # Calculate the target score
            score = self.calculate_quality_score(ph, tds, salinity_ppt, temperature)
            
            # Add some noise to make it more realistic
            score += np.random.normal(0, 2)
            score = np.clip(score, 0, 100)
            
            data.append({
                'ph': ph,
                'tds': tds,
                'salinity_ppt': salinity_ppt,
                'temperature': temperature,
                'cleanliness_score': score
            })
            
        return pd.DataFrame(data)
    
    def train_model(self, data=None):
        """Train the XGBoost model"""
        if data is None:
            print("Generating training data...")
            data = self.generate_training_data(1000)
        
        # Prepare features and target
        features = ['ph', 'tds', 'salinity_ppt', 'temperature']
        X = data[features]
        y = data['cleanliness_score']
        
        # Split the data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Create and train XGBoost model
        self.model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        
        print("Training XGBoost model...")
        self.model.fit(X_train, y_train)
        
        # Evaluate the model
        y_pred = self.model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        print(f"Model trained successfully!")
        print(f"Mean Squared Error: {mse:.2f}")
        print(f"R² Score: {r2:.3f}")
        
        self.is_trained = True
        
        # Show feature importance
        importance = self.model.feature_importances_
        for i, feature in enumerate(features):
            print(f"{feature}: {importance[i]:.3f}")
        
        return self.model
    
    def predict_cleanliness(self, ph, tds, salinity_ppt, temperature):
        """Predict cleanliness score for given sensor values"""
        if not self.is_trained:
            print("Model not trained yet! Training with default data...")
            self.train_model()
        
        # Prepare input
        input_data = np.array([[ph, tds, salinity_ppt, temperature]])
        
        # Make prediction
        score = self.model.predict(input_data)[0]
        
        # Ensure score is between 0-100
        score = np.clip(score, 0, 100)
        
        # Convert numpy float32 to regular Python float for JSON serialization
        return float(round(score, 1))
    
    def save_model(self, filepath='water_quality_model.pkl'):
        """Save the trained model"""
        if self.is_trained:
            joblib.dump(self.model, filepath)
            print(f"Model saved to {filepath}")
        else:
            print("No trained model to save!")
    
    def load_model(self, filepath='water_quality_model.pkl'):
        """Load a trained model"""
        try:
            self.model = joblib.load(filepath)
            self.is_trained = True
            print(f"Model loaded from {filepath}")
            return True
        except FileNotFoundError:
            print(f"Model file {filepath} not found!")
            return False
    
    def process_sensor_data(self, sensor_json):
        """Process sensor data from JSON and return cleanliness score"""
        try:
            # Parse JSON if it's a string
            if isinstance(sensor_json, str):
                data = json.loads(sensor_json)
            else:
                data = sensor_json
            
            # Extract values and convert to regular Python floats
            ph = float(data.get('ph', 7.0))
            tds = float(data.get('tds', 200.0))
            salinity_ppt = float(data.get('salinity', 0.5))  # Assume in ppt
            temperature = float(data.get('temperature', 22.0))
            
            # Predict cleanliness score
            score = self.predict_cleanliness(ph, tds, salinity_ppt, temperature)
            
            return {
                'cleanliness_score': float(score),  # Ensure it's a regular Python float
                'ph': float(ph),
                'tds': float(tds),
                'salinity_ppt': float(salinity_ppt),
                'temperature': float(temperature),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error processing sensor data: {e}")
            return None

def send_to_webapp(data, webapp_url='http://localhost:5004/api/sensor-data'):
    """Send the processed data to your Flask web app"""
    try:
        # Add cup_id if not present
        if 'cup_id' not in data:
            data['cup_id'] = 'ML_GENERATED'
        
        response = requests.post(webapp_url, json=data, timeout=5)
        if response.status_code == 200:
            print(f"✅ Data sent successfully: Score = {data['cleanliness_score']}")
            return True
        else:
            print(f"❌ Failed to send data: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error sending data to webapp: {e}")
        return False

# Example usage and testing
if __name__ == "__main__":
    # Create predictor
    predictor = WaterQualityPredictor()
    
    # Try to load existing model, or train a new one
    if not predictor.load_model():
        print("Training new model...")
        predictor.train_model()
        predictor.save_model()
    
    # Test with sample data
    print("\n" + "="*50)
    print("TESTING THE MODEL")
    print("="*50)
    
    # Test cases
    test_cases = [
        {"ph": 7.2, "tds": 245, "salinity": 0.02, "temperature": 23.5},  # Good water
        {"ph": 5.9, "tds": 450, "salinity": 0.08, "temperature": 28.1},  # Poor water
        {"ph": 7.4, "tds": 180, "salinity": 0.01, "temperature": 20.0},  # Excellent water
        {"ph": 9.2, "tds": 600, "salinity": 1.5, "temperature": 35.0},   # Bad water
    ]
    
    for i, test_data in enumerate(test_cases):
        result = predictor.process_sensor_data(test_data)
        if result:
            print(f"\nTest {i+1}:")
            print(f"Input: pH={test_data['ph']}, TDS={test_data['tds']}, Salinity={test_data['salinity']}, Temp={test_data['temperature']}")
            print(f"Predicted Cleanliness Score: {result['cleanliness_score']}/100")
            
            # Determine quality level
            score = result['cleanliness_score']
            if score >= 80:
                quality = "Excellent (Green)"
            elif score >= 60:
                quality = "Good (Yellow-Green)"
            elif score >= 40:
                quality = "Fair (Yellow)"
            else:
                quality = "Poor (Red)"
            print(f"Quality Level: {quality}")
    
    print(f"\n🎉 Model is ready to use!")
    print(f"💡 Run 'python continuous_monitoring.py' to start continuous monitoring")