#!/usr/bin/env bash

export TEST_FILE="input.csv"

curl -X POST "http://localhost:8580/pty/data-discovery/v1.1/classify" -H "Content-Type: text/csv" --data-binary @"$TEST_FILE"