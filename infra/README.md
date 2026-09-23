

# Ambiente: Fedora + KVM/QEMU + OpenTofu (`dmacvicar/libvirt`) + Ansible


## 1. Preparação do Host (Fedora)

### 1.1 Verificar KVM/libvirt e permissões

```bash
sudo systemctl enable --now libvirtd
sudo systemctl status libvirtd

# checar se a CPU suporta virtualização
lscpu | grep -i virtualization

# adicionar seu usuário aos grupos necessários
sudo usermod -aG libvirt,kvm $USER
newgrp libvirt   # ou faça logout/login para aplicar

# testar acesso sem sudo
virsh list --all
```

Se `virsh list --all` retornar sem erro de permissão, o acesso está correto.

### 1.2 Gerar a chave SSH exigida pelo cloud-init

```bash
ssh-keygen -t ed25519 -f ~/.ssh/devops_lab -N "" -C "devops-lab"
chmod 600 ~/.ssh/devops_lab
```

O arquivo `cloud_init.cfg` já referencia `~/.ssh/devops_lab.pub` — confirme que o caminho bate exatamente com o gerado.

### 1.3 Verificar a imagem base

```bash
ls infra/iaac/*.img 2>/dev/null || \
  wget -P infra/iaac https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
```

Confirme no `main.tf` se o `pool` do libvirt aponta para um diretório com permissão de escrita (ex: `/var/lib/libvirt/images` ou um pool próprio do seu usuário).

---

## 2. Provisionamento com OpenTofu

```bash
cd infra/iaac

tofu init
tofu validate
tofu plan -out=plan.tfplan
tofu apply plan.tfplan
```

### 2.1 Verificar as VMs criadas

```bash
virsh list --all
# devops-1, devops-2, devops-3, devops-4 devem aparecer "running"
```

### 2.2 Capturar os IPs

Se o `main.tf` já expõe `outputs`:

```bash
tofu output
tofu output -json > ../ansible/ips.json
```

Se o output não vier populado (comum com libvirt na primeira execução, pois o DHCP demora alguns segundos), use:

```bash
for vm in devops-1 devops-2 devops-3 devops-4; do
  echo -n "$vm: "
  virsh domifaddr "$vm" --source agent 2>/dev/null | awk '/ipv4/{print $4}' || \
  virsh net-dhcp-leases default | grep "$vm"
done
```

Guarde os 4 IPs — serão usados no inventário do Ansible.

---

## 3. Configuração e Automação com Ansible

### 3.1 `infra/ansible/inventory.ini`

```ini
[masters]
devops-1 ansible_host=<IP_DEVOPS_1>

[workers]
devops-2 ansible_host=<IP_DEVOPS_2>
devops-3 ansible_host=<IP_DEVOPS_3>
devops-4 ansible_host=<IP_DEVOPS_4>

[all:vars]
ansible_user=marcos
ansible_ssh_private_key_file=~/.ssh/devops_lab
ansible_ssh_common_args='-o StrictHostKeyChecking=no'
ansible_python_interpreter=/usr/bin/python3
```

Teste de conectividade:

```bash
cd infra/ansible
ansible -i inventory.ini all -m ping
```

### 3.2 `infra/ansible/playbooks/setup.yml`


```
---
- name: Preparar todas as VMs (Docker)
  hosts: all
  become: true
  tasks:
    - name: Atualizar cache apt
      ansible.builtin.apt:
        update_cache: true

    - name: Instalar dependências
      ansible.builtin.apt:
        name: [ca-certificates, curl, gnupg]
        state: present

    - name: Criar diretório de chaves apt
      ansible.builtin.file:
        path: /etc/apt/keyrings
        state: directory
        mode: "0755"

    - name: Adicionar chave GPG do Docker
      ansible.builtin.get_url:
        url: https://download.docker.com/linux/ubuntu/gpg
        dest: /etc/apt/keyrings/docker.asc
        mode: "0644"

    - name: Adicionar repositório Docker
      ansible.builtin.apt_repository:
        repo: "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable"
        filename: docker

    - name: Instalar Docker Engine
      ansible.builtin.apt:
        name: [docker-ce, docker-ce-cli, containerd.io]
        update_cache: true
        state: present

    - name: Adicionar marcos ao grupo docker
      ansible.builtin.user:
        name: marcos
        groups: docker
        append: true

    - name: Garantir serviço Docker ativo
      ansible.builtin.systemd:
        name: docker
        state: started
        enabled: true

- name: Configurar VM de Big Data
  hosts: bigdata
  become: true
  tasks:
    - name: Criar diretórios para datalake/datawarehouse
      ansible.builtin.file:
        path: "{{ item }}"
        state: directory
        owner: marcos
        mode: "0755"
      loop:
        - /opt/bigdata/datalake
        - /opt/bigdata/datawarehouse

- name: Configurar VM de ETL
  hosts: etl
  become: true
  tasks:
    - name: Criar diretório da pipeline de ETL
      ansible.builtin.file:
        path: /opt/etl
        state: directory
        owner: marcos
        mode: "0755"

- name: Configurar VM de Monitoramento
  hosts: monitoring
  become: true
  tasks:
    - name: Criar diretório de configuração do monitoramento
      ansible.builtin.file:
        path: /opt/monitoring
        state: directory
        owner: marcos
        mode: "0755"

- name: Configurar VM do Simulador
  hosts: simulator
  become: true
  tasks:
    - name: Instalar Python3 e dependências necessárias
      apt:
        name:
          - python3 
          - python3-pip 
          - python3-pandas 
        state: present 
        update_cache: yes

    - name: Instalar a biblioteca Faker via pip
      pip:
        name: faker
        state: present
        extra_args: "--break-system-packages"

    - name: Criar diretório do simulador de dados
      ansible.builtin.file:
        path: /opt/simulator
        state: directory
        owner: marcos
        mode: "0755"
```

Execução:

```bash
ansible-playbook -i inventory.ini playbooks/setup.yml
```
