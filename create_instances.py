import boto3
import sys
import os

"""
This script will create a set of EC2 instances for each student in a course.

Usage: python create_instances.py <course_name> <csv_file>

The results of the script are:
1. A set of EC2 instances, one for each student in the course
  * Amazon Linux 2 AMI
  * Each instance is tagged with the 'Name' and 'course' tags
  * SSH, HTTP, and HTTPS traffic is allowed in the security group
2. A set of DNS records in Route 53, one for each student in the course
  * <username>.<domain_name> will resolve to the public IPv4 address of the EC2 instance

Configuration:
1. Install the AWS CLI
2. Configure the AWS CLI with your credentials
3. Create a CSV file with the student names (one name per line)
4. Set the key_name variable to the name of your EC2 key pair
5. Set the domain_name variable to the domain name of your hosted zone in Route 53
6. Set the instance_type variable to the EC2 instance type you want to use

The script is configured to use the most recent version of Amazon Linux 2 AMI.  Edit the get_most_recent_ami_id() function if you want to use a different AMI.
The security group is configured to allow SSH, HTTP, and HTTPS traffic.  Edit the create_security_group() function if you want to change the rules.

This script was written with extensive help from ChatGPT3.5
"""

key_name = 'coleman-moravian'
domain_name = 'moraviancs.click'
instance_type = 't2.micro'

def get_most_recent_ami_id(ec2):
    print("Fetching the most recent Amazon Linux 2 AMI ID...")
    response = ec2.describe_images(
        Filters=[
            {'Name': 'name', 'Values': ['amzn2-ami-hvm-*-x86_64-gp2']},
            {'Name': 'architecture', 'Values': ['x86_64']},
            {'Name': 'root-device-type', 'Values': ['ebs']},
            {'Name': 'virtualization-type', 'Values': ['hvm']},
        ],
        Owners=['amazon'],
    )

    # Sort the images by creation date in descending order
    images = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)

    # Get the most recent image ID
    ami_id = images[0]['ImageId']
    print(f"Using AMI ID: {ami_id}")
    return ami_id


def create_security_group(ec2, course_name):
    # Create a security group with the required rules
    security_group_response = ec2.create_security_group(
        GroupName=f"{course_name}_security_group",
        Description=f"Security group for {course_name} instances",
        TagSpecifications=[
            {
                'ResourceType': 'security-group',
                'Tags': [
                    {'Key': 'course', 'Value': course_name},
                ],
            },
        ],
    )

    security_group_id = security_group_response['GroupId']
    print(f"Security group created with ID: {security_group_id}")

    # Authorize rules for SSH, HTTP, and HTTPS traffic
    ec2.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=[
            {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp', 'FromPort': 443, 'ToPort': 443, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
        ]
    )
    return security_group_id

def launch_ec2_instance(ec2, csv_file, course_name, ami_id, security_group_id):
        # Read student names from the file
    with open(csv_file, 'r') as file:
        student_names = file.read().splitlines()

    # Create EC2 instances for each student
    instances = []
    for name in student_names:
        print(f"Creating EC2 instance for '{name}'...")
        response = ec2.run_instances(
            ImageId=ami_id,
            InstanceType=instance_type,
            KeyName=key_name,
            SecurityGroupIds=[security_group_id],
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': name},
                        {'Key': 'course', 'Value': course_name},
                    ],
                },
            ],
        )

        instance_id = response['Instances'][0]['InstanceId']
        instances.append({'name': name, 'instance_id': instance_id})

        print(f"Instance '{name}' created with ID: {instance_id}")

    return instances

def wait_for_instances_to_be_running(ec2, instances):
    print("Waiting for instances to be running...")
    ec2.get_waiter('instance_running').wait(InstanceIds=[instance['instance_id'] for instance in instances])
    print("Instances are running.")

def get_pulic_ips(ec2, instances):
    public_ips = {}
    for instance in instances:
        response = ec2.describe_instances(InstanceIds=[instance['instance_id']])
        public_ip = response['Reservations'][0]['Instances'][0].get('PublicIpAddress', 'N/A')
        public_ips[instance['name']] = public_ip

    print("\nStudent names and corresponding public IPv4 addresses:")
    for name, public_ip in public_ips.items():
        print(f"{name}: {public_ip}")
    
    return public_ips


def create_ec2_instances(course_name, csv_file):
    ec2 = boto3.client('ec2', region_name='us-east-1')

    ami_id = get_most_recent_ami_id(ec2)
    security_group_id = create_security_group(ec2, course_name)
    instances = launch_ec2_instance(ec2, csv_file, course_name, ami_id, security_group_id)
    wait_for_instances_to_be_running(ec2, instances)
    public_ips = get_pulic_ips(ec2, instances)

    return public_ips


import boto3

def create_route53_records(public_ips):
    # Look up the hosted_zone_id for 'moraviancs.click'
    hosted_zone_id = get_hosted_zone_id(domain_name)

    # Create DNS entries and tag each subdomain
    client = boto3.client('route53')

    changes = []
    for name, public_ip in public_ips.items():
        record_set = {
            'Name': f"{name}.{domain_name}",
            'Type': 'A',
            'TTL': 300,
            'ResourceRecords': [{'Value': public_ip}]
        }

        changes.append({
            'Action': 'UPSERT',
            'ResourceRecordSet': record_set
        })

    # Create DNS records without checking whether hosted_zone_id is None
    change_batch = {'Changes': changes}
    response = client.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch=change_batch
    )

    print(f"DNS records created successfully. Change ID: {response['ChangeInfo']['Id']}")

def get_hosted_zone_id(domain_name):
    client = boto3.client('route53')

    response = client.list_hosted_zones_by_name(DNSName=domain_name)

    for hosted_zone in response['HostedZones']:
        if hosted_zone['Name'] == f"{domain_name}.":
            # Remove the prefix '/hostedzone/' from the hosted zone ID
            return hosted_zone['Id'].split('/')[-1]

    return None


def build_instances(course_name, csv_file):
    public_ips = create_ec2_instances(course_name, csv_file)
    create_route53_records(public_ips)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <course_name> <csv_file>")
        sys.exit(1)

    course_name = sys.argv[1]
    csv_file = sys.argv[2]

    # Check if the CSV file exists
    if not os.path.exists(csv_file):
        print(f"Error: File '{csv_file}' not found. Please provide a valid CSV file.")
        sys.exit(1)
    build_instances(course_name, csv_file)
