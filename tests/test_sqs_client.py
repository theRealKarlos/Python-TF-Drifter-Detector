import boto3
import sys

print("About to create boto3 SQS client")
sys.stdout.flush()
sqs = boto3.client('sqs', region_name='eu-west-2')
print("boto3 SQS client created")
sys.stdout.flush()
response = sqs.list_queues()
print("list_queues response:", response)
sys.stdout.flush()
