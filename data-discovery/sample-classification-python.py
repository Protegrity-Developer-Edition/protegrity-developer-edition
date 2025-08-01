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

test_data = (
    "The customer reported their card number as 4024007154260020, but they might need to check it again. "
    "During the verification process, we noticed 6011781675152556 was submitted multiple times by mistake. "
    "Please ensure you replace the incorrect input 5167982896988451 with valid data. "
    "I think 4539754659592262 was listed in a previous entry, but double-check just in case. "
    "For reference, 348598789276293 seems to follow an old format; update as required."
)

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
