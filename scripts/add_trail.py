#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# ///
"""
Adds a new trail to the site by updating forecast_locations.json and config.json.
Input: JSON file path (positional), --code (trail code), --name (trail name)
"""

import argparse
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
LOCATIONS_FILE = os.path.join(PROJECT_ROOT, 'src', 'forecast_locations.json')
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.json')

HELP_TEXT = """
Steps to add a new trail:

1. Create a JSON file with a forecast location every ~25 miles along the trail. Example:
   {
     "pnt": [
       {"point": "001", "name": "Eastern Terminus", "state": "MT", "lat": "48.99591", "lon": "-113.65970", "mile": "0.0"},
       {"point": "002", "name": "Waterton River Camp", "state": "MT", "lat": "48.95578", "lon": "-113.89765", "mile": "26.8"},
       ...
     ]
   }

   You can use scripts/trail_csv_to_json.py to make this easier.

2. Run this script to register the trail:
   ./scripts/add_trail.py <locations.json> --shortname <trail abbreviation> --longname "<Trail Name>"

3. Deploy to Lambda:
   make deploy

4. Immediately generate forecasts:
   ./scripts/invoke.sh --trail <trail abbreviation>
"""


def main():
    parser = argparse.ArgumentParser(
        description='Add a new trail to the site',
        epilog=HELP_TEXT,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('input_json', nargs='?', help='Path to JSON file with trail location data')
    parser.add_argument('--shortname', help='Trail abbreviation (e.g., pnt)')
    parser.add_argument('--longname', help='Trail name (e.g., Pacific Northwest Trail)')
    args = parser.parse_args()

    if not args.input_json or not args.shortname or not args.longname:
        parser.print_help()
        return

    # load input trail data
    with open(args.input_json) as f:
        input_data = json.load(f)
    # extract the locations array (input file has trail code as key)
    trail_key = list(input_data.keys())[0]
    locations = input_data[trail_key]

    # merge into forecast_locations.json
    with open(LOCATIONS_FILE) as f:
        all_locations = json.load(f)
    all_locations[args.shortname] = locations
    with open(LOCATIONS_FILE, 'w') as f:
        json.dump(all_locations, f, indent=2)
    print(f"Added {len(locations)} locations for '{args.shortname}' to {LOCATIONS_FILE}")

    # add to config.json TRAILS dict
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    config['TRAILS'][args.shortname] = args.longname
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"Added '{args.shortname}': '{args.longname}' to {CONFIG_FILE}")

    print("\nReminder: run 'make deploy' to push changes to Lambda")


if __name__ == "__main__":
    main()
