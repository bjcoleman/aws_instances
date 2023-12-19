
## AWS Instances for Class

This project automates the process of creating and destroying a set of
VMs on AWS EC2 for each student in a class.  The VMs have the following properties:

* Amazon Linux 2 OS
* SSH (22), HTTP (80) and HTTPS (443) ports open
* instructor SSH public key installed on each machine
* student SSH public key installed on individual machine for that student
* DNS subdomain <student_id>.moraviancs.click registered to the IP address for the machine

The repo contains three scripts:

### `make_instances.py`

This script takes a `course_name` and `class_list` as its command line parameters.

* `course_name` - The name of the course.  This will be used to tag all the instances for later deletion
* `class_list` - This is a file that contains unique names for each students.  Email usernames or some other
  unique identifier are good choices.

This script will:

1. Identify the most recent AMI for Amazon Linux 2
2. Create a security group for all instances (allows SSH/HTTP/HTTPS traffic)
3. Launch instances for each student
4. Register each machine IP with the corresponding subdomain

### `install_keys.sh`

This script takes `COURSE_NAME` and `KEY_FOLDER` as parameters.

* `COURSE_NAME` is used to look up all EC2 instances
* `KEY_FOLDER` is the location of the *public* SSH keys for each student.  Each key should be of the form `<name>.pub` where the `<name>` is the name from the `class_list` used in `make_instances.py`.

The script will:

* Obtain a list of EC2 instances in the course
* For each instance, copy the corresponding public SSH key into `~ec2-user/.ssh/authorized_keys`
* Report any instances for which there is no key.

After this script runs, students will be able to into their machine using their 
private key.  For example, a student with the name "bauer" and a private key `id_rsa` in their `.ssh` folder would use:

```
ssh -i ~/.ssh/id_rsa ec2-user@bauer.moraviancs.click
```

### `terminate_instances.py`

This script takes `course_name` as a command-line parameter.

* `course_name` - The name of the course used in `create_instances.py`.

This script will

1. Identify all EC2 instances in the course and terminate them
2. Delete the security group
3. Delete the DNS records


### Configuration

Before you use this system, you will need to:

* Install the AWS CLI and configure your AWS credientials.  Run `aws configure`.
* Create a virtual environment and install the requirements in `requirements.txt`
* Edit script parameters for each script:
  * `create_instances.py`: `key_name` - the name of the AWS SSH key to use when instnaces are created
  * `create_instances.py`: `domain_name` - the base domain name for all DNS entries
  * `create_instances.py`: `instance_type` - the type of EC2 instance to create
  * `install_keys.sh`: `PRIVATE_KEY_PATH` - the path to the private key that matches the key specifed as `key_name` in `create_instances.py`
  * `install_keys.sh`: `DOMAIN` - the base domain name for all DNS entries
  * `terminate_instances.py`: `domain_name` - the base domain name for all DNS entries
* Collect *public* SSH keys from each student and place them in a folder.  Each 
  file should be named `<name>.pub` to match the names in the file used with `create_instances.py`.



### TODOs

* check what happens if there is a duplicate name in the `class_list`
* Create scripts you can put in `~/bin` to call pythong in the `venv`


## SSH Config

If you create instances for students more than once, SSH will fail because the IP
and SSH hash are different.  To avoid this, have students add the following to
`~/.ssh/config`:

```
Host *.moraviancs.click
        StrictHostKeyChecking no
        UserKnownHostsFile=/dev/null
        LogLevel ERROR
```

The first configuration option turns off the check of the hash (usually you
have to type "yes" to continue).  Even without this check, SSH writes the
hash to the `known_hosts` file, so the second option redirects this to a 
non-file.  The third option turns off all warnings, which in this case
disables the warning, "Warning: Permanently added '<hostname>' (ED25519) 
to the list of known hosts."

Admittedly, this isn't the most secure approach.  In theory, it opens 
students for man-in-the-middle style attacks because we are not verifying
SSH hashes.  But since students generally type "yes" to the prompt without
checking, this is not a significant change.

### References

* [How to disable Host Key Checking check on git over ssh?](https://unix.stackexchange.com/questions/724693/how-to-disable-host-key-checking-check-on-git-over-ssh)
* [How do I skip the "known_host" question the first time I connect to a machine via SSH with public/private keys?](https://superuser.com/questions/19563/how-do-i-skip-the-known-host-question-the-first-time-i-connect-to-a-machine-vi)
* [Disable "Permanently added <host> ..." warning on local LAN](https://superuser.com/questions/1005055/disable-permanently-added-host-warning-on-local-lan)
* [SSH into a box with a frequently changed IP](https://serverfault.com/questions/193631/ssh-into-a-box-with-a-frequently-changed-ip) - I didn't use this technique because we redirect `known_hosts` to `/dev/null`, but I saved it for completeness.