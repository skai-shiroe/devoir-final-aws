import requests
import json

# Replace with your actual CloudFront Ingestion URL from the stack Outputs
CLOUDFRONT_URL = "https://d1ngb7eee3.execute-api.eu-west-3.amazonaws.com"

# Valid payload with 4+ structured measurements
valid_payload = {
    "measurements": [
        {"sensor_id": "sensor-001", "temperature": 22.5, "status": "OK"},
        {"sensor_id": "sensor-002", "temperature": 25.1, "status": "OK"},
        {"sensor_id": "sensor-003", "temperature": 18.3, "status": "ERROR"},
        {"sensor_id": "sensor-004", "temperature": 30.7, "status": "OK"},
        {"sensor_id": "sensor-005", "temperature": 19.8, "status": "ERROR"},
    ]
}

print("=== Test 1: Valid payload ===")
try:
    response = requests.post(
        f"{CLOUDFRONT_URL}/ingest",
        json=valid_payload,
        timeout=30
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {json.dumps(response.json(), indent=2)}")
    if response.status_code == 201:
        print("✅ Ingestion successful!")
    else:
        print("❌ Unexpected status code")
except Exception as e:
    print(f"❌ Request failed: {str(e)}")

print()

# Corrupted payload (malformed JSON)
print("=== Test 2: Corrupted payload (malformed JSON) ===")
try:
    response = requests.post(
        f"{CLOUDFRONT_URL}/ingest",
        data="this is not valid json",
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
    if response.status_code == 400:
        print("✅ Error correctly caught!")
    else:
        print("❌ Expected 400 error")
except Exception as e:
    print(f"❌ Request failed: {str(e)}")

print()

# Missing temperature values
print("=== Test 3: Missing temperature values ===")
invalid_payload = {
    "measurements": [
        {"sensor_id": "sensor-001", "status": "OK"},  # Missing temperature
    ]
}
try:
    response = requests.post(
        f"{CLOUDFRONT_URL}/ingest",
        json=invalid_payload,
        timeout=30
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"❌ Request failed: {str(e)}")