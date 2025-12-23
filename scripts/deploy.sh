#!/bin/bash

# Deployment script for update_forecasts Lambda function
# Usage: ./deploy.sh [--dry-run]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

FUNCTION_NAME="update_forecasts"
REGION="us-east-1"
HANDLER="lambda_function.lambda_handler"
RUNTIME="python3.13"
TIMEOUT=900
MEMORY=128

# Load AWS account ID from environment or config.json
if [ -z "$AWS_ACCOUNT_ID" ]; then
    if [ -f "config.json" ]; then
        AWS_ACCOUNT_ID=$(jq -r '.AWS_ACCOUNT_ID // empty' config.json)
    fi
fi
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}Error: AWS_ACCOUNT_ID not set. Export it or add to config.json${NC}"
    exit 1
fi
ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/forecastRole01"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deploying ${FUNCTION_NAME} to Lambda${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if dry-run mode
DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}Running in DRY-RUN mode${NC}"
fi

# Create deployment package
echo -e "\n${YELLOW}Step 1: Creating deployment package...${NC}"
cd src
rm -f ../deployment.zip

# If there are dependencies, install them
# pip install -r ../requirements.txt -t .

# Create zip file
zip -r ../deployment.zip lambda_function.py forecast_locations.json
cd ..

echo -e "${GREEN}✓ Deployment package created: deployment.zip${NC}"

# Get current function info
echo -e "\n${YELLOW}Step 2: Checking current function...${NC}"
CURRENT_SHA=$(aws lambda get-function --function-name ${FUNCTION_NAME} --region ${REGION} --query 'Configuration.CodeSha256' --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$CURRENT_SHA" == "NOT_FOUND" ]; then
    echo -e "${RED}Function does not exist. Use AWS CLI to create it first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Current CodeSha256: ${CURRENT_SHA}${NC}"

# Update function code
if [ "$DRY_RUN" = true ]; then
    echo -e "\n${YELLOW}Step 3: [DRY-RUN] Would update function code${NC}"
    echo "Command: aws lambda update-function-code --function-name ${FUNCTION_NAME} --zip-file fileb://deployment.zip --region ${REGION}"
else
    echo -e "\n${YELLOW}Step 3: Updating function code...${NC}"
    UPDATE_RESULT=$(aws lambda update-function-code \
        --function-name ${FUNCTION_NAME} \
        --zip-file fileb://deployment.zip \
        --region ${REGION} \
        --output json)

    NEW_SHA=$(echo $UPDATE_RESULT | jq -r '.CodeSha256')
    echo -e "${GREEN}✓ Code updated successfully${NC}"
    echo -e "${GREEN}✓ New CodeSha256: ${NEW_SHA}${NC}"

    # Wait for update to complete
    echo -e "\n${YELLOW}Step 4: Waiting for function to be ready...${NC}"
    aws lambda wait function-updated --function-name ${FUNCTION_NAME} --region ${REGION}
    echo -e "${GREEN}✓ Function is ready${NC}"
fi

# Display function info
echo -e "\n${YELLOW}Step 5: Current function configuration:${NC}"
aws lambda get-function-configuration \
    --function-name ${FUNCTION_NAME} \
    --region ${REGION} \
    --query '{Name:FunctionName, Runtime:Runtime, Handler:Handler, Timeout:Timeout, Memory:MemorySize, LastModified:LastModified}' \
    --output table

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment complete!${NC}"
echo -e "${GREEN}========================================${NC}"

# Cleanup
if [ "$DRY_RUN" = false ]; then
    echo -e "\n${YELLOW}Cleaning up deployment.zip...${NC}"
    rm -f deployment.zip
    echo -e "${GREEN}✓ Cleanup complete${NC}"
fi
