# LongTrailsWeather Backend

AWS Lambda function that fetches weather forecasts from the PirateWeather API for hiking trail locations. After fetching the forecasts the data is written to S3 in the format used by LongTrailsWeather-frontend.

Frontend repo: https://github.com/OpenLongTrails/LongTrailsWeather-frontend

# Configuration

### Lambda Settings
- **Runtime**: Python 3.13
- **Handler**: lambda_function.lambda_handler
- **Timeout**: 900 seconds (15 minutes)
- **Memory**: 128 MB
- **Region**: us-east-1

### API Key
The PirateWeather API key is read from:
1. Environment variable `PIRATE_WEATHER_API_KEY` (used on Lambda)
2. Fallback to `config.json` (for local testing)

## Architecture

### Data Flow
1. `del_s3_prefix_contents()` - Clears old raw and detail forecasts for a trail
2. `get_forecasts()` - Fetches forecasts from PirateWeather API for each location, saves raw JSON to S3
3. `process_forecasts()` - Reads raw forecasts, writes summary and detail files, archives both

### S3 Structure

**Bucket**: `www.longtrailsweather.net`

| Path | Description | Access |
|------|-------------|--------|
| `forecasts/raw/<trail>/` | Temporary raw API responses | Public |
| `forecasts/processed/<trail>.json` | Current summary forecasts (all locations) | Public |
| `forecasts/detail/<trail>/<point>.json` | Current detail forecasts (per location, includes GPS coords) | Public |
| `forecasts/archive/summary/<trail>_YYYYMMDD.json` | Daily archives of processed/ files | Private (Glacier) |
| `forecasts/archive/detail/<trail>_YYYYMMDD/<point>.json` | Daily detail archives | Private (Glacier) |

### Raw Forecast Filename Format
`forecast_<trail>_<point>_<name>_<mile>_<state>_<timestamp>.json`
- Spaces in names are replaced with `*`
- Fields are parsed back using `_` delimiter and index positions

## How To

### Add a New Trail
1. Add location data to `src/forecast_locations.json`
2. Deploy: `make deploy`

### Change Timeout or Memory
Edit `deploy.sh` and update `TIMEOUT` or `MEMORY` variables, or use AWS CLI:
```bash
aws lambda update-function-configuration \
  --function-name update_forecasts \
  --timeout 1200 \
  --region us-east-1
```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make deploy` | Deploy function to Lambda |
| `make deploy-dry-run` | Test deployment without uploading |
| `make invoke` | Invoke function synchronously |
| `make invoke-async` | Invoke function asynchronously |
| `make test` | Run local tests |
| `make info` | Show Lambda configuration |
| `make logs` | Tail CloudWatch logs |
| `make clean` | Remove deployment artifacts |

## License

GNU Affero General Public License v3.0 (AGPL-3.0). See [LICENSE](LICENSE) for details.
