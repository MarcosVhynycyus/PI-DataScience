[monitoring]
devops-1 ansible_host=${ips["devops-1"]}

[simulator]
devops-2 ansible_host=${ips["devops-2"]}

[all:vars]
ansible_user=marcos
ansible_ssh_private_key_file=${ssh_key_path}
ansible_ssh_common_args='-o StrictHostKeyChecking=accept-new'
ansible_python_interpreter=/usr/bin/python3
