"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
from distutils.command.config import config
import os
import boto3
from datetime import datetime
import json
import logging
import csv
from csv import writer
from botocore.exceptions import ClientError

today = datetime.now().strftime("%Y-%m-%d")  # Currnent day
filename = f'/tmp/changed_resources-{today}.csv'  # CSV report filename
ec2filename = f'/tmp/ec2changed_resources-{today}.csv'  # CSV report filename
ec2Json = f"/tmp/ec2_instances_output.json" # Temp EC2 information
AGGREGATOR_NAME = os.environ['AGGREGATOR_NAME']  # AWS Config Aggregator name
BUCKET = os.environ['BUCKET_NAME'] # Bucket Name to store file
resourceIds = []

# Generate the resource link to AWS Console UI
def get_link(aws_region, resource_id, resource_type):
    return f'https://{aws_region}.console.aws.amazon.com/config/home?region={aws_region}#/resources/timeline?resourceId={resource_id}&resourceType={resource_type}'

# Generate the CSV Report
def create_report(AGGREGATOR_NAME, today, filename):
    client = boto3.client('config')

    checker = True
    nexttoken = None
    while checker:
        if nexttoken:
            response = client.select_aggregate_resource_config(
            Expression=f"SELECT * ",
            ConfigurationAggregatorName=AGGREGATOR_NAME,
            Limit=100,
            NextToken=nexttoken
            )
            changed_resources = response["Results"]
            json_list = [json.loads(line) for line in changed_resources]
            # Transform the JSON response to CSV file
            for resource in json_list:
                aws_region = resource['awsRegion']
                resource_id = resource['resourceId']
                resource_type = resource['resourceType']
                resource['Link'] = get_link(aws_region, resource_id, resource_type)
                print(resource)
                account_id = resource['accountId']
                source_reg = resource['awsRegion']

                if resource['resourceType'] == 'AWS::EC2::Instance':
                    response2 = client.get_aggregate_resource_config(

                    ConfigurationAggregatorName=AGGREGATOR_NAME,
                    ResourceIdentifier={
                            'SourceAccountId': account_id,
                            'SourceRegion': aws_region,
                            'ResourceId': resource_id,
                            'ResourceType': resource_type
                        }
                    )
                
                    
                    
                        
                    try:
                        load_baseline(ec2Json)
                    except:
                        pass
                    write_host(resourceId=resource_id, info=response2['ConfigurationItem']['configuration'])



            all_fields = set()
            for item in json_list:
                all_fields.update(item.keys())
            # Save the report file
            with open(filename, 'a') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=list(all_fields))
                writer.writerows(json_list)
        else:
            response = client.select_aggregate_resource_config(
                Expression=f"SELECT * ",
                ConfigurationAggregatorName=AGGREGATOR_NAME,
                Limit=100
            )
            print(response)

            changed_resources = response["Results"]
            json_list = [json.loads(line) for line in changed_resources]
            # Transform the JSON response to CSV file
            for resource in json_list:
                aws_region = resource['awsRegion']
                resource_id = resource['resourceId']
                resource_type = resource['resourceType']
                resource['Link'] = get_link(aws_region, resource_id, resource_type)
                print(resource)
                account_id = resource['accountId']
                source_reg = resource['awsRegion']

                if resource['resourceType'] == 'AWS::EC2::Instance':
                    response2 = client.get_aggregate_resource_config(

                    ConfigurationAggregatorName=AGGREGATOR_NAME,
                    ResourceIdentifier={
                            'SourceAccountId': account_id,
                            'SourceRegion': aws_region,
                            'ResourceId': resource_id,
                            'ResourceType': resource_type
                        }
                    )
                    try:
                        load_baseline(ec2Json)
                    except:
                        pass
                    write_host(account_id=account_id, resourceId=resource_id, info=response2['ConfigurationItem']['configuration'])

        try:
            nexttoken = response['NextToken']
            print(nexttoken)
        except:
            checker = False
    print("Report generated " + filename)

def uploadFileS3(filename, BUCKET):

    try: 
        if os.path.exists(filename):
            s3 = boto3.client('s3')
            object_name = os.path.basename(filename)
            response = s3.delete_object(
                Bucket=BUCKET,
                Key=object_name,)
            print(response)
    except:
        logging.error(e)
        print("The file was not found")
        exit()

    try:
        if os.path.exists(filename):
            s3.upload_file(filename, BUCKET, object_name)
            print("Upload Successful")    

    except ClientError as e:
        logging.error(e)
        print("The file was not found")
        exit()

def config_reporter(event, lambda_context):
    create_report(AGGREGATOR_NAME, today, filename)
    uploadFileS3(ec2Json, BUCKET)

def load_baseline(filename):
    
    row = 0
    file = open(filename, 'r')
    data = json.load(file)
    check = True
    
    while check:

        try:
            resourceId = data['resources'][row]['resourceId']
            resourceIds.append(resourceId)
            check = True
            row += 1
 
        except:
            check = False

def write_host(account_id, resourceId, info):
    
    #TO THINK: 1 file for each host or all in the same file??

    if os.path.exists(ec2Json):
        file = open(ec2Json, 'r')
        data = json.load(file)

        if resourceId not in resourceIds:

            json_string = '{"resourceId":"'
            json_string += resourceId
            json_string += '","account_id":"'
            json_string += account_id
            json_string += '",'
            json_string += '"info\":'
            json_string += info 
            json_string += '}'

            new_data = json.loads(json_string)
            data['resources'].append(new_data)
        
        file.close()
        
    else:
        
        json_string = '{"resources":[{"resourceId":"'
        json_string += resourceId
        json_string += '",'
        json_string += '","account_id":"'
        json_string += account_id
        json_string += '",'
        json_string += '"info\":'
        json_string += info 
        json_string += '}]}'
        
        print(info)
        print(json_string)

        data = json.loads(json_string)
    json_object = json.dumps(data, indent=4)
    with open(ec2Json, "w") as outfile:
        outfile.write(json_object)