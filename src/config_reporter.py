import os
import boto3
import json
import logging
from botocore.exceptions import ClientError
 
ec2Json = "/tmp/ec2_instances_output.json"
S3Json = "/tmp/S3_output.json"
ELBJson = "/tmp/ELB_output.json"
ec2NGJson = "/tmp/ec2_natgatway_output.json"
ec2NIJson = "/tmp/ec2_networkinterface_output.json"
ec2EIPJson = "/tmp/ec2_EIP_output.json"
RDSINJson = "/tmp/RDS_Instance_output.json"
GlobalAccJson = "/tmp/GlobalAcc_output.json"
Route53Json = "/tmp/Route53_output.json"
LightSailJson = "/tmp/LightSail_output.json"

AGGREGATOR_NAME = os.environ['AGGREGATOR_NAME']  # AWS Config Aggregator name
BUCKET = os.environ['BUCKET_NAME'] # Bucket Name to store file
resourceIds = []
 
# Generate the resource link to AWS Console UI
def get_link(aws_region, resource_id, resource_type):
    return f'https://{aws_region}.console.aws.amazon.com/config/home?region={aws_region}#/resources/timeline?resourceId={resource_id}&resourceType={resource_type}'
 
# Generate the list of resources
def getdata(AGGREGATOR_NAME, type, sql_where):
    client = boto3.client('config')
 
    checker = True
    nexttoken = None
    while checker:

        if nexttoken:

            
            response = client.select_aggregate_resource_config(
            Expression=f"SELECT * WHERE resourceType = '{type}' {sql_where}", 
            ConfigurationAggregatorName=AGGREGATOR_NAME,
            Limit=100,
            NextToken=nexttoken
            )

            changed_resources = response["Results"]
            json_list = [json.loads(line) for line in changed_resources]
        else:
            
            response = client.select_aggregate_resource_config(
                Expression=f"SELECT * WHERE resourceType = '{type}' {sql_where}", 
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
    # EC2 Instance
    sql = " AND ( configuration.publicIpAddress BETWEEN '0.0.0.0' AND '255.255.255.255' OR configuration.ipv6Addresses BETWEEN '0:0:0:0:0:0:0:0' AND 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')"
    json_list = getdata(AGGREGATOR_NAME, type='AWS::EC2::Instance', sql_where=sql)
    
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

    # S3 Bucket
    sql = " AND ( supplementaryConfiguration.PublicAccessBlockConfiguration.blockPublicAcls = 'false' OR supplementaryConfiguration.PublicAccessBlockConfiguration.ignorePublicAcls = 'false' \
         OR supplementaryConfiguration.PublicAccessBlockConfiguration.blockPublicPolicy = 'false' OR supplementaryConfiguration.PublicAccessBlockConfiguration.restrictPublicBuckets = 'false' )"
    json_list = getdata(AGGREGATOR_NAME, type='AWS::S3::Bucket', sql_where=sql)

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
    
    # Elastic Load Balancer
    sql = " AND ( configuration.availabilityZones.loadBalancerAddresses.ipAddress BETWEEN '0.0.0.0' AND '255.255.255.255' OR configuration.availabilityZones.loadBalancerAddresses.ipAddress BETWEEN '0:0:0:0:0:0:0:0' AND 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff' OR configuration.scheme = 'internet-facing')"
    json_list = getdata(AGGREGATOR_NAME, type='AWS::ElasticLoadBalancingV2::LoadBalancer', sql_where=sql)

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
            load_baseline(ELBJson)
        except:
            pass
        
        write_info(account_id=account_id, resourceId=resource_id, info=response2['ConfigurationItem']['configuration'],filename=ELBJson)
    
    # NAT Gateway
    sql = " AND ( configuration.natGatewayAddresses.publicIp BETWEEN '0.0.0.0' AND '255.255.255.255' OR configuration.connectivityType = 'public')"
    json_list = getdata(AGGREGATOR_NAME, type='AWS::EC2::NatGateway', sql_where=sql)

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
            load_baseline(ec2NGJson)
        except:
            pass
        
        write_info(account_id=account_id, resourceId=resource_id, info=response2['ConfigurationItem']['configuration'],filename=ec2NGJson)
    # EC2 Network Interfaces
    sql = " AND ( configuration.association.carrierIp BETWEEN '0.0.0.0' AND '255.255.255.255' OR configuration.association.customerOwnedIp BETWEEN '0.0.0.0' AND '255.255.255.255' OR \
        configuration.association.publicIp BETWEEN '0.0.0.0' AND '255.255.255.255' OR configuration.privateIpAddresses.association.carrierIp BETWEEN '0.0.0.0' AND '255.255.255.255' OR \
        configuration.privateIpAddresses.association.customerOwnedIp BETWEEN '0.0.0.0' AND '255.255.255.255' OR configuration.privateIpAddresses.association.publicIp \
        BETWEEN '0.0.0.0' AND '255.255.255.255' OR configuration.ipv6Addresses.ipv6Address BETWEEN '0:0:0:0:0:0:0:0' AND 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff') AND configuration.status = 'in-use'"
    json_list = getdata(AGGREGATOR_NAME, type='AWS::EC2::NetworkInterface', sql_where=sql)

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
            load_baseline(ec2NIJson)
        except:
            pass
        
        write_info(account_id=account_id, resourceId=resource_id, info=response2['ConfigurationItem']['configuration'],filename=ec2NIJson)

    # EC2 EIP
    sql = " AND ( configuration.carrierIp BETWEEN '0.0.0.0' AND '255.255.255.255' OR configuration.customerOwnedIp BETWEEN '0.0.0.0' AND '255.255.255.255' OR \
        configuration.publicIp BETWEEN '0.0.0.0' AND '255.255.255.255')"
    json_list = getdata(AGGREGATOR_NAME, type='AWS::EC2::EIP', sql_where=sql)

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
            load_baseline(ec2EIPJson)
        except:
            pass
        
        write_info(account_id=account_id, resourceId=resource_id, info=response2['ConfigurationItem']['configuration'],filename=ec2EIPJson)

    # RDS Instance 
    sql = " AND configuration.dBInstanceStatus = 'available'"
    json_list = getdata(AGGREGATOR_NAME, type='AWS::RDS::DBInstance', sql_where=sql)

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
            load_baseline(RDSINJson)
        except:
            pass
        
        write_info(account_id=account_id, resourceId=resource_id, info=response2['ConfigurationItem']['configuration'],filename=RDSINJson)

    # Global Accelerator Instance 
    sql = " AND ( configuration.IpAddresses BETWEEN '0.0.0.0' AND '255.255.255.255' or configuration.DnsName <> '')"
    json_list = getdata(AGGREGATOR_NAME, type='AWS::GlobalAccelerator::Accelerator', sql_where=sql)

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
            load_baseline(GlobalAccJson)
        except:
            pass
        
        write_info(account_id=account_id, resourceId=resource_id, info=response2['ConfigurationItem']['configuration'],filename=GlobalAccJson)

    # LightSail Instance 
    sql = " AND ( configuration.IpAddresses BETWEEN '0.0.0.0' AND '255.255.255.255' OR configuration.Url <> '')"
    json_list = getdata(AGGREGATOR_NAME, type='AWS::Lightsail::StaticIp', sql_where=sql)

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
            load_baseline(LightSailJson)
        except:
            pass
        
        write_info(account_id=account_id, resourceId=resource_id, info=response2['ConfigurationItem']['configuration'],filename=LightSailJson)
    
    # Route53 Resolver 
    sql = " AND ( configuration.TargetIps.Ip BETWEEN '0.0.0.0' AND '255.255.255.255' )"
    json_list = getdata(AGGREGATOR_NAME, type='AWS::Route53Resolver::ResolverRule', sql_where=sql)

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
            load_baseline(Route53Json)
        except:
            pass
        
        write_info(account_id=account_id, resourceId=resource_id, info=response2['ConfigurationItem']['configuration'],filename=Route53Json)



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
    uploadFileS3(ELBJson, BUCKET)
    uploadFileS3(ec2NGJson, BUCKET)
    uploadFileS3(ec2NIJson, BUCKET)
    uploadFileS3(ec2EIPJson, BUCKET)
    uploadFileS3(RDSINJson, BUCKET)
    uploadFileS3(GlobalAccJson, BUCKET)
    uploadFileS3(LightSailJson, BUCKET)
    uploadFileS3(Route53Json, BUCKET)
 
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
        