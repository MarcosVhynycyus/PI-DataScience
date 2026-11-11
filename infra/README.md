

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
[monitoring]
devops-1 ansible_host=<IP_DEVOPS-1>

[simulator]
devops-2 ansible_host=<IP_DEVOPS-2>

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


# Infraestrutura do Espaço MR

## Visão geral

A infraestrutura utiliza OpenTofu, QEMU/KVM, libvirt,
cloud-init e Ansible para provisionar e administrar
duas máquinas virtuais Ubuntu Server 24.04.

- devops-1: monitoramento e Grafana (planejado).
- devops-2: execução do simulador de dados (planejado).

Cada VM possui 1 vCPU, 1 GB de RAM e disco de 10 GB.

## Pré-requisitos

No computador hospedeiro:

- Linux com virtualização KVM disponível.
- QEMU/libvirt com rede e pool chamados "default".
- OpenTofu e Ansible instalados.
- Cliente SSH e chave SSH Ed25519.

O ambiente foi testado no Linux Mint com KVM/libvirt.

## Preparação da chave SSH

Caso ainda não exista uma chave para este laboratório:

ssh-keygen -t ed25519 -f ~/.ssh/devops_lab

O arquivo variables.tf permite informar outro caminho
pela variável ssh_key_path.

## Provisionamento

A partir da raiz do repositório:

cd infra/iac
tofu init
tofu validate
tofu plan
tofu apply

A imagem Ubuntu é obtida automaticamente pelo OpenTofu.

Os endereços MAC podem ser definidos localmente por
terraform.tfvars. Caso não sejam informados, o libvirt
poderá gerá-los.

Para consultar os endereços IP:

tofu output ips

## Configuração inicial

O cloud-init configura o usuário marcos e sua chave SSH.

O OpenTofu gera automaticamente:

infra/ansible/inventory.ini

Esse arquivo contém os IPs utilizados pelo Ansible.

## Testar o Ansible

A partir da raiz do repositório:

ansible all -i infra/ansible/inventory.ini -m ping

Ambas as máquinas devem retornar "pong".

O playbook infra/ansible/playbooks/setup.yml contém
a preparação do ambiente, mas sua execução ainda
precisa ser validada nesta configuração.

## Arquivos locais

Os arquivos terraform.tfstate, terraform.tfvars,
.terraform/ e o inventário gerado não devem ser
versionados.

Cada integrante utiliza seu próprio estado local.

## Observações

A infraestrutura foi validada no laboratório com
duas VMs, OpenTofu, cloud-init, SSH e Ansible.

A reprodução integral em outros computadores
ainda não foi testada.

A instalação de Docker, Grafana e do simulador
será realizada nas próximas etapas.


## Comando para resetar as VM's

```
sudo virsh destroy devops-1
sudo virsh destroy devops-2

sudo virsh undefine devops-1 --remove-all-storage --nvram
sudo virsh undefine devops-2 --remove-all-storage --nvram

sudo virsh list --all

```