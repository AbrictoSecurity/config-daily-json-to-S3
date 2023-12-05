import os
import boto3
import json
import logging
from botocore.exceptions import ClientError
 
ec2Json = f"/tmp/ec2_instances_output.json"
S3Json = f"/tmp/S3_output.json"
AGGREGATOR_NAME = os.environ['AGGREGATOR_NAME']  # AWS Config Aggregator name
BUCKET = os.environ['BUCKET_NAME'] # Bucket Name to store file
resourceIds = []
 
# Generate the resource link to AWS Console UI
def get_link(aws_region, resource_id, resource_type):
    return f'https://{aws_region}.console.aws.amazon.com/config/home?region={aws_region}#/resources/timeline?resourceId={resource_id}&resourceType={resource_type}'
 
# Generate the list of resources
def getdata(AGGREGATOR_NAME, type, publicIp):
    client = boto3.client('config')
 
    checker = True
    nexttoken = None
    while checker:

        if nexttoken:

            if publicIp:
                response = client.select_aggregate_resource_config(
                Expression=f"SELECT * WHERE resourceType = '{type}' AND ( configuration.publicIpAddress BETWEEN '0.0.0.0'\
                    AND '255.255.255.255' OR configuration.ipv6Addresses BETWEEN '0:0:0:0:0:0:0:0' AND 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')", 
                ConfigurationAggregatorName=AGGREGATOR_NAME,
                Limit=100,
                NextToken=nexttoken
                )
            else:
                response = client.select_aggregate_resource_config(
                Expression=f"SELECT * WHERE resourceType = '{type}'", 
                ConfigurationAggregatorName=AGGREGATOR_NAME,
                Limit=100,
                NextToken=nexttoken
                )

            changed_resources = response["Results"]
            json_list = [json.loads(line) for line in changed_resources]
        else:
            if publicIp:
                response = client.select_aggregate_resource_config(
                    Expression=f"SELECT * WHERE resourceType = '{type}'  AND ( configuration.publicIpAddress BETWEEN '0.0.0.0'\
                    AND '255.255.255.255' OR configuration.ipv6Addresses BETWEEN '0:0:0:0:0:0:0:0' AND 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')", 
                    ConfigurationAggregatorName=AGGREGATOR_NAME,
                    Limit=100
                )
            else:
                response = client.select_aggregate_resource_config(
                    Expression=f"SELECT * WHERE resourceType = '{type}'", 
                    ConfigurationAggregatorName=AGGREGATOR_NAME,
                    Limit=100
                )

            changed_resources = response["Results"]
            json_list = [json.loads(line) for line in changed_resources]
        try:
            nexttoken = response['NextToken']
            print(nexttoken)
        except:
            checker = False
        return json_list
 
def create_report(AGGREGATOR_NAME):
    
    client = boto3.client('config')
     
    json_list = getdata(AGGREGATOR_NAME, type='AWS::EC2::Instance',publicIp=True)
    
    for resource in json_list:
        aws_region = resource['awsRegion']
        resource_id = resource['resourceId']
        resource_type = resource['resourceType']
        resource['Link'] = get_link(aws_region, resource_id, resource_type)
        account_id = resource['accountId']
 
        response2 = client.get_aggregate_resource_config(
            ConfigurationAggregatorName=AGGREGATOR_NAME,
            ResourceIdentifier={
                    'SourceAccountId': account_id,
                    'SourceRegion': aws_region,
                    'ResourceId': resource_id,
                    'ResourceType': resource_type})
        try:
            load_baseline(ec2Json)
        except:
            pass
        
        write_info(account_id=account_id, resourceId=resource_id, info=response2['ConfigurationItem']['configuration'],filename=ec2Json)

    json_list = getdata(AGGREGATOR_NAME, type='AWS::S3::Bucket', publicIp=False)

    for resource in json_list:
        aws_region = resource['awsRegion']
        resource_id = resource['resourceId']
        resource_type = resource['resourceType']
        resource['Link'] = get_link(aws_region, resource_id, resource_type)
        account_id = resource['accountId']
 
        response2 = client.get_aggregate_resource_config(
        ConfigurationAggregatorName=AGGREGATOR_NAME,
        ResourceIdentifier={
                'SourceAccountId': account_id,
                'SourceRegion': aws_region,
                'ResourceId': resource_id,
                'ResourceType': resource_type})

        try:
            load_baseline(S3Json)
        except:
            pass
        
        write_info(account_id=account_id, resourceId=resource_id, info=response2['ConfigurationItem']['configuration'],filename=S3Json)

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
    create_report(AGGREGATOR_NAME)
    uploadFileS3(ec2Json, BUCKET)
    uploadFileS3(S3Json, BUCKET)
 
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
 
def write_info(account_id, resourceId, info, filename):
   
    if os.path.exists(filename):
        file = open(filename, 'r')
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
        json_string += '","account_id":"'
        json_string += account_id
        json_string += '",'
        json_string += '"info\":'
        json_string += info
        json_string += '}]}'
       
        data = json.loads(json_string)
    
    json_object = json.dumps(data, indent=4)
    with open(filename, "w") as outfile:
        outfile.write(json_object)