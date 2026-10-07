# Status do projeto

Última atualização: 2026-10-07

## Fase atual

ETAPA 003 concluída e validada operacionalmente pelo operador: testes em
container, API, permissões e persistência SQLite confirmados com sucesso.
A ETAPA 002 permanece validada. A ETAPA 004 não foi iniciada.

## Implementado

- diretório oficial do projeto;
- estrutura inicial de diretórios;
- documentação básica;
- AGENTS.md;
- README.md;
- .gitignore;
- repositório Git local.
- aplicação FastAPI mínima: GET / e GET /health;
- Dockerfile com Python slim, Uvicorn e usuário não-root;
- Compose com um serviço signage-app, restart unless-stopped e healthcheck;
- binding configurável por SIGNAGE_BIND_IP e SIGNAGE_PORT, com padrão
  127.0.0.1:8080 para porta interna 8000;
- testes pytest para os endpoints existentes e cadastro de telas;
- SQLite via SQLAlchemy 2.x, volume persistente e inicialização idempotente;
- modelo Screen e API de criação, listagem, consulta e atualização parcial;
- documentação de implantação, operações e ADR 0002 aceito.

## Ainda não implementado

- painel administrativo;
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

Planejar a próxima etapa do MVP após a auditoria do diff pelo operador.
A ETAPA 004 não será iniciada nesta atualização documental.

## Registro da ETAPA 002

Estado inicial: main limpa e sincronizada com origin/main, apenas estrutura e
documentação; Dockerfile, compose.yaml, .env.example e os documentos de
implantação, operações e ADR 0002 estavam vazios.

Criados: app/__init__.py, app/main.py, tests/__init__.py, tests/test_main.py,
requirements.txt e .dockerignore.

Alterados: Dockerfile, compose.yaml, .env.example, README.md,
docs/ARCHITECTURE.md, docs/DEPLOYMENT.md, docs/OPERATIONS.md,
docs/adr/0002-fastapi.md e este docs/STATUS.md.

Decisões: somente dois endpoints; dependências diretas fixadas; testes na
imagem para execução reproduzível sem dependências no host; .dockerignore
adicional para restringir o contexto aos arquivos necessários e excluir
segredos/dados. Não criado .env. ADR SQLite preservado.

Verificações: leituras iniciais obrigatórias e inspeção dos arquivos concluídas.
Porta 8080 livre na inspeção com ss fora do sandbox; dentro do sandbox, a
consulta foi bloqueada por permissão de netlink.
Sintaxe dos quatro arquivos Python validada com ast.parse sem instalar
dependências; git diff revisado e git diff --check aprovado.

Problema operacional na validação inicial (resolvido na validação abaixo):
sudo exigia autenticação em terminal. A inspeção de
containers, redes e volumes não pôde ser realizada. Build, pytest em Docker,
inicialização, respostas HTTP, logs e estado healthy não foram confirmados
naquela tentativa.
As tentativas de compose config --quiet, compose build e compose run com
pytest terminaram com "sudo: A terminal is required to authenticate";
nenhum teste pytest chegou a executar. A inicialização foi adiada porque a
inspeção obrigatória do ambiente Docker não pôde ser concluída.
Foi mantida a decisão de não instalar dependências no host para contornar
a pendência inicial.

Nenhum commit ou push realizado. Nenhuma alteração de arquivos fora do projeto,
nem alteração de firewall, SSH, grupos, serviços externos ou Docker global.

Correção de replicabilidade: compose.yaml passou a usar
${SIGNAGE_BIND_IP:-127.0.0.1}:${SIGNAGE_PORT:-8080}:8000. .env.example documenta
as variáveis; README.md, docs/DEPLOYMENT.md, docs/OPERATIONS.md e
docs/ARCHITECTURE.md foram ajustados para o padrão local e a configuração por
ambiente. Nenhum arquivo novo ou .env real criado nesta correção. Nenhuma
outra alteração arquitetural. Revisão do diff e git diff --check aprovados.
docker compose config --quiet e config --format json executados sem sudo
(sem acesso ao daemon): padrão 127.0.0.1:8080 e substituição por variáveis
com 10.4.254.202:9090 validados. Build, pytest em container e implantação
permaneciam pendentes pela autenticação sudo naquele momento.

## Validação operacional da ETAPA 002

Validação concluída com sucesso, conforme resultados reais informados pelo
operador e registrados em 2026-10-06:

- `sudo docker compose config`: aprovado;
- `sudo docker compose build`: aprovado;
- imagem criada: `digital-signage:etapa002`;
- `sudo docker compose run --rm signage-app pytest -q`: 2 testes aprovados;
- `sudo docker compose up -d`: aprovado;
- container: `digital-signage-app`, estado `healthy`;
- binding confirmado: `10.4.254.202:8080 -> 8000/tcp`;
- GET `http://10.4.254.202:8080/`: HTTP 200,
  resposta `{"name":"Digital Signage","status":"running"}`;
- GET `http://10.4.254.202:8080/health`: HTTP 200,
  resposta `{"status":"ok"}`.

Problema encontrado: `PytestCacheWarning` porque o usuário não-root não possui
permissão de escrita em `/app/.pytest_cache`. O warning não afetou os dois
testes aprovados. Não alterar permissões de `/app`; usar nos próximos testes:

```bash
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
```

Atualização documental: nenhum arquivo criado; alterados README.md,
docs/STATUS.md, docs/ARCHITECTURE.md, docs/DEPLOYMENT.md e docs/OPERATIONS.md.
Decisões: registrar a validação concluída e desabilitar o cache nos comandos
pytest documentados, preservando o usuário não-root e as permissões existentes.
Os testes e resultados acima foram informados pelo operador; não foram
reexecutados nesta atualização. Logs não foram fornecidos nessa validação.
Não há pendência de validação operacional da ETAPA 002 nos resultados
informados. SQLite e demais funcionalidades continuam não implementados.
Próximo passo recomendado: planejar a etapa de persistência, sem iniciá-la aqui.
Nenhum commit ou push realizado nesta atualização.

## Registro da ETAPA 003

Estado inicial: diretório oficial confirmado; leituras obrigatórias integrais
concluídas; main limpa e sincronizada com origin/main. ETAPA 002 validada pelo
operador; ADR 0003 já aceito. Inspeção dos arquivos concluída antes de editar.

Criados: app/config.py, app/database.py, app/models.py, app/schemas.py,
app/routes/__init__.py, app/routes/screens.py, tests/conftest.py e
tests/test_screens.py.
Alterados: app/main.py, requirements.txt, Dockerfile, compose.yaml,
.dockerignore, .env.example, README.md, docs/ARCHITECTURE.md,
docs/DEPLOYMENT.md, docs/OPERATIONS.md e docs/STATUS.md.

Implementado: Screen, POST/GET /api/screens e GET/PATCH /api/screens/{screen_id},
slug único/validado, conflito 409, ausentes 404, atualização parcial e active;
timestamps UTC gerados pelo servidor. GET / e GET /health preservados.
SQLAlchemy 2.0.40 adicionado; criação idempotente de tabelas no lifespan.
DATABASE_URL padrão sqlite:////app/data/signage.db; volume nomeado signage-data;
imagem etapa003; diretório /app/data preparado para UID/GID 10001.
Decisão: volume nomeado para portabilidade e permissões não-root, sem bind mount,
chmod 777 ou alteração das permissões de /app para cache pytest.

Testes implementados: 23 casos (incluindo parametrizações), com SQLite temporário,
engine e sessões isolados do banco de produção. Cobrem endpoints existentes,
CRUD permitido, ativação/desativação, conflitos na criação/atualização,
validação, campos imutáveis, nulos e persistência entre inicializações.
Na implementação inicial, o agente não executou pytest, build, inicialização,
logs ou persistência real em Docker. A validação posterior pelo operador foi
concluída com sucesso e está registrada na seção seguinte.
Verificações da implementação inicial: sintaxe dos 12 arquivos Python por ast.parse aprovada;
docker compose config --quiet aprovado sem acesso ao daemon.
Inspeção sudo docker compose ps falhou por restrição "no new privileges".
Não houve tentativa de contornar sudo. Comandos manuais em DEPLOYMENT/OPERATIONS.
Revisão integral do diff e dos arquivos novos concluída sem alterações fora
do escopo; git diff --check aprovado.

Os testes em container, permissões do volume, estado healthy, API e
persistência foram posteriormente confirmados pelo operador, conforme abaixo.
Nenhuma alteração fora do diretório oficial, instalação de dependências no host,
alteração de firewall/SSH/sudoers/grupos/Docker global, git add, commit ou push.
Sem interface administrativa, autenticação, upload, player, mídia, agendamento
ou Alembic. Próximo passo: auditar o diff e planejar a próxima etapa do MVP,
sem implementá-la nesta atualização.

## Validação operacional da ETAPA 003

ETAPA 003 concluída e validada com sucesso, conforme resultados reais
informados pelo operador e registrados em 2026-10-07. Os comandos e testes
operacionais abaixo foram executados pelo operador; não foram reexecutados
pelo agente nesta atualização documental.

### Docker e testes automatizados

- `sudo docker compose config`: aprovado;
- `sudo docker compose build`: aprovado;
- imagem construída: `digital-signage:etapa003`;
- `sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider`:
  `23 passed, 1 warning`, sem falhas;
- warning: `DeprecationWarning` proveniente de Starlette/AnyIO; não impediu
  a aprovação dos testes.

### Container e armazenamento

- serviço: `signage-app`;
- container: `digital-signage-app`, estado `healthy`;
- binding: `10.4.254.202:8080 -> 8000/tcp`;
- usuário efetivo: `uid=10001(signage) gid=10001(signage)`;
- `/app/data` pertence a `signage:signage`;
- `/app/data/signage.db` criado com sucesso no volume nomeado `signage-data`.

### Endpoints base e API de telas

| Requisição | Resultado confirmado |
|---|---|
| GET `/` | HTTP 200; `{"name":"Digital Signage","status":"running"}` |
| GET `/health` | HTTP 200; `{"status":"ok"}` |
| POST `/api/screens` | HTTP 201; TV Piloto criada, `id=1`, `slug=tv-piloto` |
| GET `/api/screens` | HTTP 200; tela listada corretamente |
| GET `/api/screens/1` | HTTP 200 |
| PATCH `/api/screens/1` alterando `location` | HTTP 200; `updated_at` atualizado |
| PATCH `/api/screens/1` com `active=false` | HTTP 200 |
| PATCH `/api/screens/1` com `active=true` | HTTP 200 |
| Tentativa com slug duplicado | HTTP 409; `{"detail":"Slug já cadastrado"}` |
| Tentativa com slug inválido | HTTP 422 |
| GET `/api/screens/999999` | HTTP 404; `{"detail":"Tela não encontrada"}` |

### Persistência operacional

O registro `id=1` permaneceu disponível após cada um dos ciclos confirmados:

1. `sudo docker compose restart signage-app`;
2. `sudo docker compose up -d --force-recreate`;
3. `sudo docker compose down` seguido de `sudo docker compose up -d`, sem `-v`;
4. novo `sudo docker compose build` seguido de
   `sudo docker compose up -d --force-recreate`.

Após o último ciclo, o container voltou ao estado `healthy`, o registro
continuou disponível e os mesmos `created_at` e `updated_at` foram preservados.
A persistência SQLite da ETAPA 003 está validada operacionalmente.

### Registro desta atualização documental

Nenhum arquivo criado. Alterados somente README.md, docs/STATUS.md,
docs/DEPLOYMENT.md, docs/OPERATIONS.md e docs/ARCHITECTURE.md para registrar a
conclusão e remover referências a validações operacionais ainda pendentes.
Decisão: registrar os resultados fornecidos pelo operador, preservando os
procedimentos úteis para futuras implantações e revalidações.

Verificação documental: diff revisado e `git diff --check` aprovado.
Os testes operacionais não foram reexecutados nesta atualização; seus
resultados são os informados pelo operador. Logs detalhados não foram
fornecidos nesta validação.

Problema encontrado: um DeprecationWarning de Starlette/AnyIO, sem falhas de
teste; nenhuma correção de código ou dependências realizada nesta atualização.
Não há pendência de validação operacional da ETAPA 003 nos resultados
informados. Próximo passo recomendado: auditoria do diff pelo operador e
planejamento da próxima etapa do MVP, sem iniciar a ETAPA 004 aqui.
Nenhuma funcionalidade implementada, alteração de código da aplicação,
mudança no ambiente do servidor, alteração fora do diretório oficial,
git add, commit ou push nesta atualização.
