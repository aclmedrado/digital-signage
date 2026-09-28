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

A aplicação será executada através de Docker.

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
