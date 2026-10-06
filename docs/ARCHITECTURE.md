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
consulta /health usando a biblioteca padrão Python. Não há banco, volumes,
montagens do host ou outros serviços. A configuração usa a rede própria do
Compose e restart unless-stopped. Os testes pytest são executados na imagem.

Build, dois testes em container e implantação foram validados operacionalmente.
O container está healthy, com binding 10.4.254.202:8080 para a porta interna 8000
e ambos os endpoints retornando HTTP 200, conforme docs/STATUS.md.
As responsabilidades e persistência descritas abaixo
representam o MVP futuro, não funcionalidades disponíveis nesta etapa.

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
