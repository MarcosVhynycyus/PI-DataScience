import os
from pathlib import Path
import paramiko

def enviar_diretorio_sftp(
    diretorio_local: str,
    caminho_remoto: str,
    host: str,
    usuario: str,
    senha: str = None,
    chave_privada: str = None,
    porta: int = 22
):
    """Envia todos os arquivos .csv de um diretório local para o servidor SFTP remoto."""
    pasta_local = Path(diretorio_local)
    if not pasta_local.exists():
        raise FileNotFoundError(f"Diretório local '{diretorio_local}' não existe.")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(
            hostname=host,
            port=porta,
            username=usuario,
            password=senha,
            key_filename=chave_privada
        )
        
        with ssh.open_sftp() as sftp:
            # Cria a pasta remota caso não exista
            try:
                sftp.chdir(caminho_remoto)
            except IOError:
                sftp.mkdir(caminho_remoto)

            for arquivo in pasta_local.glob("*.csv"):
                destino = f"{caminho_remoto.rstrip('/')}/{arquivo.name}"
                print(f"Enviando {arquivo.name} -> {destino}")
                sftp.put(str(arquivo), destino)

    finally:
        ssh.close()