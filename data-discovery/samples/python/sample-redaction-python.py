#!/usr/bin/env python
"""
This example demonstrates how to redact sensitive information from unstructured text
using the Data Discovery Transform API with Python's `requests` library.

It submits text with sensitive information to a local Data Discovery service, which
classifies the PII and replaces each detected entity with a label (e.g. [PERSON]).

Note: If the `requests` library is not installed, you can add it using:
    pip install requests
"""
import requests

URL = "http://localhost:8580/pty/data-discovery/v2/transform/label"

test_data = """My name is John Smith, and I live in Stamford. 
My Social Security number is 234-23-2344, and I am 52 years old. 
You can reach me on my cell at (203) 222-3445 - that's a Connecticut number. 
The username I use to access my account is john_smith."""

# Use 'text/plain' for unstructured text. Use 'text/csv' for tabular/CSV input.
headers = {
    "Content-Type": "text/plain"
}

response = requests.post(URL, headers=headers, data=test_data)

print("Status Code:", response.status_code)
print("Response Body:", response.text)
