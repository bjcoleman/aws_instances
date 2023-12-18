#!/bin/bash

# This script installs the public keys for all users in the specified course
# on all running EC2 instances with the 'course' tag set to the specified course name.
# It should be run after create_instance.py

# Configuration
# * Set the PRIVATE_KEY_PATH variable to the path of the key that has access to the EC2 instances
# * Set the DOMAIN variable to the domain name of the EC2 instances
PRIVATE_KEY_PATH="~/.ssh/coleman-moravian.pem"
DOMAIN="moraviancs.click"

# This script was written by ChatGPT3.5

# Check if the number of arguments is correct
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <course_name> <keys_folder>"
    exit 1
fi

# Extract arguments
COURSE_NAME="$1"
KEYS_FOLDER="$2"

# Validate that the keys folder exists
if [ ! -d "$KEYS_FOLDER" ]; then
    echo "Error: Keys folder '$KEYS_FOLDER' not found."
    exit 1
fi

# Disable host key checking in SSH
SSH_OPTIONS="-o StrictHostKeyChecking=no"

# Get a list of running EC2 instances with the 'course' tag set to the specified course name
INSTANCE_IDS=$(aws ec2 describe-instances --filters "Name=tag:course,Values=$COURSE_NAME" "Name=instance-state-name,Values=running" --query "Reservations[*].Instances[*].InstanceId" --output text)

# Loop through each running instance
for INSTANCE_ID in $INSTANCE_IDS; do
    # Get the value of the 'Name' tag for the current instance
    USERNAME=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query "Reservations[*].Instances[*].Tags[?Key=='Name'].Value" --output text)

    # Check if a public key file exists for the current user
    PUBLIC_KEY_FILE="$KEYS_FOLDER/$USERNAME.pub"
    if [ -e $PUBLIC_KEY_FILE ]; then
        # Read the public key
        PUBLIC_KEY=$(cat $PUBLIC_KEY_FILE)

        # Construct the hostname
        HOSTNAME="${USERNAME}.moraviancs.click"

        # SSH into the instance and append the public key to the authorized_keys file
        SSH_OUTPUT=$(ssh $SSH_OPTIONS -i $PRIVATE_KEY_PATH ec2-user@${HOSTNAME} "echo '$PUBLIC_KEY' >> ~/.ssh/authorized_keys" 2>&1)
        if [ $? -eq 0 ]; then
            echo "Public key added for user $USERNAME on running instance $HOSTNAME"
        else
            echo "Error adding public key for user $USERNAME on running instance $HOSTNAME. SSH error: $SSH_OUTPUT"
        fi
    else
        echo "Public key file not found for user $USERNAME"
    fi
done
