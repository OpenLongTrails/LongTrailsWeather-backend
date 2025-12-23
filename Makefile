.PHONY: help deploy deploy-dry-run invoke invoke-async test clean info logs

help:
	@echo "Available commands:"
	@echo "  make deploy          - Deploy the Lambda function"
	@echo "  make deploy-dry-run  - Test deployment without actually deploying"
	@echo "  make invoke          - Invoke the Lambda function synchronously"
	@echo "  make invoke-async    - Invoke the Lambda function asynchronously"
	@echo "  make test            - Run local tests"
	@echo "  make info            - Show Lambda function information"
	@echo "  make logs            - Tail CloudWatch logs"
	@echo "  make clean           - Clean up deployment artifacts"

deploy:
	@chmod +x scripts/deploy.sh
	@./scripts/deploy.sh

deploy-dry-run:
	@chmod +x scripts/deploy.sh
	@./scripts/deploy.sh --dry-run

invoke:
	@chmod +x scripts/invoke.sh
	@./scripts/invoke.sh

invoke-async:
	@chmod +x scripts/invoke.sh
	@./scripts/invoke.sh --async

test:
	@python3 test_local.py

info:
	@aws lambda get-function-configuration \
		--function-name update_forecasts \
		--region us-east-1 \
		--output table

logs:
	@aws logs tail /aws/lambda/update_forecasts --follow --region us-east-1

clean:
	@rm -f deployment.zip response.json
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "Cleanup complete"
