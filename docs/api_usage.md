# CIRIS API Usage & Code Examples

## cURL Usage Examples

### 1. Check System Status
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/system/status"
```

### 2. Create a Case
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/cases" \
  -H "Content-Type: application/json" \
  -d '{
    "complaint_id": "CMP_2026_TEST_101",
    "reported_loss_amount": 60000.0,
    "fraud_type": "Investment Cyber Fraud",
    "victim_location": {
      "state": "Maharashtra",
      "district": "Mumbai",
      "city": "Mumbai",
      "latitude": 19.1136,
      "longitude": 72.8697
    }
  }'
```

### 3. Get Case Intelligence
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/cases/CASE-DEMO-001/intelligence"
```

### 4. Get Money Flow Graph
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/cases/CASE-DEMO-001/money-flow?max_hops=3"
```

### 5. Get ATM Prediction
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/cases/CASE-DEMO-001/prediction"
```

---

## Python API Integration Example

```python
import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"

# Fetch intelligence for CASE-DEMO-001
response = requests.get(f"{BASE_URL}/cases/CASE-DEMO-001/intelligence")
intelligence = response.json()

print(f"Case Risk: {intelligence['overall_case_risk']}")
print(f"Top ATM Endpoint: {intelligence['potential_endpoints'][0]['endpoint_name']}")
print(f"Recommended Action: {intelligence['intervention_recommendation']['recommended_action']}")
```
