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
