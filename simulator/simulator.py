import pandas as pd
from faker import Faker
from datetime import datetime
import random

fake = Faker('pt_BR')
registros = []

for _ in range(100):
    registros.append({
        'id_transacao': fake.uuid4(),
        'cliente': fake.name(),
        'valor': round(random.uniform(15.0, 850.0), 2),
        'categoria': random.choice(['Eletrônicos', 'Vestuário', 'Alimentos', 'Eletrodomesticos', 'Esportivo', 'Automobilistico']),
        'timestamp': datetime.now().isoformat()
    })

df = pd.DataFrame(registros)
df.to_csv('vendas.csv', index=False)
print("Massa de dados gerada com sucesso!")