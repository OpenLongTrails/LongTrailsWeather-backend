import json
import math
import os
import boto3
import datetime
import urllib.request

S3_BUCKET = 'www.longtrailsweather.net'


def is_valid_timestamp(val):
    """
    Returns True if val is a valid numeric timestamp.
    Returns False for None, non-numeric types, or NaN.
    """
    if val is None:
        return False
    if not isinstance(val, (int, float)):
        return False
    if isinstance(val, float) and math.isnan(val):
        return False
    return True


def get_api_key():
    """
    Returns PirateWeather API key from environment variable or config.json fallback.
    """
    api_key = os.environ.get('PIRATE_WEATHER_API_KEY')
    if api_key:
        return api_key
    # fallback for local testing
    with open('config.json', 'r') as f:
        config = json.load(f)
    return config['PIRATE_WEATHER_API_KEY']


def load_locations():
    """
    Returns dict of trail locations from forecast_locations.json.
    """
    with open('forecast_locations.json', 'r') as f:
        return json.load(f)


def del_s3_prefix_contents(prefix):
    """
    Deletes all objects under the given S3 prefix.
    prefix: e.g., 'forecasts/raw/lt' or 'forecasts/detail/lt'
    """
    objects_to_delete = []
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(S3_BUCKET)

    for obj in bucket.objects.filter(Prefix=prefix):
        if obj.key[-1] != '/':
            objects_to_delete.append({'Key': obj.key})

    # delete_objects accepts up to 1,000 objects; complains if list is empty
    if len(objects_to_delete) > 0:
        bucket.delete_objects(Delete={'Objects': objects_to_delete})


def get_forecasts(locations, trailname):
    api_key = get_api_key()
    for location in locations:
        url = f"https://api.pirateweather.net/forecast/{api_key}/{location['lat']},{location['lon']}?exclude=minutely,hourly"
        forecast = urllib.request.urlopen(url).read()

        #           0            1                 2                         3                                          4                                    5                   6 7
        filename = 'forecast_' + trailname + "_" + location['point'] + '_' + location['name'].replace(" ", "*") + "_" + str(float(location['mile'])) + "_" + location['state'] + "_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.json'

        write_to_s3(S3_BUCKET, 'forecasts/raw/' + trailname + '/' + filename, forecast)

        print(S3_BUCKET + '/forecasts/raw/' + trailname + '/' + filename + ' written.')


def process_forecasts(trailname, map_url_template):
    forecasts = []
    last_modified = datetime.datetime.today()

    s3 = boto3.resource('s3')

    bucket = s3.Bucket(S3_BUCKET)

    for obj in bucket.objects.filter(Prefix='forecasts/raw/' + trailname):
        if (obj.key[-1] != '/'):
            days = []

            content_object = s3.Object(obj._bucket_name, obj.key)
            file_content = content_object.get()['Body'].read().decode('utf-8')
            json_content = json.loads(file_content)
            alerts = json_content.get('alerts') or []

            last_modified = content_object.last_modified

            print('processing ' + content_object.key + '...', end='')

            for n, source_day in enumerate(json_content['daily']['data']):
                processed_day = {}

                processed_day['daynum'] = n

                print(str(n) + '...', end='')

                if 'time' in source_day:
                    processed_day['time'] = source_day['time']
                else:
                    processed_day['time'] = "#NA"

                if 'icon' in source_day:
                    processed_day['icon'] = source_day['icon']
                else:
                    processed_day['icon'] = "#NA"

                if 'temperatureHigh' in source_day:
                    processed_day['temperatureHigh'] = source_day['temperatureHigh']
                else:
                    processed_day['temperatureHigh'] = "#NA"

                if 'temperatureLow' in source_day:
                    processed_day['temperatureLow'] = source_day['temperatureLow']
                else:
                    processed_day['temperatureLow'] = "#NA"

                if 'precipAccumulation' in source_day:
                    processed_day['precipAccumulation'] = source_day['precipAccumulation']
                else:
                    processed_day['precipAccumulation'] = "#NA"

                if 'precipProbability' in source_day:
                    processed_day['precipProbability'] = source_day['precipProbability']
                else:
                    processed_day['precipProbability'] = "#NA"

                if 'precipType' in source_day:
                    processed_day['precipType'] = source_day['precipType']
                else:
                    processed_day['precipType'] = "#NA"

                if 'summary' in source_day:
                    processed_day['summary'] = source_day['summary']
                else:
                    processed_day['summary'] = "#NA"

                # check if any alert overlaps this day
                day_start = source_day.get('time', 0)
                day_end = day_start + 86400
                has_alert = False
                for alert in alerts:
                    alert_start = alert.get('time')
                    alert_end = alert.get('expires')
                    start_valid = is_valid_timestamp(alert_start)
                    end_valid = is_valid_timestamp(alert_end)
                    # start > end is nonsensical — treat both as bad
                    if start_valid and end_valid and alert_start > alert_end:
                        start_valid = False
                        end_valid = False
                    if not start_valid:
                        alert_start = 0
                    if not end_valid:
                        alert_end = float('inf')
                    if alert_start < day_end and alert_end > day_start:
                        has_alert = True
                        break
                processed_day['alert'] = has_alert

                days.append(processed_day)

            print('')

            # Write detail file with all daily data for this location
            point = content_object.key.split('_')[2]
            detail = {
                'gps': [json_content['longitude'], json_content['latitude']],
                'days': json_content['daily']['data'],
                'alerts': alerts
            }
            detail_json = json.dumps(detail)
            write_to_s3(S3_BUCKET, f'forecasts/detail/{trailname}/{point}.json', detail_json)
            # Archive detail file
            date_str = f'{datetime.datetime.now().year}{datetime.datetime.now().month:02}{datetime.datetime.now().day:02}'
            write_to_s3(S3_BUCKET, f'forecasts/archive/detail/{trailname}_{date_str}/{point}.json', detail_json)

            forecasts.insert(int(content_object.key.split('_')[2]),
                             {'key': content_object.key,
                              'location_index': int(content_object.key.split('_')[2]),
                              'location_name': content_object.key.split('_')[3].replace('*', ' '),
                              'lat': json_content['latitude'],
                              'lon': json_content['longitude'],
                              'distance': content_object.key.split('_')[4],
                              'timezone': json_content['timezone'],
                              'days': days})

    a = {'last_modified': str(last_modified),
         'map_url_template': map_url_template,
         'forecasts': forecasts}

    write_to_s3(S3_BUCKET, 'forecasts/processed/' + trailname + '.json', json.dumps(a))
    write_to_s3(S3_BUCKET, 'forecasts/archive/summary/' + trailname + f'_{datetime.datetime.now().year}{datetime.datetime.now().month:02}{datetime.datetime.now().day:02}.json', json.dumps(a))


def write_to_s3(s3_bucketname, fullpath, string):
    """
    Writes string content to S3. Archive files are private; others are public-read.
    """
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(s3_bucketname)
    acl = 'private' if fullpath.startswith('forecasts/archive/') else 'public-read'
    response = bucket.put_object(
        ACL=acl,
        ContentType='application/json',
        Key=fullpath,
        Body=string,
    )
    print('saved ' + s3_bucketname + '/' + response.key)


def main(trails_to_update=None):
    """
    Updates forecasts for specified trails, or all if none specified.
    trails_to_update: optional list of trail codes (at, azt, ct, lt, pct)
    """
    trail_data = load_locations()

    # if no trails specified, update all; otherwise filter to requested trails
    trails = trails_to_update if trails_to_update else trail_data.keys()
    for trail in trails:
        if trail in trail_data:
            update_trail(trail, trail_data[trail]['locations'], trail_data[trail]['map_url_template'])
        else:
            print(f"Unknown trail: {trail}")


def update_trail(trailname, locations, map_url_template):
    del_s3_prefix_contents(f'forecasts/raw/{trailname}')
    del_s3_prefix_contents(f'forecasts/detail/{trailname}')
    get_forecasts(locations, trailname)
    process_forecasts(trailname, map_url_template)
    

def lambda_handler(event, context):
    """
    Entry point for Lambda. Accepts optional 'trails' list in event.
    If trails not specified, updates all trails.
    """
    trails_to_update = event.get('trails') if event else None
    main(trails_to_update)

    print('done.')
    return("success.")

