# Balance Report Segment APIs Documentation

## Overview
Two new APIs have been created to work with balance report segments and financial data:

1. **Segments API** - Get unique segment values
2. **Financial Data API** - Get financial data for specific segment combinations

## API Endpoints

### 1. Get Unique Segments
**Endpoint:** `GET /api/accounts-entities/balance-report/segments/`

**Description:** Returns all unique values for segment1, segment2, and segment3.

**Query Parameters:**
- `segment1` (optional) - Filter segment2 and segment3 based on segment1
- `segment2` (optional) - Filter segment3 based on segment1 and segment2

**Example Requests:**
```bash
# Get all unique segments
GET /api/accounts-entities/balance-report/segments/

# Get segment2 and segment3 values for specific segment1
GET /api/accounts-entities/balance-report/segments/?segment1=10001

# Get segment3 values for specific segment1 and segment2
GET /api/accounts-entities/balance-report/segments/?segment1=10001&segment2=2205403
```

**Response Format:**
```json
{
    "success": true,
    "data": {
        "segment1": ["10001", "10191", "10334"],
        "segment2": ["2205403", "5041026", "5041025", "5080004", "5090001"],
        "segment3": ["CTRLCE1", "0000000", "SIPCCE1", "HRCE001", "IACE001", "CONSCE1"],
        "total_combinations": 10
    }
}
```

### 2. Get Financial Data for Segments
**Endpoint:** `GET /api/accounts-entities/balance-report/financial-data/`

**Description:** Returns detailed financial data for a specific segment combination.

**Required Query Parameters:**
- `segment1` - First segment value
- `segment2` - Second segment value  
- `segment3` - Third segment value

**Example Request:**
```bash
GET /api/accounts-entities/balance-report/financial-data/?segment1=10001&segment2=2205403&segment3=CTRLCE1
```

**Response Format:**
```json
{
    "success": true,
    "data": {
        "segments": {
            "segment1": "10001",
            "segment2": "2205403",
            "segment3": "CTRLCE1"
        },
        "latest_record": {
            "control_budget_name": "MIC_HQ_MONTHLY",
            "ledger_name": "MIC HQ Primary Ledger",
            "as_of_period": "Sep-25",
            "actual_ytd": 10000.0,
            "encumbrance_ytd": 13000.0,
            "funds_available_asof": -23000.0,
            "other_ytd": 2.0,
            "budget_ytd": 2.0,
            "last_updated": "2025-09-09T19:53:45.123456Z"
        },
        "aggregated_totals": {
            "total_actual_ytd": 10000.0,
            "total_encumbrance_ytd": 13000.0,
            "total_funds_available": -23000.0,
            "total_other_ytd": 2.0,
            "total_budget_ytd": 2.0,
            "record_count": 1
        },
        "calculated_metrics": {
            "budget_utilization_percent": 500000.0,
            "funds_remaining": -23000.0,
            "total_committed": 23000.0
        }
    }
}
```

### 3. Get Financial Data for Multiple Segments
**Endpoint:** `POST /api/accounts-entities/balance-report/financial-data/`

**Description:** Returns financial data for multiple segment combinations in a single request.

**Request Body:**
```json
{
    "segments": [
        {
            "segment1": "10001",
            "segment2": "2205403",
            "segment3": "CTRLCE1"
        },
        {
            "segment1": "10001",
            "segment2": "5041026",
            "segment3": "0000000"
        },
        {
            "segment1": "10191",
            "segment2": "5041025",
            "segment3": "HRCE001"
        }
    ]
}
```

**Response Format:**
```json
{
    "success": true,
    "data": [
        {
            "segments": {
                "segment1": "10001",
                "segment2": "2205403",
                "segment3": "CTRLCE1"
            },
            "success": true,
            "data": {
                "actual_ytd": 10000.0,
                "encumbrance_ytd": 13000.0,
                "funds_available_asof": -23000.0,
                "other_ytd": 2.0,
                "budget_ytd": 2.0,
                "as_of_period": "Sep-25",
                "last_updated": "2025-09-09T19:53:45.123456Z"
            }
        },
        {
            "segments": {
                "segment1": "10001",
                "segment2": "5041026",
                "segment3": "0000000"
            },
            "success": true,
            "data": {
                "actual_ytd": 0.0,
                "encumbrance_ytd": 0.0,
                "funds_available_asof": 50000.0,
                "other_ytd": 0.0,
                "budget_ytd": 50000.0,
                "as_of_period": "Sep-25",
                "last_updated": "2025-09-09T19:53:45.123456Z"
            }
        }
    ],
    "total_requested": 3,
    "found": 2
}
```

## Field Descriptions

### Financial Data Fields:
- **actual_ytd**: Actual spending year-to-date
- **encumbrance_ytd**: Encumbered (committed) funds year-to-date
- **funds_available_asof**: Available funds as of the report period
- **other_ytd**: Other financial adjustments year-to-date
- **budget_ytd**: Total budget allocation year-to-date

### Calculated Metrics:
- **budget_utilization_percent**: (Actual YTD / Budget YTD) * 100
- **funds_remaining**: Available funds
- **total_committed**: Actual YTD + Encumbrance YTD

## Error Responses

### Missing Segments (400 Bad Request):
```json
{
    "success": false,
    "message": "All three segments (segment1, segment2, segment3) are required"
}
```

### No Data Found (404 Not Found):
```json
{
    "success": false,
    "message": "No data found for segments: 10001/2205403/INVALID"
}
```

### Server Error (500 Internal Server Error):
```json
{
    "success": false,
    "message": "Error retrieving financial data: [error details]"
}
```

## Available Segment Values

Based on current data:

**Segment1 (Cost Centers):**
- 10001, 10191, 10334

**Segment2 (Accounts):**
- 2205403, 5041026, 5041025, 5080004, 5090001

**Segment3 (Projects):**
- CTRLCE1, 0000000, SIPCCE1, HRCE001, IACE001, CONSCE1

## Authentication
All endpoints require authentication. Include your JWT token in the Authorization header:
```
Authorization: Bearer your_jwt_token_here
```

## Rate Limiting
Standard API rate limiting applies to these endpoints.

## Usage Examples

### Python/Requests:
```python
import requests

# Get unique segments
response = requests.get(
    'http://localhost:8000/api/accounts-entities/balance-report/segments/',
    headers={'Authorization': 'Bearer your_token'}
)

# Get financial data for specific segments
response = requests.get(
    'http://localhost:8000/api/accounts-entities/balance-report/financial-data/',
    params={
        'segment1': '10001',
        'segment2': '2205403', 
        'segment3': 'CTRLCE1'
    },
    headers={'Authorization': 'Bearer your_token'}
)
```

### JavaScript/Fetch:
```javascript
// Get unique segments
const segments = await fetch('/api/accounts-entities/balance-report/segments/', {
    headers: {
        'Authorization': 'Bearer your_token'
    }
});

// Get financial data
const financialData = await fetch(
    '/api/accounts-entities/balance-report/financial-data/?segment1=10001&segment2=2205403&segment3=CTRLCE1',
    {
        headers: {
            'Authorization': 'Bearer your_token'
        }
    }
);
```
