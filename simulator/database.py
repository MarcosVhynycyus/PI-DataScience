import os
import time
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://user:password@db:5432/varejo_db"
)

def get_engine(retries=5, delay=3):
    """Cria a conexão com o banco tratando tentativas de reconexão na inicialização."""
    engine = create_engine(DATABASE_URL)
    for i in range(retries):
        try:
            connection = engine.connect()
            connection.close()
            return engine
        except OperationalError:
            print(f"Aguardando banco de dados subir... ({i+1}/{retries})")
            time.sleep(delay)
    raise Exception("Não foi possível conectar ao banco de dados SQL.")

engine = get_engine()