# Módulo Simulador de Fontes de Dados

Para viabilizar os testes e a execução do pipeline de dados sem dependências de ambientes de produção externos, este módulo contém um **gerador/simulador de eventos em tempo real**.

---

## 📡 Fontes de Dados Simuladas

O simulador gera dados contínuos correspondentes a três origens distintas:

1. **Sistema de Vendas (ERP/PDV):**
   - Transações de compra efetuadas.
   - IDs de clientes, produtos, valores, datas e formas de pagamento.
   - *Formato:* Estruturado (JSON / CSV / SQL direct).

2. **E-commerce (Logs de Navegação):**
   - Eventos de visualização de produtos, termos buscados, itens adicionados/removidos do carrinho e cliques em banners promocionais.
   - *Formato:* Semiestruturado (JSON events).

3. **Redes Sociais & Avaliações:**
   - Comentários de clientes, notas (ratings 1 a 5 estrelas) e feedbacks em texto livre.
   - *Formato:* Não estruturado (JSON com texto livre).

---

## 🛠️ Como Executar o Simulador

### Dependências
Certifique-se de que o pacote `Faker` e `kafka-python` (se aplicável) estão instalados:

```bash
pip install faker
```

### Execução Simples
Para iniciar a geração contínua de eventos simulados:

```bash
python simulator.py --rate 100 --output hdfs
```

Parâmetros disponíveis:
- `--rate`: Quantidade de eventos gerados por segundo.
- `--output`: Destino dos dados (`hdfs`, `local`, `stream`).