# Infraestrutura do Espaço MR

Guia para preparar o host, provisionar as VMs com OpenTofu, configurar os
serviços com Ansible e iniciar o simulador. Os comandos são executados no
**computador hospedeiro, na raiz do repositório**, salvo indicação contrária.

Para uma instalação nova, siga as etapas 1 a 7. Se as VMs já existem, siga a
[manutenção do ambiente existente](#8-manutenção-do-ambiente-existente).

## 1. Arquitetura e requisitos

| VM | Grupo Ansible | Recursos | Serviços |
| --- | --- | --- | --- |
| `devops-1` | `monitoring` | 1 vCPU, 1 GiB RAM, disco de 10 GiB | Grafana em Docker; Prometheus e firewall de métricas em systemd. |
| `devops-2` | `simulator` | 1 vCPU, 1 GiB RAM, disco de 10 GiB | Node Exporter; PostgreSQL, API Flask/Gunicorn, gerador Python e Adminer em Docker. |

O host precisa de Linux x86_64 com virtualização Intel VT-x/AMD-V habilitada,
KVM/QEMU, libvirt, OpenTofu, Ansible, Python 3 e cliente SSH. Reserve os recursos
das duas VMs, além dos utilizados pelo próprio host; o armazenamento precisa
acomodar os dois discos, a imagem base e os arquivos de estado.

O host e as VMs precisam de acesso à internet para baixar providers, imagem
Ubuntu, pacotes APT, imagens Docker e dependências Python. Docker é instalado
**nas VMs** pelo Ansible; não é obrigatório no host para executar o ambiente.

As VMs são Ubuntu Server **24.04 amd64**. Essa versão está vinculada à imagem
cloud e ao repositório Docker do playbook. O usuário das VMs é **`marcos`**, com
SSH por chave e `sudo` sem senha, conforme o cloud-init; ele independe do nome
do usuário no computador hospedeiro.

Responsabilidades e arquivos:

```text
infra/
├── iac/
│   ├── main.tf                    # VMs, discos, imagem base e inventário
│   ├── variables.tf               # Chave SSH e MACs opcionais
│   ├── cloud_init.cfg             # Usuário, SSH e hostname das VMs
│   ├── network_config.cfg         # Modelo auxiliar; não referenciado em main.tf
│   ├── inventory.tpl              # Inventário gerado a partir dos IPs das VMs
│   └── .terraform.lock.hcl         # Versões e checksums dos providers
└── ansible/
    ├── inventory.ini              # Gerado pelo OpenTofu; específico do ambiente
    ├── group_vars/all/monitoring.yml
    ├── playbooks/setup.yml         # Configuração completa; importa monitoring.yml
    ├── playbooks/monitoring.yml    # Monitoramento de VMs já preparadas
    ├── templates/monitoring-compose.yml.j2
    └── roles/
        ├── node_exporter/
        ├── prometheus/
        ├── grafana_provisioning/
        ├── metrics_firewall/
        ├── simulator/
        └── simulator_metrics/
```

O OpenTofu administra recursos de infraestrutura. O Ansible administra pacotes,
serviços, implantação do simulador e configuração do monitoramento.

## 2. Preparar o host

### 2.1 Instalar ferramentas

No **Fedora**:

```bash
sudo dnf install qemu-kvm qemu-img libvirt libvirt-client \
  libvirt-daemon-config-network virt-install genisoimage \
  ansible-core opentofu python3 openssh-clients git curl
```

O [OpenTofu está disponível no repositório do Fedora](https://opentofu.org/docs/intro/install/fedora/).
O pacote `genisoimage` fornece `mkisofs`, necessário para gerar o disco cloud-init
com o [provider libvirt 0.8.3 usado neste projeto](https://github.com/dmacvicar/terraform-provider-libvirt/blob/v0.8.3/libvirt/cloudinit_def.go).

Como alternativa, no **Ubuntu/Debian/Linux Mint**:

```bash
sudo apt-get update
sudo apt-get install qemu-kvm qemu-utils libvirt-daemon-system libvirt-clients \
  genisoimage ansible-core python3 openssh-client git curl
```

Nessas distribuições, instale também o OpenTofu pelo
[procedimento oficial para pacotes DEB](https://opentofu.org/docs/intro/install/deb/).
As distribuições do host não alteram o sistema operacional das VMs.

### 2.2 Habilitar libvirt e conferir KVM

Em uma instalação nova que utiliza daemons modulares, como as versões atuais
do Fedora:

```bash
sudo systemctl enable --now virtqemud.socket virtnetworkd.socket \
  virtstoraged.socket virtsecretd.socket virtnodedevd.socket virtnwfilterd.socket \
  virtproxyd.socket virtlogd.socket virtlockd.socket
```

Se o host utiliza o daemon tradicional `libvirtd`, mantenha esse modo e use:

```bash
sudo systemctl enable --now libvirtd.service
```

Use o modo já configurado no host. A
[documentação do libvirt](https://libvirt.org/daemons.html) explica como identificar
os daemons ativos; não é necessário migrar o modo para executar este projeto.

Confira a virtualização e as ferramentas:

```bash
lscpu
ls -l /dev/kvm
virt-host-validate qemu
command -v tofu ansible-playbook virsh mkisofs
```

Os testes de KVM precisam passar. Se a virtualização estiver desabilitada,
configure-a na BIOS/UEFI; em um host que também seja uma VM, é necessário que
o hipervisor disponibilize virtualização aninhada.

### 2.3 Permitir acesso ao libvirt

```bash
sudo usermod -aG libvirt,kvm "$USER"
```

Encerre a sessão e entre novamente para atualizar os grupos. Depois confira:

```bash
id
virsh -c qemu:///system list --all
```

Esse último comando precisa funcionar com o usuário que executará o OpenTofu.
Todos os comandos `virsh` deste guia usam **`qemu:///system`**, a mesma conexão
do provider. A conexão `qemu:///session` mostra outro ambiente.

### 2.4 Conferir rede e armazenamento

O código espera uma rede e um pool de armazenamento chamados **`default`**:

```bash
virsh -c qemu:///system net-list --all
virsh -c qemu:///system net-info default
virsh -c qemu:///system pool-list --all
virsh -c qemu:///system pool-info default
```

Se a rede existir, mas estiver inativa, inicie-a:

```bash
virsh -c qemu:///system net-start default
```

Se a rede não estiver definida, uma instalação padrão do libvirt fornece seu
modelo em `/usr/share/libvirt/networks/default.xml`. Somente nesse caso:

```bash
virsh -c qemu:///system net-define /usr/share/libvirt/networks/default.xml
virsh -c qemu:///system net-start default
```

Se o pool existir e estiver inativo, use `pool-start default`. Se ele
**não existir**, crie um pool de diretório:

```bash
sudo install -d -m 0755 /var/lib/libvirt/images
virsh -c qemu:///system pool-define-as default dir --target /var/lib/libvirt/images
virsh -c qemu:///system pool-start default
```

Habilite o início automático da rede e do pool, inclusive se já estavam ativos:

```bash
virsh -c qemu:///system net-autostart default
virsh -c qemu:///system pool-autostart default
```

A rede fornece NAT e DHCP. Os endereços são descobertos pelo OpenTofu e gravados
no inventário; não há IP fixo no código. Um MAC estável não é uma reserva de IP.

## 3. Preparar repositório, chave SSH e variáveis

Se ainda não tiver uma cópia do projeto:

```bash
git clone https://github.com/MarcosVhynycyus/PI-DataScience.git
cd PI-DataScience
```

Se já tiver uma cópia, abra um terminal na raiz dela. O diretório correto dos
arquivos OpenTofu é **`infra/iac`**.

Confira se já existe a chave do laboratório:

```bash
ls -l ~/.ssh/devops_lab ~/.ssh/devops_lab.pub
```

Somente se ela não existir, crie-a:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/devops_lab -C devops-lab
chmod 600 ~/.ssh/devops_lab
```

Preserve a chave usada pelas VMs existentes. Se houver passphrase, carregue a
chave em um agente SSH ativo antes de executar Ansible:

```bash
ssh-add ~/.ssh/devops_lab
```

As variáveis estão em `infra/iac/variables.tf`:

| Variável | Padrão | Uso |
| --- | --- | --- |
| `ssh_key_path` | `~/.ssh/devops_lab` | Caminho da chave privada no host; o arquivo `.pub` correspondente também precisa existir. |
| `vm_macs` | `null` | Lista opcional de exatamente dois MACs, na ordem `devops-1`, `devops-2`. |

Para usar outra chave, crie `infra/iac/terraform.tfvars` com o caminho real, por
exemplo:

```hcl
ssh_key_path = "~/.ssh/minha_chave_do_laboratorio"
```

Se precisar manter MACs já utilizados, informe os valores existentes em
`vm_macs`; consulte-os com `virsh -c qemu:///system domiflist devops-1` e o mesmo
comando para `devops-2`. O nome do host, a quantidade de VMs e seus recursos
estão definidos em `main.tf`, não em variáveis de entrada.

## 4. Provisionar as duas VMs

Esta etapa é para uma instalação nova ou uma mudança de infraestrutura revisada.
Se as VMs já existem, conserve o estado OpenTofu correspondente e confira-o antes
de planejar mudanças. Uma cópia nova do Git não contém esse estado local.

```bash
tofu -chdir=infra/iac init
tofu -chdir=infra/iac fmt -check -diff
tofu -chdir=infra/iac validate
tofu -chdir=infra/iac plan -out=plan.tfplan
```

Revise o plano antes de aplicá-lo. Em uma instalação nova, ele cria os discos,
as duas VMs, os discos cloud-init e o inventário. Em um ambiente existente,
investigue qualquer exclusão ou substituição de recursos antes de continuar.

Para executar o plano revisado:

```bash
tofu -chdir=infra/iac apply plan.tfplan
tofu -chdir=infra/iac output ips
virsh -c qemu:///system list --all
```

São esperadas **`devops-1` e `devops-2`** em execução. A imagem Ubuntu 24.04 é
baixada automaticamente da URL definida em `main.tf`; não é necessário baixar
uma imagem para a pasta do projeto. O arquivo auxiliar `network_config.cfg`
não é passado ao recurso cloud-init atual; a imagem utiliza DHCP.

O inventário é gerado automaticamente em `infra/ansible/inventory.ini`:

```bash
cat infra/ansible/inventory.ini
ansible-inventory -i infra/ansible/inventory.ini --graph
```

Ele associa `devops-1` ao grupo `monitoring`, `devops-2` ao grupo `simulator`,
configura o usuário `marcos`, a chave escolhida e o Python da VM. A política
SSH é `StrictHostKeyChecking=accept-new`: aceita hosts novos e verifica as
identidades conhecidas nas conexões seguintes.

Espere o SSH e o cloud-init antes de instalar pacotes:

```bash
ansible all -i infra/ansible/inventory.ini \
  -m ansible.builtin.wait_for_connection -a 'timeout=300'
ansible all -i infra/ansible/inventory.ini --become \
  -m ansible.builtin.command -a 'cloud-init status --wait'
ansible all -i infra/ansible/inventory.ini -m ansible.builtin.ping
```

O cloud-init deve concluir com `status: done`; ambas as VMs devem responder
`pong`. Se houver falha, consulte a seção de diagnóstico antes de continuar.

## 5. Implantar o ambiente com Ansible

Com as duas VMs ligadas e o inventário gerado pelo OpenTofu, execute a partir
da raiz do repositório:

```bash
ansible-playbook -i infra/ansible/inventory.ini infra/ansible/playbooks/setup.yml
```

O playbook aguarda SSH e cloud-init, atualiza pacotes pelo APT e instala
Docker Engine, Compose e Buildx nas duas VMs. Ele envia os arquivos de
`simulator/` para a VM geradora, constrói as imagens e inicia PostgreSQL, API,
gerador e Adminer. A execução aguarda as seis tabelas e confirma que a API
retorna vendas.

O mesmo comando instala Node Exporter e Prometheus, sobe o Grafana e
provisiona a fonte Prometheus e o dashboard **Monitoramento — VM Geradora**.
O playbook verifica os targets `UP`, a geração de dados, a comunicação entre
Grafana e Prometheus e o carregamento do dashboard.

As portas padrão são 3000 para Grafana, 9090 para Prometheus, 9100 para Node
Exporter e 8000 para as métricas do gerador. As métricas são habilitadas por
padrão para o IP da VM de monitoramento mostrado no inventário. As variáveis
compartilhadas estão em [monitoring.yml](ansible/group_vars/all/monitoring.yml).

## 6. Localizar o projeto e os dados do simulador

O diretório padrão é `/opt/simulator` e o volume do PostgreSQL se chama
`simulator_postgres_data`. Se os containers já existem, o playbook usa o
diretório e o nome do projeto registrados pelo Compose, inclusive para
containers parados. Arquivos de código alterados na VM recebem backup e as
variáveis de métricas são atualizadas no bloco gerenciado do `.env`.

O gerador inicializa as tabelas e passa a produzir dados em ciclos de cinco
segundos, com inconsistências sintéticas configuradas no Compose. O endereço
`SIMULATOR_API_URL` exibido pelo playbook pode ser usado para renderizar o
relatório. [Pipeline ETL](../pipeline/README.md)

## 7. Acessar e validar os serviços

Consulte os IPs atuais no inventário. Na tabela, `<IP_MONITORING>` é o
`ansible_host` de `devops-1`, e `<IP_SIMULATOR>` é o de `devops-2`.

| Serviço | Acesso padrão | Observação |
| --- | --- | --- |
| Grafana | `http://<IP_MONITORING>:3000` | Usuário inicial `admin`. |
| Dashboard | `http://<IP_MONITORING>:3000/d/vm-geradora` | Também em Dashboards → Infraestrutura. |
| Prometheus | `http://<IP_MONITORING>:9090` | Acesso do host KVM e das redes Docker do Grafana. |
| Targets | `http://<IP_MONITORING>:9090/targets` | `vm-geradora` deve estar UP; `aplicacao-geradora` quando habilitado. |
| Node Exporter | `http://<IP_SIMULATOR>:9100/metrics` | Acesso restrito à VM de monitoramento. |
| Métricas da aplicação | `http://<IP_SIMULATOR>:8000/metrics` | Quando habilitadas pelo Ansible; somente o monitoramento é permitido. |
| API | `http://<IP_SIMULATOR>:5000/health` | Valida a conexão com PostgreSQL. |
| Adminer | `http://<IP_SIMULATOR>:8080` | Interface de consulta ao banco. |
| PostgreSQL | `<IP_SIMULATOR>:5432` | Banco `varejo_db`, usuário `user`, senha `password`. |

As credenciais do PostgreSQL são as de laboratório definidas no Compose. No
Adminer, selecione PostgreSQL e use **servidor `db`**, pois ele se conecta pela
rede interna dos containers.

Consulte a senha inicial gerada do Grafana:

```bash
ansible monitoring -i infra/ansible/inventory.ini --become \
  -m ansible.builtin.command -a 'cat /opt/monitoring/grafana_admin_password'
```

Se a senha já foi alterada na interface, utilize a senha atual. O arquivo define
somente a senha inicial; sua leitura não redefine as credenciais.

Verifique serviços, configuração, métricas e saúde:

```bash
ansible all -i infra/ansible/inventory.ini \
  -m ansible.builtin.command -a 'systemctl is-active docker'
ansible simulator -i infra/ansible/inventory.ini \
  -m ansible.builtin.command -a 'systemctl is-active prometheus-node-exporter'
ansible monitoring -i infra/ansible/inventory.ini \
  -m ansible.builtin.command -a 'systemctl is-active prometheus'
ansible monitoring -i infra/ansible/inventory.ini --become \
  -m ansible.builtin.command -a 'promtool check config /etc/prometheus/prometheus.yml'
ansible monitoring -i infra/ansible/inventory.ini \
  -m ansible.builtin.uri \
  -a 'url=http://{{ hostvars[groups["simulator"][0]].ansible_host }}:9100/metrics'
ansible monitoring -i infra/ansible/inventory.ini \
  -m ansible.builtin.uri -a 'url=http://127.0.0.1:9090/api/v1/targets'
ansible monitoring -i infra/ansible/inventory.ini \
  -m ansible.builtin.uri -a 'url=http://127.0.0.1:3000/api/health'
```

A resposta do Grafana deve conter `database: ok`; os targets gerenciados devem
ter `health: up`. As taxas no dashboard precisam de algumas coletas para aparecer.
A seção da aplicação fica sem dados enquanto a opção correspondente estiver
desabilitada.

O Ansible mantém regras de acesso na cadeia IPv4 `MR-VM-METRICS`, persistidas
pelo serviço `vm-metrics-firewall`. A porta 9100 aceita somente o monitoramento;
a 9090 aceita acesso local, o host KVM e as sub-redes Docker do Grafana. Para
acessar a UI do Prometheus de outro cliente, acrescente seu IP/CIDR a
`prometheus_ui_allowed_sources` e reaplique o monitoramento. A opção não libera
9100 nem altera a publicação de 3000. Os detalhes estão no
[guia de monitoramento](../monitoring/README.md).

## 8. Manutenção do ambiente existente

Reexecute `setup.yml` para atualizar pacotes, reaplicar o código do simulador
e reconciliar a configuração dos serviços nos dois grupos. Os volumes do
PostgreSQL e do Grafana são reutilizados. Quando o DHCP mudar, atualize o
inventário antes de executar o playbook.

Para reaplicar somente o monitoramento com Docker e o simulador já
disponíveis, execute:

```bash
ansible-playbook -i infra/ansible/inventory.ini infra/ansible/playbooks/monitoring.yml
```

Em uma instalação antiga sem métricas do gerador, execute o fluxo completo
para atualizar o simulador ou passe `-e simulator_metrics_enabled=false`
para coletar as métricas da VM. O monitoramento consulta as duas VMs para
verificar os targets. [Monitoramento](../monitoring/README.md)

### 8.1 Iniciar após desligar o computador

O código OpenTofu não habilita autostart das VMs. Para iniciá-las manualmente,
depois que libvirt, rede e pool estiverem disponíveis:

```bash
virsh -c qemu:///system start devops-1
virsh -c qemu:///system start devops-2
```

Execute `start` somente nas VMs desligadas. Para habilitar início automático
dessas VMs junto com libvirt:

```bash
virsh -c qemu:///system autostart devops-1
virsh -c qemu:///system autostart devops-2
```

No modo modular, habilite também o daemon QEMU no boot para que o autostart das
VMs não dependa de uma primeira conexão de cliente:

```bash
sudo systemctl enable virtqemud.service
```

Docker, Prometheus e Node Exporter são habilitados pelo Ansible. Os containers
usam políticas de reinício. Depois de subir as VMs, confira DHCP, inventário e os
serviços com os comandos da etapa 7.

### 8.2 Conferir IPs quando o DHCP mudar

```bash
virsh -c qemu:///system net-dhcp-leases default
virsh -c qemu:///system domifaddr devops-1 --source lease
virsh -c qemu:///system domifaddr devops-2 --source lease
```

Compare os leases com `ansible_host` no inventário local e com `tofu output ips`.
Se estiverem divergentes, atualize os endereços do inventário antes de executar
Ansible e reconcilie o estado em uma próxima aplicação revisada do OpenTofu.
O inventário será regravado a partir do estado na aplicação normal da IaC.
Reaplique o monitoramento para atualizar targets e regras de acesso.

### 8.3 Preservar dados e estado

| Local | Conteúdo que precisa ser preservado |
| --- | --- |
| `infra/iac/terraform.tfstate` e backups | Associação dos recursos OpenTofu com as VMs e discos reais. |
| `infra/iac/terraform.tfvars` | Configuração local de chave e MACs, quando utilizada. |
| Chave SSH privada e `.pub` | Acesso às VMs existentes. |
| `infra/ansible/inventory.ini` | Endereços e parâmetros de conexão atuais. |
| Volume `monitoring_grafana_data` | Usuários, credenciais e dashboards do Grafana. |
| Volume `simulator_postgres_data` | Dados do PostgreSQL no projeto Compose padrão. |
| `/opt/monitoring/grafana_admin_password` | Senha inicial do Grafana. |
| `/etc/prometheus` e `/var/lib/prometheus` | Configuração e armazenamento local do Prometheus. |

Os arquivos de estado, planos, `terraform.tfvars`, imagens locais, `.terraform/`
e inventário são ignorados pelo `.gitignore`. Guarde cópias do estado e das
configurações fora do Git. O `.terraform.lock.hcl` é versionado e deve ser mantido.
O Git não salva os dados existentes dentro das VMs e dos volumes Docker.

Esta rotina não exige comandos de destruição, exclusão de volumes ou reset de
VMs. Para mudar CPU, memória, imagem ou discos, revise primeiro o plano do
OpenTofu e o impacto nos dados existentes.

## 9. Diagnóstico

| Sintoma | Verificação e encaminhamento |
| --- | --- |
| `virsh list` vazio, mas VMs existem | Use `virsh -c qemu:///system`; a sessão do usuário é outra conexão. |
| Acesso negado ao socket libvirt | Confira `id`, o login após alterar grupos e os daemons ativos; valide `virsh` com o usuário do OpenTofu. |
| Rede/pool `default` ausente ou inativo | Confira `net-list --all` e `pool-list --all`; prepare apenas o componente ausente conforme a etapa 2.4. |
| Falha ao executar `mkisofs` | Instale `genisoimage` no host e confira `command -v mkisofs`. |
| Download de imagem/pacotes falha | Confira acesso HTTPS e DNS no host; nas VMs, confira DHCP, gateway e saída NAT. |
| SSH demora ou não conecta | Confira o lease atual, a chave e o fim do cloud-init; utilize `wait_for_connection` antes do setup. |
| `Permission denied (publickey)` | Confira `ssh_key_path`, a chave pública usada no primeiro boot e o usuário `marcos`. Alterar a variável depois não instala outra chave na VM já criada. |
| APT bloqueado no primeiro boot | Aguarde `cloud-init status --wait` e os processos de atualização existentes. |
| `docker compose` ou Buildx indisponível na geradora | Reaplique `setup.yml` e confira `docker compose version`. |
| Permissão negada no Docker em sessão SSH antiga | Abra nova sessão após a inclusão no grupo `docker`, ou use Ansible com `--become`. |
| API inicia, mas tabelas ainda não existem | Confira os logs do gerador e aguarde um ciclo concluído; o endpoint `/health` testa a conexão, não a existência das tabelas. |
| Gerador/API reiniciando | Consulte `docker compose ps` e logs de `db`, `api` e `generator`; o banco pode ainda estar inicializando. |
| VM sem espaço ou serviços encerrados por falta de memória | Confira `df -h`, `free -h` e logs de kernel; cada VM tem apenas 10 GiB e 1 GiB de RAM. |
| Node Exporter não responde a partir do host | Acesso direto do host à porta 9100 é bloqueado por projeto; teste a partir de `monitoring`. |
| Prometheus abre localmente, mas não no navegador | Confira o IP do cliente em `prometheus_ui_allowed_sources` e a origem da conexão. |
| Target DOWN | Teste `/metrics` a partir de `monitoring`, confira IPs, portas, serviços e `iptables -S MR-VM-METRICS`. |
| Painéis da aplicação sem dados | Confira as variáveis de métricas do simulador e se o job `aplicacao-geradora` está UP. |
| `Dashboard ausente` com Grafana 13 | Utilize a role atualizada: a validação contempla `resource` (armazenamento unificado); a tabela antiga `dashboard` pode ficar vazia. |

Comandos de logs, sem reiniciar os serviços:

```bash
ansible all -i infra/ansible/inventory.ini --become \
  -m ansible.builtin.command -a 'journalctl -u cloud-init.service --no-pager -n 50'
ansible monitoring -i infra/ansible/inventory.ini --become \
  -m ansible.builtin.command -a 'journalctl -u prometheus --no-pager -n 50'
ansible monitoring -i infra/ansible/inventory.ini --become \
  -m ansible.builtin.command \
  -a 'docker compose --project-directory /opt/monitoring logs --tail 100 grafana'
ansible simulator -i infra/ansible/inventory.ini --become \
  -m ansible.builtin.command \
  -a 'docker compose --project-directory /opt/simulator logs --tail 100 db api generator'
```

No host Fedora, falhas de permissão ao abrir discos também devem ser investigadas
nos logs do libvirt e do SELinux, mantendo o pool no caminho apropriado.

## 10. Validações locais e documentação complementar

Sem alterar as VMs, é possível verificar:

```bash
tofu -chdir=infra/iac fmt -check -diff
tofu -chdir=infra/iac validate
ansible-playbook -i infra/ansible/inventory.ini \
  infra/ansible/playbooks/setup.yml --syntax-check
ansible-playbook -i infra/ansible/inventory.ini \
  infra/ansible/playbooks/monitoring.yml --syntax-check
```

`tofu validate` exige os providers instalados por `tofu init`. As validações
Ansible exigem um inventário válido. Os testes de renderização, consultas PromQL
e instrumentação estão descritos no [guia de monitoramento](../monitoring/README.md#validações-locais-e-resultados).
A renderização usa conexão local e grava em `/tmp`; ela não implanta serviços.

Nesta revisão, o host inspecionado é Fedora 44 x86_64, com OpenTofu 1.12.6,
Ansible Core 2.20.7 e libvirt 12.0.0. O provider `dmacvicar/libvirt` está fixado
em 0.8.3; o provider `hashicorp/local` é registrado no lockfile. As versões dos
pacotes do host não são fixadas pelo projeto. O Grafana 13.3.1 e o dashboard
provisionado foram confirmados por consulta somente de leitura na VM existente;
essa inspeção não equivale a um teste de instalação do zero em outro computador.

- [Visão geral e execução dos pipelines](../README.md)
- [Monitoramento: arquitetura, métricas, provisioning e testes](../monitoring/README.md)
- [Código e Docker Compose do simulador](../simulator/docker-compose.yml)


```
ansible-playbook -i infra/ansible/inventory.ini infra/ansible/playbooks/setup.yml
```
