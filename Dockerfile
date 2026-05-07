# Usar imagem oficial do Python
FROM python:3.12-slim

# Evitar que o Python gere arquivos .pyc e que o stdout seja bufferizado
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema (essenciais para Pillow e PostgreSQL)
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    libpq-dev \
    gcc \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Instalar dependências do Python
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copiar o restante do código do projeto
COPY . /app/

# Criar pastas para arquivos estáticos e mídia
RUN mkdir -p /app/static /app/media

# Expor a porta que o Django usará
EXPOSE 8000

# Comando para iniciar (será sobrescrito pelo compose se necessário)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
