#!/usr/bin/env bash

export TEST_DATA="My name is John Smith, and I live in Stamford. 
My Social Security number is 234-23-2344, and I am 52 years old. 
You can reach me on my cell at (203) 222-3445 - that's a Connecticut number. 
The username I use to access my account is john_smith."

curl -X POST "http://localhost:8580/pty/data-discovery/v1.1/classify" -H "Content-Type: text/plain" --data "$TEST_DATA"
