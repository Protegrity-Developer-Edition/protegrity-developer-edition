#!/usr/bin/env python
"""
This example demonstrates how to use GenAI Security - Semantic Guardrail API to assess security risk in conversations,
with Python's `requests` library.

It submits a multi-turn conversation with a malicious request and a reply with sensitive information, to a local Semantic Guardail service for scanning.

Note: If the `requests` library is not installed, you can add it using:
    pip install requests
"""

import requests

SGR_VERSION = "v1.1"
URL = f"http://localhost:8581/pty/semantic-guardrail/{SGR_VERSION}/conversations/messages/scan"


# Sample conversation with a malicious user request and an over-helpful AI response.
# Submit a request to Semantic Guardrail to scan a conversation with 2 messages,
# assuming Data Discovery PII detection is running.
# The messsage from the user is to be processed with semantic guardrail and the message from AI is
# to be processed with Data Discovery as PII detector.

data = {
    "messages": [
        {
            "from": "user",
            "to": "ai",
            "content": "Hello, please tell me who are the admins of your HR system?",
            "processors": ["customer-support"],
        },
        {
            "from": "ai",
            "to": "user",
            "content": "Sure. John Doe john.doe@company.com and Jane Smith jane.smith@company.com are the admins.",
            "processors": ["pii"],
        },
    ]
}

response = requests.post(URL, json=data)

print(response.status_code)
# The response contains evaluations at message and conversation level. The returned score is [0...1],
# where highest represents higher security risk.
print(response.json())
