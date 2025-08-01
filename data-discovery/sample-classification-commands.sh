#!/usr/bin/env bash

export TEST_DATA="The customer reported their card number as 4024007154260020, \
but they might need to check it again. During the verification process, \
we noticed 6011781675152556 was submitted multiple times by mistake. \
Please ensure you replace the incorrect input 5167982896988451 with valid data. \
I think 4539754659592262 was listed in a previous entry, but double-check just in case. \
For reference, 348598789276293 seems to follow an old format; update as required."

curl -X POST "http://localhost:8580/pty/data-discovery/v1.0/classify" -H "Content-Type: text/plain" --data "$TEST_DATA"
