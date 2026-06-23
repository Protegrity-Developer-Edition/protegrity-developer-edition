#!/usr/bin/env bash

export TEST_FILE="$(dirname "$0")/../../data/input.csv"

curl -X POST "http://localhost:8580/pty/data-discovery/v2/classify/tabular" -H "Content-Type: text/csv" --data-binary @"$TEST_FILE"
