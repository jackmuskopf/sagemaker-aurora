# Sagemaker-Aurora management tool

## Requirements
 - Python 3
 - - boto3
 - Terraform 12
 - AWS profile with access to target account
 - Make (optional -- see Makefile for bash commands)
 - existing S3 bucket for holding Terraform state files

## Configuration
Create a file in the root directory named `configuration.yaml`.  Paste this into the contents and update the variables to fit your VPC, Subnets, and other configurations.

```
state_bucket: my-tf-state-bucket
state_key: sgmkr-aurora.tfstate
aws_profile: default
app_name: aurora-sgmkr
stage: develop
vpc_id: vpc-xxxxxxx
sgmkr_subnet: subnet-aaaaaaa
aurora_subnets:
  - subnet-bbbbbbb
  - subnet-ccccccc
db_name: main
db_port: 5432
db_username: postgres
db_password: "CHANGE_ME!!!!"
```

## Usage


