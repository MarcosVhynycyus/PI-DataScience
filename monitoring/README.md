# Módulo de Monitoramento e Observabilidade

Este módulo descreve as rotinas e ferramentas configuradas para garantir a saúde, alta disponibilidade e performance da infraestrutura do pipeline de dados e dos jobs do Apache Spark.

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