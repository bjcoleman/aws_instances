import boto3
import sys

"""
This script will clean up all the instances and resources created by the
create_instances.py script. It will:
    1. Find all EC2 instances with the 'course' tag
    2. Terminate all instances
    3. Delete the security group
    4. Delete the DNS records

Usage: python terminate_script.py <course_name>

Configuration:
* set the domain_name variable to the domain name you are using for the course

ChatGPT3.5 wrote most of this, but I had to write the DNS record deletion
code because GhatGPT just couldn't get it right!
"""

domain_name = 'moraviancs.click'


def delete_course_resources(course_name):
    # Step 1: Find all EC2 instances with the 'course' tag
    instances = get_instances_with_tag('course', course_name)

    if not instances:
        print(f"No instances found with 'course' tag value '{course_name}'.")
        return

    print_termination_summary(instances)

    # Step 2: Generate a list of dicts with instance id and name
    instance_ids = [instance['InstanceId'] for instance in instances]
    instance_names = [get_tag_value(instance, 'Name') for instance in instances]
    #instances_info = [{'id': instance['InstanceId'], 'name': get_tag_value(instance, 'name')} for instance in instances]

    # Step 3: Terminate instances and wait for termination
    terminate_instances(instance_ids)
    wait_for_termination(instance_ids)

    # Step 4: Delete security group
    security_group_name = f"{course_name}_security_group"
    delete_security_group(security_group_name)

    # Step 5: Delete DNS records
    delete_dns_record(domain_name, instance_names)

    print("Course resources deleted successfully.")

def print_termination_summary(instances):
    print(f"Terminating {len(instances)} instances:")
    for instance in instances:
        print(f"  {instance['InstanceId']}: {get_tag_value(instance, 'Name')}")


def get_instances_with_tag(key, value):
    ec2_client = boto3.client('ec2')
    response = ec2_client.describe_instances(
        Filters=[
            {
                'Name': f'tag:{key}',
                'Values': [value]
            }, 
            {
                'Name': 'instance-state-name',
                'Values': ['pending', 'running', 'shutting-down', 'stopping']
            }
        ]
    )

    instances = []
    for reservation in response['Reservations']:
        instances.extend(reservation['Instances'])

    return instances

def get_tag_value(resource, key):
    tags = resource.get('Tags', [])
    for tag in tags:
        if tag['Key'] == key:
            return tag['Value']
    return None

def terminate_instances(instance_ids):
    ec2_client = boto3.client('ec2')
    ec2_client.terminate_instances(InstanceIds=instance_ids)

def wait_for_termination(instance_ids):
    print("Waiting for instances to terminate...")
    ec2_client = boto3.client('ec2')
    waiter = ec2_client.get_waiter('instance_terminated')
    waiter.wait(InstanceIds=instance_ids)

def delete_security_group(security_group_name):
    print(f"Deleting security group '{security_group_name}'...")
    ec2_client = boto3.client('ec2')
    try:
        ec2_client.delete_security_group(GroupName=security_group_name)
    except ec2_client.exceptions.ClientError as e:
        if 'InvalidGroup.NotFound' in str(e):
            print(f"Security group '{security_group_name}' not found.")
        else:
            raise

def delete_dns_record(domain_name, subdomains):
    route53 = boto3.client('route53')
    hosted_zone_id = get_hosted_zone_id(route53, domain_name)

    if not hosted_zone_id:
        print(f"Hosted zone for '{domain_name}' not found.")
        return

    resp = route53.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    records = resp['ResourceRecordSets']

    change = []

    for record in records:
        name = record['Name'].split('.')[0]
        if name in subdomains:
            print(f"Deleting DNS record for '{name}'...")
            change.append({'Action': 'DELETE', 'ResourceRecordSet': record})

    route53.change_resource_record_sets(HostedZoneId=hosted_zone_id, ChangeBatch={'Changes':change})

    print(f"DNS records deleted.")

def get_hosted_zone_id(route53_client, domain_name):
    response = route53_client.list_hosted_zones_by_name(DNSName=domain_name)
    for hosted_zone in response['HostedZones']:
        if hosted_zone['Name'] == f"{domain_name}.":
            return hosted_zone['Id']
    return None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python terminate_script.py <course_name>")
        sys.exit(1)

    course_name = sys.argv[1]

    delete_course_resources(course_name)

