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

A ETAPA 002 implementa uma aplicação FastAPI mínima com GET / e GET /health,
Dockerfile, Compose e dois testes pytest. A validação operacional foi concluída:
2 testes aprovados, container healthy e endpoints com HTTP 200 na implantação
em 10.4.254.202:8080; não há banco, upload ou player.

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

## Execução mínima

No diretório oficial, confira primeiro se a porta escolhida (padrão 8080) está livre com
`ss -tulpn`. Se houver conflito, não suba o serviço.

```bash
sudo docker compose build
sudo docker compose up -d --wait
sudo docker compose ps
sudo docker compose logs --tail=100
curl --fail --noproxy '*' http://127.0.0.1:8080/
curl --fail --noproxy '*' http://127.0.0.1:8080/health
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
sudo docker compose stop
```

Os endpoints retornam, respectivamente,
`{"name": "Digital Signage", "status": "running"}` e `{"status": "ok"}`.
As dependências são instaladas somente na imagem. Não é necessário criar .env.
O binding padrão é 127.0.0.1:8080, acessível somente no host. SIGNAGE_BIND_IP
e SIGNAGE_PORT permitem configurar outra interface e porta; veja .env.example
e docs/DEPLOYMENT.md. Ajuste as URLs acima quando alterar esses valores.
Consulte docs/DEPLOYMENT.md para inspeção prévia e docs/OPERATIONS.md para rotina.

## Licença

Este projeto é distribuído sob a licença MIT. Consulte `LICENSE`.
