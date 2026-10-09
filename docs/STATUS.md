# Status do projeto

Última atualização: 2026-10-09

## Fase atual

ETAPA 003 concluída e validada operacionalmente pelo operador: testes em
container, API, permissões e persistência SQLite confirmados com sucesso.
A ETAPA 002 permanece validada. A ETAPA 004 está concluída e validada
operacionalmente, conforme resultados fornecidos pelo operador: config e
build aprovados, 66 testes aprovados, container healthy, regressão dos
endpoints confirmada, TV Piloto preservada no SQLite e oito testes pelo
navegador aprovados. Autenticação e autorização continuam não implementadas;
o painel e a API são destinados somente ao ambiente interno controlado.

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
- painel administrativo server-rendered em /admin com Jinja2 e CSS local;
- listagem, cadastro, edição, ativação e desativação de telas no navegador;
- regras de Screen compartilhadas entre API e interface, sem HTTP interno;
- testes administrativos definidos sobre SQLite temporário isolado.

## Ainda não implementado

- autenticação e autorização;
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

Auditoria e versionamento das alterações pelo operador. A validação
operacional da ETAPA 004 está concluída; nenhuma etapa seguinte foi iniciada
nesta atualização documental.

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

## Registro da ETAPA 004

### Estado inicial e inspeções

Diretório oficial confirmado por pwd. main limpa e sincronizada com
origin/main no commit d46dfb4; git log -3 confirmou os dois novos commits
documentais sobre o ADR 0004 e o prompt. O bloqueio anterior de arquivos
não rastreados foi resolvido pelo operador antes desta implementação.
AGENTS.md, README.md, STATUS, ARCHITECTURE, os quatro ADRs e o prompt
etapa004 foram lidos integralmente. Código FastAPI, banco, modelos, schemas,
rotas, testes, diretórios de templates/static e arquivos Docker envolvidos
foram inspecionados antes de editar. A ETAPA 003 já tinha validação
operacional registrada; não foi revalidada nesta sessão.

### Arquivos criados

- app/services/__init__.py;
- app/services/screens.py;
- app/routes/admin/__init__.py;
- app/routes/admin/screens.py;
- app/templates/base.html;
- app/templates/admin/screens/list.html;
- app/templates/admin/screens/form.html;
- app/templates/admin/screens/not_found.html;
- app/static/admin.css;
- tests/test_admin_screens.py.

### Arquivos alterados

- app/main.py;
- app/routes/screens.py;
- requirements.txt;
- compose.yaml;
- .dockerignore;
- README.md;
- docs/ARCHITECTURE.md;
- docs/DEPLOYMENT.md;
- docs/OPERATIONS.md;
- docs/STATUS.md.

### Implementação e decisões

Interface server-rendered no mesmo container, coerente com ADR 0004.
GET /admin redireciona para /admin/screens; a listagem ordenada por id
apresenta nome, slug, localização, ativa/inativa e ações. GET
/admin/screens/new e POST /admin/screens realizam cadastro com estado ativo.
GET/POST /admin/screens/{screen_id}/edit editam somente nome, slug e
localização; POST /admin/screens/{screen_id}/toggle altera active.
Cada edição ou alteração de active atualiza updated_at em UTC.
Não há alteração de estado por GET nem exclusão.

Sucesso usa POST → Redirect 303 → GET da listagem; parâmetro result seleciona
uma mensagem de confirmação fixa. Validação inválida retorna formulário
HTML 422 e conflito de slug retorna formulário HTML 409, preservando os
valores enviados. Tela ausente retorna HTML 404. Templates compartilham
base.html e usam escape automático, labels e validação HTML; CSS é local
e responsivo, sem JavaScript, CDN ou frontend separado.

Pequenas funções compartilhadas foram extraídas para app/services/screens.py;
API e interface reutilizam Screen, ScreenCreate, ScreenUpdate e get_session,
incluindo commit/rollback em slug duplicado. O pattern do slug no HTML vem
do schema existente. Não há chamadas HTTP internas nem framework de serviços.
As rotas e respostas da API foram preservadas na implementação; sua regressão
foi posteriormente validada pelo operador, conforme registro abaixo.

Adicionadas somente Jinja2==3.1.6, para templates, e
python-multipart==0.0.32, para processamento de formulários pelo FastAPI.
As versões foram consultadas nas fontes oficiais; instalação e compatibilidade
em container foram posteriormente validadas pelo build e pelos testes do
operador. Não houve instalação no host.
.dockerignore passou a incluir os novos diretórios Python, templates e CSS
no contexto restrito. Tag atualizada para digital-signage:etapa004, conforme
a convenção existente; docs/DEPLOYMENT.md registrou inicialmente a imagem
definida para build e foi atualizado após a validação operacional do operador.
Dockerfile, usuário não-root, porta, healthcheck, SQLite, DATABASE_URL,
esquema e volume signage-data foram preservados. O agente não acessou nem
alterou o banco real na implementação inicial; o operador posteriormente
confirmou a preservação de TV Piloto no SQLite.

### Testes definidos e verificações da implementação inicial

Definidos 43 casos administrativos, contando parametrizações, além dos 23
casos existentes: total 66. A contagem inicial foi feita por inspeção AST do
código, sem coleta ou execução pytest naquele momento. Os 66 testes foram
posteriormente executados e aprovados pelo operador, conforme registro abaixo.
A fixture existente substitui engine e sessão por SQLite temporário;
não houve mudança em tests/conftest.py.

Cobertura administrativa definida: redirect, lista vazia e ordenada,
ativa/inativa, formulário de criação, cadastro ativo, confirmação e refresh
sem duplicação, conflito de criação, formulário de edição, edição preservando
active, updated_at, rollback integral em conflito de edição, telas ausentes,
toggle e timestamps, GET sem mutação, ausência de DELETE, validação HTML de
campos vazios/ausentes, comprimentos e slug, preservação dos valores, escape
HTML e serviço do CSS local. Os testes anteriores de API e endpoints base
permanecem intactos.

Efetivamente executado na implementação inicial: ast.parse nos 17 arquivos
Python, aprovado;
docker compose config --quiet sem sudo e sem acesso ao daemon, aprovado;
revisão do diff e dos arquivos novos, e git diff --check, aprovados.
Comparação AST confirmou endpoints base, assinaturas/decorators da API e
funções extraídas preservados; os dez arquivos novos passaram na verificação
de whitespace. Banco, schemas, testes anteriores e Dockerfile foram comparados
com HEAD e permanecem intactos; no Compose mudou somente a tag da imagem.
Essas verificações não substituem pytest, build ou validação pelo navegador.

### Bloqueio na implementação inicial (resolvido pela validação do operador)

A inspeção sudo -n docker compose ps foi bloqueada por "no new privileges".
Não houve tentativa de contornar sudo ou alterar permissões. Inspeção do
estado real de containers, redes, volumes e binding, build, pytest em
container, implantação, estado healthy e logs não foram executados pelo
agente naquela tentativa. Esse bloqueio não foi contornado; a validação
operacional foi posteriormente concluída pelo operador, com os resultados
registrados na seção seguinte. Os procedimentos permanecem documentados em
docs/DEPLOYMENT.md e docs/OPERATIONS.md para futuras implantações ou revalidações.

### Segurança, escopo e próximo passo

Autenticação e autorização ainda não implementadas; painel e API somente
para ambiente interno controlado, sem exposição direta à Internet.
Nenhuma alteração global do servidor, de firewall, SSH, sudoers, grupos,
daemon Docker ou rede. Não foram criadas cópias do projeto fora do diretório
oficial, novos serviços, uploads, player ou funcionalidades de etapas futuras.
Nenhum git add, commit ou push realizado. Próximo passo recomendado: auditoria
e versionamento pelo operador. A validação operacional da ETAPA 004 está
concluída; nenhuma etapa seguinte foi iniciada nesta atualização.

## Validação operacional da ETAPA 004

ETAPA 004 concluída e validada com sucesso, conforme resultados reais
fornecidos pelo operador e registrados em 2026-10-09. Os comandos, testes e
observações operacionais abaixo foram executados ou confirmados pelo operador;
não foram reexecutados pelo agente nesta atualização documental.

### Docker

- `docker compose config --quiet`: aprovado;
- `docker compose build`: aprovado;
- imagem: `digital-signage:etapa004`;
- container: `digital-signage-app`, estado `healthy`;
- binding: `10.4.254.202:8080`;
- logs: inicialização normal, sem erros.

### Testes automatizados e warnings

- Resultado: `66 passed, 3 warnings`, nenhuma falha;
- dois warnings relacionados ao cache do pytest decorreram de erro de
  digitação no argumento utilizado pelo operador;
- um `DeprecationWarning` de Starlette/AnyIO;
- os warnings não impediram a aprovação dos testes.

O comando correto para futuras execuções é:

```bash
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
```

Não alterar permissões para resolver os warnings de cache. Nenhuma correção
de código ou dependências foi realizada nesta atualização.

### Regressão e dados existentes

| Verificação | Resultado confirmado pelo operador |
|---|---|
| GET `/` | HTTP 200 |
| GET `/health` | HTTP 200 |
| GET `/api/screens` | HTTP 200 |
| Registro TV Piloto | Preservado no SQLite |

### Validação pelo navegador

Todos os oito testes foram aprovados pelo operador:

1. Painel abre e apresenta TV Piloto.
2. Nova tela exibe o formulário.
3. Cadastro com slug diferente funciona.
4. Edição de nome e localização funciona.
5. Ativação e desativação funcionam.
6. Slug duplicado apresenta mensagem compreensível.
7. Atualização da página não duplica cadastro.
8. Interface mantém boa legibilidade em computador e tablet/janela estreita.

URLs administrativas do ambiente validado:

- `http://10.4.254.202:8080/admin`;
- `http://10.4.254.202:8080/admin/screens`.

### Registro desta atualização documental

Nenhum arquivo criado. Alterados somente README.md, docs/STATUS.md,
docs/ARCHITECTURE.md, docs/DEPLOYMENT.md e docs/OPERATIONS.md para registrar
a conclusão, os resultados e a origem operacional das evidências, removendo
as referências atuais às validações pendentes já resolvidas. O bloqueio de
sudo da implementação inicial foi preservado como registro histórico.

Verificação documental: diff revisado e `git diff --check` aprovado.
Os testes, comandos Docker e validações pelo navegador não foram reexecutados
nesta atualização; seus resultados são os fornecidos pelo operador.

Não há pendência de validação operacional da ETAPA 004 nos resultados
informados. Autenticação e autorização permanecem ausentes no painel e na API;
o uso continua restrito ao ambiente interno controlado, sem exposição direta
à Internet. O DeprecationWarning de Starlette/AnyIO permanece registrado,
sem falhas e sem correção nesta atualização.

Próximo passo recomendado: auditoria e versionamento pelo operador. Nenhuma
ETAPA 005 iniciada, funcionalidade implementada, alteração de código, Docker,
banco ou configuração global do servidor. Nenhum git add, commit ou push.
