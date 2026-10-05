# Digital Signage

Sistema leve e aberto de sinalização digital para gerenciamento centralizado
de TVs utilizando TV Boxes reaproveitadas.

## Objetivo

Permitir que um administrador publique imagens, vídeos e informes através de
uma interface web e controle o conteúdo exibido em uma ou mais TVs.

As TVs utilizarão TV Boxes com navegador executado em modo kiosk.

## Arquitetura prevista

Administrador
      |
      | Navegador
      v
Servidor Digital Signage
      |
      | HTTP
      v
TV Box
      |
      | HDMI
      v
TV

## Servidor de desenvolvimento inicial

IP interno:

`10.4.254.202`

Diretório:

`/home/administrador/digital-signage`

## Tecnologias previstas

- Docker
- Docker Compose
- Python
- FastAPI
- SQLite
- HTML
- CSS
- JavaScript
- Chromium kiosk

## Estado do projeto

O projeto está em fase inicial de estruturação.

Consulte:

`docs/STATUS.md`

## Documentação

- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/STATUS.md`
- `docs/ROADMAP.md`
- `docs/DEPLOYMENT.md`
- `docs/OPERATIONS.md`
- `docs/SECURITY.md`
- `docs/adr/`

## Licença

Este projeto é distribuído sob a licença MIT. Consulte `LICENSE`.
