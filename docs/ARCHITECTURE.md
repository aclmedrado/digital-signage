# Arquitetura

## Visão geral

O Digital Signage será composto inicialmente por dois elementos principais:

1. servidor central;
2. players instalados em TV Boxes.

## Servidor

Responsável por:

- interface administrativa;
- API;
- banco de dados;
- gerenciamento de mídia;
- programação das telas.

A aplicação é definida para execução através de Docker e Docker Compose.

## Implementação da ETAPA 002

FastAPI em app/main.py atende somente GET / e GET /health em JSON, via
Uvicorn na porta interna 8000. O único serviço Compose é signage-app, com
container digital-signage-app e publicação configurável por SIGNAGE_BIND_IP e
SIGNAGE_PORT, com padrão 127.0.0.1:8080 (somente acesso local no host).
O IP da implantação não é fixado no Compose nem no código Python.

A imagem usa Python 3.12 slim e usuário não-root (UID/GID 10001). O healthcheck
consulta /health usando a biblioteca padrão Python. Na ETAPA 002 não havia banco ou volumes. Não há montagens do host
ou outros serviços. A configuração usa a rede própria do
Compose e restart unless-stopped. Os testes pytest são executados na imagem.

Build, dois testes em container e implantação foram validados operacionalmente.
O container está healthy, com binding 10.4.254.202:8080 para a porta interna 8000
e ambos os endpoints retornando HTTP 200, conforme docs/STATUS.md.
Interface administrativa, gerenciamento de mídia e player continuam previstos
para o MVP.


## Implementação da ETAPA 003

SQLite acessado por SQLAlchemy 2.x, configurado por DATABASE_URL, com padrão
sqlite:////app/data/signage.db. O volume nomeado signage-data do Compose é
montado em /app/data. A imagem prepara apenas esse diretório com propriedade
UID/GID 10001; o volume novo recebe esse conteúdo e suas permissões no primeiro
uso. A aplicação permanece não-root, sem tornar /app gravável.

Screen contém id inteiro gerado, name e location obrigatórios, slug obrigatório
único com formato ^[a-z0-9]+(?:-[a-z0-9]+)*$, active booleano com padrão true e
timestamps created_at/updated_at gerados pelo servidor em UTC. Strings têm
limite de 200 caracteres. active expressa habilitação administrativa.
SQLite armazena os timestamps em UTC sem offset; a API os devolve com offset UTC.

POST e GET /api/screens criam/listam; GET e PATCH /api/screens/{screen_id}
consultam/atualizam. Listagem ordenada por id; ausentes retornam 404, conflitos
de slug 409 e validação 422. PATCH aceita somente name, slug, location e active;
campos nulos e campos adicionais são rejeitados. Não há exclusão de telas.

O lifespan cria tabelas com metadata.create_all de forma idempotente, sem
apagar dados ou migrar esquemas existentes. SQLite usa check_same_thread=False;
cada requisição recebe sessão fechada ao final, com rollback em conflito.
Testes usam SQLite em arquivo temporário, substituindo engine de inicialização
e dependência de sessão para não tocar o banco de produção.
Não há Alembic. Alterações futuras de esquema exigirão decisão específica.
A ETAPA 003 foi concluída e validada operacionalmente pelo operador: 23 testes
aprovados, container healthy em 10.4.254.202:8080 e usuário efetivo UID/GID 10001.
A propriedade signage:signage de /app/data e a criação de signage.db foram
confirmadas. O registro id=1 persistiu após restart, recriação, down/up sem -v
e rebuild; created_at e updated_at foram preservados após rebuild/recriação.
Os resultados completos estão em docs/STATUS.md.

## TV Box

Responsável somente pela reprodução do conteúdo.

A TV Box deverá executar Chromium ou navegador compatível em modo kiosk.

O player deverá acessar uma URL fornecida pelo servidor.

Exemplo futuro:

http://SERVIDOR/player/recepcao

## Princípio arquitetural

A TV Box deve permanecer simples.

Regras de negócio, armazenamento e gerenciamento devem ficar no servidor.

## Persistência

Dados persistentes:

- banco;
- imagens;
- vídeos.

Eles devem sobreviver à reconstrução ou substituição de containers.

## MVP

Fluxo pretendido:

Administrador
    |
    v
Painel Web
    |
    v
FastAPI
    |
    +---- SQLite
    |
    +---- Media
    |
    v
Player Web
    |
    v
Chromium kiosk
    |
    v
TV
