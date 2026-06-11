#!/usr/bin/env python
"""
This example demonstrates how to classify tabular data (csv) using the Data Discovery API
with Python's `requests` library.

It submits the contents of a csv file with sensitive information, to a local Data Discovery 
service for classification.

Note: If the `requests` library is not installed, you can add it using:
    pip install requests
"""
import os
import requests

URL = "http://localhost:8580/pty/data-discovery/v2/classify/tabular"
INPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "input.csv")

with open(INPUT_FILE, "r") as f:
    test_data = f.read()

parameters = {
    # Submit the request with the 'score_threshold' parameter to filter classification results 
    # with scores equal to or above 0.6.
    # If this parameter is not specified, the 'score_threshold' will default to 0.
    'score_threshold': 0.6,

    # The 'has_headers' parameter indicates whether the CSV input has headers.
    # Set it to True if the first row contains headers, otherwise False.
    # If this parameter is not specified, it will default to True.
    'has_headers': True,

    # The 'column_delimiter' parameter specifies the delimiter used in the CSV input.
    # If this parameter is not specified, it will default to a comma (",").
    'column_delimiter': ",",
}

# Use 'text/csv' for tabular/CSV input. Use 'text/plain' for unstructured text.
headers = {
    "Content-Type": "text/csv"
}

response = requests.post(URL, headers=headers, data=test_data, params=parameters)

print("Status Code:", response.status_code)
print("Response Body:", response.text)
