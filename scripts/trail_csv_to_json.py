#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# ///
"""
Converts first 6 columns of a CSV file to a JSON array of objects.
Input: CSV path, JSON path, array name (positional args)
"""

import csv
import json
import sys

def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <input.csv> <output.json> <array_name>")
        sys.exit(1)

    csv_path = sys.argv[1]
    json_path = sys.argv[2]
    array_name = sys.argv[3]

    with open(csv_path, newline='') as f:
        reader = csv.reader(f)
        headers = next(reader)[:6]
        data = [{headers[i]: row[i] for i in range(6)} for row in reader]

    with open(json_path, 'w') as f:
        json.dump({array_name: data}, f, indent=2)

if __name__ == "__main__":
    main()
