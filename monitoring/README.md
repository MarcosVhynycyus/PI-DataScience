# Módulo de Monitoramento e Observabilidade

Este módulo descreve as rotinas e ferramentas configuradas para garantir a saúde, alta disponibilidade e performance da infraestrutura do pipeline de dados e dos jobs do Apache Spark.

---

## Executar o Grafana na VM de monitoramento

A partir da raiz do repositório, execute:

```bash
ansible-playbook -i infra/ansible/inventory.ini infra/ansible/playbooks/setup.yml --limit monitoring
```

O playbook instala o Docker e o plugin Compose, cria a configuração em
`/opt/monitoring/compose.yml` e inicia o Grafana na porta `3000`. Os dados ficam
em um volume Docker persistente. O container reinicia automaticamente após
reinicializações da VM, e os logs têm limite de tamanho.

Acesse `http://<IP_DA_VM_MONITORING>:3000` com o usuário `admin`. Para consultar
a senha inicial gerada na VM:

```bash
ansible monitoring -i infra/ansible/inventory.ini --become -m ansible.builtin.command -a 'cat /opt/monitoring/grafana_admin_password'
```

A senha é preservada nas próximas execuções. Esse arquivo define a senha apenas
na criação do banco do Grafana; alterações posteriores devem ser feitas no
próprio Grafana. Não remova o volume caso queira preservar usuários e dashboards.

Por padrão, a imagem é `grafana/grafana:latest`, baixada apenas quando ausente.
Para fixar uma versão, use `-e grafana_image=grafana/grafana:<versao>`.
A porta também pode ser alterada com `-e grafana_port=3001`.

O playbook verifica `/api/health` antes de concluir. Essa etapa configura apenas
o Grafana; Prometheus, fontes de dados, dashboards e alertas ainda precisam ser
configurados para coletar e visualizar métricas.

Referência: [instalação oficial do Grafana com Docker](https://grafana.com/docs/grafana/latest/setup-grafana/installation/docker/).

---

## 🎯 Escopo do Monitoramento

O monitoramento abrange três camadas da solução:

1. **Infraestrutura Linux (Nós e Servidores):**
   - Uso de CPU, Memória RAM, Espaço em Disco (HDFS) e tráfego de rede.
2. **Pipeline de Dados (Apache Spark):**
   - Status dos jobs (Succeeded / Failed), latência das tarefas, uso de memória heap dos executores e vazamento de memória.
3. **Qualidade dos Dados & Recomendações:**
   - Volume de dados processados por minuto, taxa de erro/dados incorretos e latência de geração de recomendações.

---

## 🛠️ Ferramentas Utilizadas

- **Prometheus:** Coleta de métricas do sistema operacional e dos serviços Spark via *exporters*.
- **Grafana:** Dashboards interativos para visualização gráfica das métricas em tempo real.
- **Spark Web UI:** Interface gráfica nativa do Spark acessível na porta `4040` (ou `8080` para o Master).

---

## 📊 Principais Alertas Configurados

| Alerta | Condição | Ação |
| :--- | :--- | :--- |
| **HDFS Disk Full** | Uso de disco > 85% | Notificação e limpeza de logs antigos |
| **Spark Job Failure** | Erro em qualquer estagio do job | Reinício automático e notificação do time |
| **High Latency Streaming** | Atraso no processamento > 10s | Escalonamento de workers via Ansible |
