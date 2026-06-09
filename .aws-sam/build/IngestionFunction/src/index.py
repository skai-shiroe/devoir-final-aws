import json
import os
import uuid
import boto3
from datetime import datetime

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

S3_BUCKET = os.environ.get("S3_BUCKET", "default-bucket")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "default-table")


def handler(event, context):
    try:
        # Parse the incoming HTTP request body
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", {})

        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        now = datetime.utcnow()
        year = now.strftime("%Y")
        month = now.strftime("%m")

        # Extract measurements list
        measurements = body.get("measurements", [])

        # Save raw payload to S3 with temporal partitioning
        s3_key = f"raw-zone/year={year}/month={month}/{request_id}.json"
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(body, indent=2),
            ContentType="application/json",
        )

        # Compute metrics
        temperatures = [
            m["temperature"]
            for m in measurements
            if "temperature" in m and isinstance(m.get("temperature"), (int, float))
        ]
        avg_temperature = round(sum(temperatures) / len(temperatures), 2) if temperatures else 0.0
        error_count = sum(
            1 for m in measurements if m.get("status", "").upper() == "ERROR"
        )

        # Save execution report to DynamoDB
        table = dynamodb.Table(DYNAMODB_TABLE)
        table.put_item(
            Item={
                "request_id": request_id,
                "timestamp": timestamp,
                "s3_path": s3_key,
                "avg_temperature": avg_temperature,
                "error_count": error_count,
                "total_measurements": len(measurements),
            }
        )

        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "Ingestion successful",
                "request_id": request_id,
                "s3_path": s3_key,
                "avg_temperature": avg_temperature,
                "error_count": error_count,
            }),
        }

    except Exception as e:
        # Log the error (will appear in CloudWatch)
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "Ingestion failed",
                "error": str(e),
            }),
        }