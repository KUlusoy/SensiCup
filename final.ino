/********************************************************************************
 * ESP32 water-quality logger (FIXED VERSION)
 * 
 * This version sends data in the exact format expected by your Flask app
 * FIXES: TDS showing values when unplugged, and proper salinity calculation
 ********************************************************************************/

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <math.h>

/* --------------------- CONFIG --------------------- */
#define ADC_PCF8591
// #define ADC_ADS7830

#ifdef ADC_PCF8591
  const uint8_t ADC_I2C_ADDR = 0x48;
#elif defined(ADC_ADS7830)
  const uint8_t ADC_I2C_ADDR = 0x48;
#endif

const float ADC_VREF = 3.3f;
const int ADC_SAMPLES = 31;
const uint32_t ADC_SAMPLE_DELAY_MS = 40;
float ecVal = 0;

// FIXED: Add threshold for detecting unplugged sensors
const float TDS_VOLTAGE_THRESHOLD = 0.1f;  // Below this voltage, assume sensor unplugged

#define ONE_WIRE_BUS 4
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// WiFi Configuration
const char* WIFI_SSID = "USG-Mobility";
const char* WIFI_PASS = "shadygrove9631";
  
// Server Configuration - FIXED URL TO MATCH YOUR FLASK APP
const char* SERVER_URL = "http://10.83.4.74:5004/api/sensor-data";  // Changed port to 5004

// CUP ID - CHANGE THIS TO MATCH WHAT YOU TYPE ON THE WEBSITE
const char* CUP_ID = "CUP123";  // Change this to whatever cup code you want to use

const uint32_t SEND_INTERVAL_MS = 3000UL;

Preferences prefs;

struct PH_Cal { 
  float slope; float intercept; 
  };
PH_Cal phcal;

/* --------------------- DECLARATIONS --------------------- */
void initADC();
uint8_t readADC_8bit_raw(uint8_t channel);
float readAdcMedianVoltage(uint8_t channel);
int16_t medianFilterInt16(int16_t* arr, int n);
void loadCalibration();
void savePHCalibration(float s, float i);
float voltageToPH(float v);
float tdsFromVoltage(float voltage, float temperatureC);
float calculateCleanliness(float ph, float tds, float temp);
float calculateSalinity(float tds);

/* --------------------- HELPERS --------------------- */
int16_t medianFilterInt16(int16_t* arr, int n) {
  static int16_t buf[128];
  if (n > (int)(sizeof(buf)/sizeof(buf[0]))) return arr[n/2];
  for (int i=0;i<n;i++) buf[i] = arr[i];
  for (int i=1;i<n;i++){
    int16_t v = buf[i];
    int j = i - 1;
    while (j >= 0 && buf[j] > v) { buf[j+1] = buf[j]; j--; }
    buf[j+1] = v;
  }
  return buf[n/2];
}

void initADC() {  
  Wire.begin(21,22);
}

uint8_t readADC_8bit_raw(uint8_t channel) {
  channel = channel & 0x07;
#ifdef ADC_PCF8591
  uint8_t control = 0x40 | (channel & 0x03);
  Wire.beginTransmission(ADC_I2C_ADDR);
  Wire.write(control);
  Wire.endTransmission();
  Wire.requestFrom((int)ADC_I2C_ADDR, 1);
  if (Wire.available()) Wire.read();
  Wire.requestFrom((int)ADC_I2C_ADDR, 1);
  if (Wire.available()) return Wire.read();
  return 0;
#elif defined(ADC_ADS7830)
  uint8_t cmd = 0x84 | ((channel & 0x07) << 4);
  Wire.beginTransmission(ADC_I2C_ADDR);
  Wire.write(cmd);
  Wire.endTransmission();
  Wire.requestFrom((int)ADC_I2C_ADDR, 1);
  if (Wire.available()) return Wire.read();
  return 0;
#else
  #error "No ADC type defined."
#endif
}

float readAdcMedianVoltage(uint8_t channel) {
  static int16_t samples[128];
  if (ADC_SAMPLES > (int)(sizeof(samples)/sizeof(samples[0]))) {
    // invalid config
  }
  for (int i=0;i<ADC_SAMPLES;i++){
    uint8_t raw = readADC_8bit_raw(channel);
    samples[i] = (int16_t)raw;
    delay(ADC_SAMPLE_DELAY_MS);
  }
  int16_t med = medianFilterInt16(samples, ADC_SAMPLES);
  float volts = ((float)med / 255.0f) * ADC_VREF;
  return volts;
}

float voltageToPH(float voltage) {
  return phcal.slope * voltage + phcal.intercept;
}

// FIXED: Better TDS calculation with threshold check
float tdsFromVoltage(float voltage, float temperatureC) {
  // Check if sensor appears to be unplugged (very low voltage)
  if (!isfinite(voltage) || voltage <= TDS_VOLTAGE_THRESHOLD) {
    ecVal = 0.0f;  // Reset EC value too
    Serial.println("TDS sensor appears unplugged (voltage too low)");
    return 0.0f;
  }
  
  float temp = isfinite(temperatureC) ? temperatureC : 25.0f;
  float v = voltage;
  
  // Calculate raw EC from voltage
  float ecRaw = 133.42f * v * v * v - 255.86f * v * v + 857.39f * v;
  ecVal = ecRaw;
  
  if (ecRaw < 0.0f) {
    ecRaw = 0.0f;
    ecVal = 0.0f;
  }
  
  // Temperature compensation
  const float tempCoeff = 0.02f;
  float comp = 1.0f + tempCoeff * (temp - 25.0f);
  if (fabsf(comp) < 1e-6f) comp = 1.0f;
  float ec25 = ecRaw / comp;
  
  // Convert EC to TDS
  const float TDS_FACTOR = 0.5f;
  float tds = ec25 * TDS_FACTOR;
  
  if (!isfinite(tds) || tds < 0.0f) return 0.0f;
  
  return tds;
}

// NEW: Calculate cleanliness score based on water quality parameters
float calculateCleanliness(float ph, float tds, float temp) {
  float score = 100.0f;
  
  // pH penalty (ideal range 6.5-8.5)
  if (ph < 6.5f || ph > 8.5f) {
    float phDiff = (ph < 6.5f) ? (6.5f - ph) : (ph - 8.5f);
    score -= phDiff * 10.0f; // 10 points per pH unit deviation
  }
  
  // TDS penalty (under 300 is excellent, over 600 is concerning)
  if (tds > 300.0f) {
    score -= (tds - 300.0f) * 0.05f; // 5 points per 100 ppm over 300
  }
  
  // Temperature penalty (ideal range 20-25°C)
  if (temp < 15.0f || temp > 30.0f) {
    float tempDiff = (temp < 15.0f) ? (15.0f - temp) : (temp - 30.0f);
    score -= tempDiff * 2.0f; // 2 points per degree deviation
  }
  
  // Ensure score stays within bounds
  if (score < 0.0f) score = 0.0f;
  if (score > 100.0f) score = 100.0f;
  
  return score;
}

// FIXED: Proper salinity calculation from TDS (ppm) to salinity (%)
float calculateSalinity(float tds) {
  // If TDS is 0 or very low, salinity should also be 0
  if (tds <= 0.0f || tds < 10.0f) {
    return 0.0f;
  }
  
  // Convert TDS (ppm) to salinity (%)
  // Standard conversion: Salinity (%) ≈ TDS (ppm) / 10000
  // This gives a more realistic salinity percentage
  // For reference:
  // - Fresh water: < 0.05% (< 500 ppm TDS)
  // - Brackish water: 0.05% - 3% (500 - 30,000 ppm TDS)
  // - Salt water: > 3% (> 30,000 ppm TDS)
  
  float salinity = tds / 10000.0f;  // Convert ppm to percentage
  
  // Cap at reasonable maximum (seawater is ~3.5%)
  if (salinity > 5.0f) salinity = 5.0f;
  
  return salinity;
}

void loadCalibration() {
  prefs.begin("cal", true);
  if (prefs.isKey("ph_slope") && prefs.isKey("ph_intr")) {
    phcal.slope = prefs.getFloat("ph_slope", -5.5f);
    phcal.intercept = prefs.getFloat("ph_intr", 21.0f);
  } else {
    phcal.slope = -5.5f; 
    phcal.intercept = 21.0f;
  }
  prefs.end();
  
  Serial.printf("Loaded pH calibration: slope=%.3f, intercept=%.3f\n", phcal.slope, phcal.intercept);
}

void savePHCalibration(float slope, float intercept) {
  prefs.begin("cal", false);
  prefs.putFloat("ph_slope", slope);
  prefs.putFloat("ph_intr", intercept);
  prefs.end();
  phcal.slope = slope; 
  phcal.intercept = intercept;
}

unsigned long lastSend = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("=== SensiCup ESP32 Starting ===");
  Serial.printf("Cup ID: %s\n", CUP_ID);
  Serial.printf("Server URL: %s\n", SERVER_URL);
  Serial.printf("TDS voltage threshold: %.2fV\n", TDS_VOLTAGE_THRESHOLD);

  Serial.print("WiFi connecting to "); Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(250); Serial.print('.');
  }
  Serial.println();
  Serial.print("IP: "); Serial.println(WiFi.localIP());

  initADC();
  sensors.begin();
  loadCalibration();
  
  Serial.println("Initialization complete. Starting measurements...");
  lastSend = millis() - SEND_INTERVAL_MS;
}

void loop() {
  unsigned long now = millis();
  if (now - lastSend >= SEND_INTERVAL_MS) {
    lastSend = now;

    Serial.println("\n=== Taking Measurements ===");

    // Start DS18B20 conversion
    sensors.requestTemperatures();

    // Sample ADC
    float phVolts = readAdcMedianVoltage(0);
    float tdsVolts = readAdcMedianVoltage(1);

    Serial.printf("Raw voltages: pH=%.3fV, TDS=%.3fV\n", phVolts, tdsVolts);

    float tempC = sensors.getTempCByIndex(0);
    if (tempC == DEVICE_DISCONNECTED_C) {
      tempC = 25.0f; // Use default temperature if sensor disconnected
      Serial.println("Temperature sensor disconnected, using 25.0°C");
    }

    float phValue = voltageToPH(phVolts);
    float tdsValue = tdsFromVoltage(tdsVolts, tempC);
    float cleanlinessScore = calculateCleanliness(phValue, tdsValue, tempC);
    float salinityValue = calculateSalinity(tdsValue);

    Serial.printf("Calculated values:\n");
    Serial.printf("  Temperature: %.1f°C\n", tempC);
    Serial.printf("  pH: %.2f\n", phValue);
    Serial.printf("  TDS: %.1f ppm\n", tdsValue);
    Serial.printf("  Salinity: %.3f%%\n", salinityValue);
    Serial.printf("  Cleanliness: %.1f/100\n", cleanlinessScore);
    Serial.printf("  Raw EC: %.2f µS/cm\n", ecVal);

    // Build JSON in the EXACT format your Flask app expects
    StaticJsonDocument<512> doc;
    doc["cup_id"] = CUP_ID;                    // This is the key field!
    doc["ph"] = phValue;                       // Match Flask app field names
    doc["tds"] = tdsValue;                     // Match Flask app field names
    doc["temperature"] = tempC;                // Match Flask app field names
    doc["salinity"] = salinityValue;           // Match Flask app field names
    doc["cleanliness_score"] = cleanlinessScore; // Match Flask app field names

    String payload;
    serializeJson(doc, payload);
    
    Serial.println("JSON payload:");
    Serial.println(payload);

    // POST to server
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(SERVER_URL);
      http.addHeader("Content-Type", "application/json");
      
      Serial.println("Sending POST request...");
      int httpCode = http.POST(payload);
      
      if (httpCode > 0) {
        String resp = http.getString();
        Serial.printf("HTTP %d response: %s\n", httpCode, resp.c_str());
        
        if (httpCode == 200) {
          Serial.println("✓ Data sent successfully!");
        } else {
          Serial.printf("⚠ Unexpected HTTP code: %d\n", httpCode);
        }
      } else {
        Serial.printf("✗ HTTP POST failed: %s\n", http.errorToString(httpCode).c_str());
      }
      http.end();
    } else {
      Serial.println("✗ WiFi disconnected - skipping POST");
    }
    
    Serial.println("=== Measurement Complete ===\n");
  }
  delay(100); // Small delay to prevent overwhelming the system
}