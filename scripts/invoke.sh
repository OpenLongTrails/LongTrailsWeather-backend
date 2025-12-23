#!/bin/bash

# Script to invoke the Lambda function
# Usage: ./invoke.sh [--async] [--trail <code>]

FUNCTION_NAME="update_forecasts"
REGION="us-east-1"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

INVOCATION_TYPE="RequestResponse"
PAYLOAD='{}'

while [[ $# -gt 0 ]]; do
    case $1 in
        --async)
            INVOCATION_TYPE="Event"
            echo -e "${YELLOW}Running in async mode${NC}"
            shift
            ;;
        --trail)
            PAYLOAD="{\"trails\": [\"$2\"]}"
            echo -e "${YELLOW}Updating trail: $2${NC}"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

echo -e "${GREEN}Invoking Lambda function: ${FUNCTION_NAME}${NC}"
echo -e "${YELLOW}Region: ${REGION}${NC}"
echo ""

aws lambda invoke \
    --function-name ${FUNCTION_NAME} \
    --region ${REGION} \
    --invocation-type ${INVOCATION_TYPE} \
    --log-type Tail \
    --payload "${PAYLOAD}" \
    response.json \
    --query 'LogResult' \
    --output text | base64 -d

echo ""
echo -e "${GREEN}Response saved to response.json:${NC}"
cat response.json
echo ""
