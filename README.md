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

A ETAPA 003 adiciona SQLite via SQLAlchemy 2.x e cadastro de telas por API,
com criação, listagem, consulta e atualização parcial em `/api/screens`.
`DATABASE_URL` usa por padrão `sqlite:////app/data/signage.db`, persistido em
volume Docker nomeado. A ETAPA 003 está concluída e validada operacionalmente
pelo operador: 23 testes aprovados, container healthy e persistência confirmada
após restart, recriação, down/up sem -v e rebuild.

A ETAPA 004 implementa o painel administrativo inicial em `/admin`, com
listagem, cadastro, edição, ativação e desativação de telas usando FastAPI,
Jinja2 e formulários HTML, sem JavaScript. A etapa está concluída e validada
operacionalmente, conforme resultados fornecidos pelo operador: 66 testes
aprovados, container healthy, TV Piloto preservada no SQLite e os oito testes
pelo navegador aprovados. Acesso no ambiente atual:
`http://10.4.254.202:8080/admin`. Resultados e warnings em docs/STATUS.md.
O painel e a API ainda não possuem autenticação ou autorização: manter a
aplicação somente em ambiente interno controlado, sem exposição pública.

A ETAPA 005 implementa a biblioteca em `/admin/media`, priorizando MP4/H.264,
com upload, catálogo, metadados e pré-visualização pelo navegador. Suporta
também JPG/JPEG, PNG, WebP e GIF, preservando animações. SVG é rejeitado até
existir tratamento seguro. A etapa está concluída e validada operacionalmente,
conforme resultados fornecidos pelo operador: config e build aprovados,
149 testes aprovados, 1 warning de depreciação Starlette/AnyIO, container
healthy e os 14 itens do checklist pelo navegador aprovados. HTTP Range
206/416 e persistência após restart e force-recreate foram confirmados.
Não há player nem playlists; a compatibilidade com TV Boxes continua pendente.

Perfil MP4: uma trilha H.264 de 8 bits `yuv420p`, até 1920 × 1080 e 30 FPS,
com uma trilha AAC opcional. Não há transcodificação. Limites padrão:
250 MiB por vídeo, 10 MiB por imagem, 20.000.000 pixels por quadro,
100 quadros e 100.000.000 pixels acumulados por imagem. As variáveis de
`.env.example` permitem ajustar os limites; MiB significa 1024 × 1024 bytes.
Os arquivos ficam em `signage-media:/app/media`; o banco permanece em
`signage-data:/app/data`. A imagem instala Pillow e o pacote Debian que
fornece ffprobe, sem dependências no host.

O upload ainda não possui autenticação, autorização ou proteção CSRF.
Usar somente com operadores confiáveis em ambiente restrito. Esses controles
são obrigatórios na ETAPA 006, antes da liberação institucional; não expor
à Internet. O operador decidiu manter temporariamente `10.4.254.202:8080`
durante os testes, como risco temporariamente aceito. Esse binding não
constitui proteção de acesso nem autorização para liberação institucional.
Consulte os resultados em `docs/STATUS.md` e os procedimentos e backup em
`docs/OPERATIONS.md`.

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
As dependências são instaladas somente na imagem. A configuração real usa .env não versionado; consulte .env.example.
O binding padrão é 127.0.0.1:8080, acessível somente no host. SIGNAGE_BIND_IP
e SIGNAGE_PORT permitem configurar outra interface e porta; veja .env.example
e docs/DEPLOYMENT.md. Ajuste as URLs acima quando alterar esses valores.
Consulte docs/DEPLOYMENT.md para inspeção prévia e docs/OPERATIONS.md para rotina.

## Licença

Este projeto é distribuído sob a licença MIT. Consulte `LICENSE`.
