#!/usr/bin/env python
"""
This example demonstrates how to classify unstructured text using the Data Discovery API
with Python's `requests` library.

It submits text with sensitive information, to a local Data Discovery service for classification.

Note: If the `requests` library is not installed, you can add it using:
    pip install requests
"""
import requests

URL = "http://localhost:8580/pty/data-discovery/v1.0/classify"

test_data = """My name is John Smith, and I live in Stamford. 
My Social Security number is 234-23-2344, and I am 52 years old. 
You can reach me on my cell at (203) 222-3445 - that's a Connecticut number. 
The username I use to access my account is john_smith."""

# Submit the request with the 'score_threshold' parameter to filter classification results 
# with scores equal to or above 0.6.
# If this parameter is not specified, the 'score_threshold' will default to 0.
parameters = {
    'score_threshold': 0.6
}

# To classify unstructured text, use the 'text/plain' content type in the request header.
headers = {
    "Content-Type": "text/plain"
}

# The unstructured text must be submitted in the request body.
response = requests.post(URL, headers=headers, data=test_data, params=parameters)

print("Status Code:", response.status_code)
print("Response Body:", response.text)
