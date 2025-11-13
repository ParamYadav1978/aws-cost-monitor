import boto3
import os
from datetime import datetime, timedelta

# Initialize AWS clients
ce_client = boto3.client('ce') # Cost Explorer
sns_client = boto3.client('sns')

# Get the SNS Topic ARN from an environment variable
# In a real Lambda, you would set this in the configuration
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', 'arn:aws:sns:us-east-1:123456789012:MyWeeklyReportTopic')

def lambda_handler(event, context):
    """
    This function is triggered by EventBridge (CloudWatch Events) on a schedule.
    It fetches the last 7 days of AWS costs and publishes a report to an SNS topic.
    
    NOTE: Calling the Cost Explorer API (ce:GetCostAndUsage) is NOT free. 
    It costs $0.01 per request.
    """
    
    # 1. Define the time range for the report (last 7 days)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    try:
        # 2. Call the Cost Explorer API
        # This is the part that would cost $0.01
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='DAILY', # We want a day-by-day breakdown
            Metrics=['UnblendedCost']
        )
        
        # 3. Format the report
        report = f"AWS Cost Report for {start_date} to {end_date}:\n\n"
        total_cost = 0.0

        for day in response['ResultsByTime']:
            date = day['TimePeriod']['Start']
            cost = float(day['Total']['UnblendedCost']['Amount'])
            total_cost += cost
            report += f"- {date}: ${cost:.2f}\n"
        
        report += f"\nTotal for the last 7 days: ${total_cost:.2f}"
        
        print("Report Generated Successfully:\n", report)

        # 4. Publish the report to the SNS topic
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject='Weekly AWS Cost Report',
            Message=report
        )
        
        return {
            'statusCode': 200,
            'body': 'Report sent successfully!'
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        # Send an error message if it fails
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject='AWS Cost Report FAILED',
            Message=f"Failed to generate cost report. Error: {str(e)}"
        )
        return {
            'statusCode': 500,
            'body': str(e)
        }