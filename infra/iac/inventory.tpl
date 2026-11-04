[monitoring]
devops-1 ansible_host=${ips["devops-3"]}

[simulator]
devops-1 ansible_host=${ips["devops-4"]}

[all:vars]
ansible_user=marcos
ansible_ssh_private_key_file=~/.ssh/devops_lab
ansible_ssh_common_args='-o StrictHostKeyChecking=no'
ansible_python_interpreter=/usr/bin/python3