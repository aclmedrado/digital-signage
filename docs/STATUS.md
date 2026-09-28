# Status do projeto

Última atualização: 2026-09-28

## Fase atual

Estruturação inicial do repositório.

## Implementado

- diretório oficial do projeto;
- estrutura inicial de diretórios;
- documentação básica;
- AGENTS.md;
- README.md;
- .gitignore;
- repositório Git local.

## Ainda não implementado

- aplicação FastAPI;
- Dockerfile funcional;
- Docker Compose funcional;
- banco SQLite;
- painel administrativo;
- cadastro de telas;
- upload de imagens;
- player web;
- integração com TV Box;
- Chromium kiosk;
- vídeos;
- agendamento;
- grupos de telas;
- monitoramento.

## Ambiente

Servidor:

10.4.254.202

Diretório:

/home/administrador/digital-signage

## Infraestrutura confirmada

Servidor:

- Hostname: utilities
- IP principal: 10.4.254.202
- Sistema operacional: Ubuntu 26.04.1 LTS
- Arquitetura: x86_64
- Docker Engine: 29.8.1
- Docker Compose: 5.5.1
- containerd: 2.3.6
- Serviço Docker: ativo e habilitado no boot
- UFW: inativo

O Docker foi instalado através do repositório oficial da Docker.

O usuário `administrador` não pertence deliberadamente ao grupo `docker`.
Operações administrativas do Docker devem utilizar `sudo`.

## Próxima etapa

Publicar o repositório no GitHub e, em seguida, implementar o primeiro
container da aplicação com FastAPI e endpoint de healthcheck.
