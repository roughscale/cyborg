import boto3
import json
from pprint import pprint

session = boto3.Session(profile_name='default')
vpc_client = session.client('ec2')

#vpcs = vpc_client.describe_vpcs()
learn_vpc = vpc_client.describe_vpcs(
         Filters=[
           {
            'Name': 'tag:Name',
            'Values': [
                'learn',
            ]
          },
         ]
       )

# get target VPC
target_vpc = vpc_client.describe_vpcs(
         Filters=[
           {
            'Name': 'tag:Name',
            'Values': [
                'target',
            ]
          },
         ]
       )
# vpcs should return only 1 VPC
learn_vpc_id = learn_vpc["Vpcs"][0]["VpcId"]
target_vpc_id = target_vpc["Vpcs"][0]["VpcId"]

subnets = {}
hosts = {}

def get_tag_name(tags):
    tag_names = [ tag["Value"] for tag in tags for k,v in tag.items() if k == 'Key' and v == 'Name']
    return(tag_names)[0]

for vpc_id in [ learn_vpc_id, target_vpc_id]:
  # get all instances in vpc
  instances_list = vpc_client.describe_instances(
        Filters=[
            {
              'Name': 'vpc-id',
              'Values': [
                  vpc_id,
                  ]
              },
            ]
        )

  host_list = {}

  instances = [ i for r in instances_list["Reservations"] for i in r["Instances"] ]


  for inst in instances:
    inst_name = get_tag_name(inst["Tags"])
    host_list[inst["InstanceId"]] = inst_name

  # get all subnets in vpc
  subnets_list = vpc_client.describe_subnets(
        Filters=[
            {
              'Name': 'vpc-id',
              'Values': [
                  vpc_id,
                  ]
              },
            ]
        )

  for subnet in subnets_list["Subnets"]:
    subnet_id = subnet["SubnetId"]
    subnet_tags = subnet["Tags"]
    subnet_cidr = subnet["CidrBlock"]
    subnet_name = get_tag_name(subnet_tags)
    subnets[subnet_name] = subnet_cidr
    hosts[subnet_name] = {}

    # get all ip addresses in vpc subnets
    list_nics = vpc_client.describe_network_interfaces(
        Filters=[
            {
              'Name': 'subnet-id',
              'Values': [
                  subnet_id,
                  ]
              },
            ]
        )

    attached_nics = [ attach for attach in list_nics["NetworkInterfaces"] if "Attachment" in attach]
    for nic in attached_nics:
          nic_instance_id =nic["Attachment"]["InstanceId"]
          #print(nic_instance_id)
          nic_hostname = host_list[nic_instance_id]
          nic_ip_address = nic["PrivateIpAddress"]
          #print(nic_ip_address,nic_hostname)
          hosts[subnet_name][nic_hostname] = nic_ip_address

json_output = { "subnets": subnets, "hosts": hosts }
print(json.dumps(json_output))
