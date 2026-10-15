# Status do projeto

Última atualização: 2026-10-15

## Fase atual

ETAPA 003 concluída e validada operacionalmente pelo operador: testes em
container, API, permissões e persistência SQLite confirmados com sucesso.
A ETAPA 002 permanece validada. A ETAPA 004 está concluída e validada
operacionalmente, conforme resultados fornecidos pelo operador: config e
build aprovados, 66 testes aprovados, container healthy, regressão dos
endpoints confirmada, TV Piloto preservada no SQLite e oito testes pelo
navegador aprovados. Naquela etapa, autenticação e autorização ainda não
existiam; a política implementada na ETAPA 006 está descrita abaixo.

A ETAPA 005 está concluída e validada operacionalmente com sucesso, conforme
resultados fornecidos pelo operador: config/build aprovados, imagem
digital-signage:etapa005, container healthy, 149 passed e 1 warning em
18.60 segundos, sem falhas. Regressão HTTP, os 14 itens do checklist pelo
navegador, vídeos MP4 H.264 reais e imagem WebP, Range 206/416 e persistência
após restart/force-recreate foram confirmados. TV Piloto e TV do Pátio,
volume SQLite e permissões não-root foram preservados; signage-media criado.
Esses resultados não foram reexecutados nesta atualização documental.

O operador manteve temporariamente 10.4.254.202:8080 durante os testes da
ETAPA 005, como
risco temporariamente aceito. O binding não constitui proteção de acesso
nem autorização para liberação institucional. Autenticação, autorização e
proteção CSRF foram implementadas e validadas pelo operador na ETAPA 006,
no ambiente local com túnel SSH descrito abaixo. Não transmitir
credenciais/cookies no HTTP da LAN.
Compatibilidade com TV Boxes continua pendente.

A ETAPA 006 está concluída e validada operacionalmente pelo operador no
ambiente local de testes. Implementa login, Argon2id, sessões opacas
persistentes, autorização admin, logout com revogação, pré-sessão de login e
CSRF em formulários/API. Config/build aprovados, imagem digital-signage:etapa006,
container digital-signage-app healthy e inicialização sem erros nos logs
apresentados. A suíte em container teve **267 passed, 1 warning em 172.98
segundos**, sem falhas, incluindo aprovação de todos os testes anteriores.
O warning é de depreciação Starlette/AnyIO. Separadamente, os 18 itens manuais
foram aprovados; primeiro administrador criado com sucesso pelo operador.

Binding efetivo confirmado: 127.0.0.1:8080. Acesso administrativo por túnel SSH,
sem exposição direta do HTTP à rede institucional no ambiente validado.
Configuração temporária: SIGNAGE_BIND_IP=127.0.0.1, SIGNAGE_PORT=8080,
SESSION_COOKIE_SECURE=false e LOCAL_AUTH_TEST_MODE=true. Cookies observados
com HttpOnly habilitado, SameSite=Lax e Secure desabilitado conforme HTTP local.
CSRF autenticado sem token retornou 403; Range autenticado bytes=0-99 retornou
206 Partial Content com 100 bytes. Login/logout, autorização, preservação de
telas/mídias, persistência após restart conforme expiração e usuários/telas/
mídias após recriação foram confirmados pelo operador.

Resultados fornecidos pelo operador nesta solicitação, sem execução ou
reexecução pelo Codex nesta atualização documental. O bloqueio sudo inicial
e as verificações estáticas permanecem no histórico da implementação;
evidências atuais em [Validação operacional da ETAPA 006](#validação-operacional-da-etapa-006).
O sistema não está liberado para uso institucional amplo. HTTPS válido,
SESSION_COOKIE_SECURE=true, LOCAL_AUTH_TEST_MODE=false, revisão das políticas
de acesso e definição de autenticação dos futuros players continuam necessários.
Backup/restauração conjunta permanecem sem confirmação de execução.

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
- biblioteca unificada MediaAsset, tabela media_assets e arquivos com UUID;
- upload e catálogo administrativo de MP4/H.264, JPEG, PNG, WebP e GIF;
- validação por ffprobe/Pillow, limites configuráveis, animações preservadas;
- pré-visualização img/video e entrega por id com FileResponse/HTTP Range;
- volume signage-media definido para /app/media, sem alterar signage-data;
- testes de mídia definidos com banco e diretório temporários isolados.
- User, AuthSession, LoginChallenge e LoginLimit persistentes no SQLite;
- Argon2id e bootstrap administrativo interativo, sem credenciais padrão;
- login/logout com pré-sessão CSRF, cookies opacos e revogação no servidor;
- autorização admin em painel, API de telas e arquivos, com CSRF nas escritas;
- cookies Secure por padrão, timeouts absoluto/inatividade e limitação de login;
- configuração de transporte validada, no-store e proteção antes de ler corpos;
- novos testes isolados e regressão adaptada com login/CSRF reais.

## Ainda não implementado

- HTTPS institucional e configuração operacional de transporte seguro;
- MFA, recuperação de conta e auditoria completa (fora da ETAPA 006);
- ingestão/exibição segura de SVG;
- playlists e associação mídia-tela;
- player web;
- integração com TV Box;
- Chromium kiosk;
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

## Próximo passo recomendado

Auditoria do diff documental pelo operador. Antes da disponibilização
institucional: HTTPS com certificado válido, SESSION_COOKIE_SECURE=true,
LOCAL_AUTH_TEST_MODE=false, revisão das políticas de acesso e definição de
autenticação específica para os futuros players das TV Boxes. Validar backup
conjunto e restauração em ambiente isolado autorizado; não há evidência de
execução desses procedimentos nesta validação. MFA, recuperação administrativa
e auditoria de operações permanecem trabalhos futuros conforme decisões
existentes. Compatibilidade com TV Boxes ainda exige validação específica.
Nenhuma etapa seguinte foi iniciada nesta atualização documental.

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

## Registro da ETAPA 005

### Estado inicial e inspeções

pwd confirmou /home/administrador/digital-signage. Working tree limpa,
branch main, HEAD 7a4ce3b, sincronizada com a referência local origin/main.
git log confirmou 1d0e394 da ETAPA 004 e os commits de ADR/prompt da ETAPA 005.
AGENTS.md, README.md, STATUS, ARCHITECTURE, os cinco ADRs e etapa005.md
foram lidos integralmente antes de alterar arquivos. Código, Dockerfile,
Compose, dependências, configuração de exemplo, regras de ignore, templates,
CSS, serviços, banco e testes foram inspecionados. Documentos operacionais
e SECURITY (inicialmente vazio) foram inspecionados antes de editar.
Não foi encontrada divergência relevante entre documentação e código.

docker compose config --quiet passou sem sudo, sem acessar o daemon.
sudo -n docker compose ps foi bloqueado por no new privileges: estado real
de containers, volumes e redes não confirmado na implementação inicial.
Nenhum contorno de sudo, alteração operacional, instalação no host ou acesso
ao SQLite real.
ETAPAS 001–004 permanecem com a validação histórica fornecida pelo operador.

### Arquivos criados

- app/services/media.py;
- app/routes/admin/media.py;
- app/routes/media.py;
- app/templates/admin/media/form.html;
- app/templates/admin/media/list.html;
- tests/test_media.py.

### Arquivos modificados

- app/config.py;
- app/models.py;
- app/main.py;
- app/templates/base.html;
- app/static/admin.css;
- tests/conftest.py;
- requirements.txt;
- Dockerfile;
- compose.yaml;
- .dockerignore;
- .env.example;
- README.md;
- docs/ARCHITECTURE.md;
- docs/DEPLOYMENT.md;
- docs/OPERATIONS.md;
- docs/SECURITY.md;
- docs/STATUS.md.

### Implementação e decisões

MediaAsset usa media_assets com id, título obrigatório (1–200 caracteres),
kind video/image, nome original (até 255 caracteres, somente exibição),
nome físico UUID único, MIME validado, tamanho, dimensões, duração e codecs
do vídeo, created_at UTC. frame_rate e frame_count completam os metadados.
CHECKs exigem tamanho/dimensões positivos e metadados coerentes por tipo.
Screen não foi modificado; create_all cria a nova tabela no próximo startup,
sem Alembic ou alteração do esquema existente.

UploadFile é lido em blocos de 1 MiB para temporário 0600 sob /app/media.
Limites configuráveis em MiB reais: vídeo 250 e imagem 10; arquivo vazio
é recusado. Não se confia em Content-Length ou MIME do navegador. Arquivo
validado é publicado sem sobrescrita com UUID, usando hard link exclusivo
e removendo o temporário no mesmo volume. Falha no banco faz rollback e
remove o definitivo recém-criado. finally tenta limpar cada caminho mesmo
se outra remoção falhar; falha de limpeza é registrada e retorna HTML 503.
Queda abrupta entre publicação e commit pode deixar resíduos; não foi
implementada exclusão automática ou coleta de arquivos órfãos.

Vídeo: MP4 real com uma trilha H.264 yuv420p/8 bits, até 1920 × 1080 e 30 FPS,
AAC opcional (uma trilha), sem outras trilhas. yuv420p foi escolhido como
perfil inicial conservador; outros pixel formats são recusados com razão.
ffprobe usa lista de argumentos, shell=False, protocolo file, referências
externas desabilitadas, timeout padrão 15 s, saída conjunta até 64 KiB,
sondagem limitada e um thread. Valida formato/marca, codecs, dimensões,
duração finita, FPS e presença de pacotes; erros, timeout, JSON inválido e
truncamentos detectáveis são recusados. Leitura de boxes é limitada a 10.000.
Não há transcodificação nem validação de decodificação completa de frames.

Imagens: Pillow==12.3.0, conteúdo e extensão coerentes para JPEG, PNG,
WebP e GIF; verify seguido de reabertura/load de todos os quadros permitidos.
Limites adicionais configuráveis: 20.000.000 pixels/quadro, 100 quadros e
100.000.000 pixels acumulados. Animações GIF/WebP permanecem byte a byte no
formato original. SVG bruto é rejeitado com mensagem explícita; nenhuma
biblioteca de SVG foi adicionada. Versão Pillow, APIs e pacote Debian
consultados nas fontes oficiais registradas em ARCHITECTURE.

Interface: GET /admin/media, GET /admin/media/new e POST /admin/media;
catálogo determinístico por id, título, tipo/MIME, nome original, bytes/MiB,
dimensões, duração/codecs/FPS ou quadros, data UTC e pré-visualização.
Jinja2 com escape automático, base.html e CSS local responsivo. img lazy;
video controls muted preload=metadata, sem autoplay. Sucesso usa 303;
validação esperada usa HTML 422/413 e falhas operacionais HTML 500/503.
GET /media/{media_id}/file fica em router separado, resolve banco e confina
nome/caminho UUID, 404 para ausentes, FileResponse com MIME validado, inline,
nosniff e CSP. Range válido usa 206, fora do arquivo 416 e malformado 400
conforme Starlette. A suíte e Range 206/416 foram posteriormente aprovados
pelo operador, conforme registro abaixo.

Docker: digital-signage:etapa005, único signage-app, signage-data:/app/data
preservado e signage-media:/app/media adicionado na implementação inicial.
/app/media preparado no build para UID/GID 10001. Sem chmod 777, novo serviço,
bind mount, alteração de porta/healthcheck ou configuração global.
Debian fornece ffprobe no pacote ffmpeg; instalado com no-install-recommends
somente na imagem, também para gerar vídeos sintéticos dos testes.
Não foi construído ou iniciado container pelo agente na implementação inicial;
build e implantação foram posteriormente confirmados pelo operador.

### Testes definidos e verificações da implementação inicial

83 novos casos de mídia e 66 casos anteriores: 149 definidos por inspeção
AST na implementação inicial, não por coleta pytest naquele momento.
Os 149 testes foram posteriormente executados e aprovados pelo operador,
conforme registro abaixo. Cobertura: catálogo/formulário, todos os formatos,
GIF/WebP animados, MP4 real sintético com/sem áudio, metadados, incompatíveis,
truncamento, vazios/corrompidos, tamanhos real/exato/excedido, pixels/quadros,
timeout/erro/saída excessiva/JSON ffprobe, UUID/path traversal, escape HTML,
persistência em nova inicialização temporária, entrega/headers, Range
206/416/400, ausentes, limpeza/rollback, colisão UUID sem sobrescrita, SVG,
isolamento de banco/mídia e preservação de tela criada no teste.

Efetivamente executado na implementação inicial: ast.parse em 21 arquivos
Python, aprovado;
docker compose config --quiet, aprovado sem sudo/daemon; revisão dos diffs
e arquivos novos e git diff --check, aprovados. Verificações estáticas não
confirmam imports, build, pytest, reprodução ou persistência operacional.
Comparação AST confirmou Screen, endpoints base e lifespan preservados;
oito arquivos anteriores de banco/schemas/API/admin/serviço/testes permanecem
idênticos a HEAD. Comparação do Compose normalizado confirmou serviço único,
binding, rede, restart, healthcheck, DATABASE_URL e volume SQLite preservados,
volume de mídia adicionado e substituição das seis variáveis de limites.
A primeira versão desse script de comparação teve TypeError por confundir
a lista de montagens do serviço com a definição de volumes; o script foi
corrigido e reexecutado com sucesso, sem alteração da aplicação por esse erro.

Bloqueio na implementação inicial (validação posteriormente concluída pelo
operador, sem contorno pelo agente):

Tentativa sudo -n docker compose run --rm signage-app pytest -q
-p no:cacheprovider bloqueada por no new privileges antes de executar testes.
Resultado pytest daquela sessão: 0 executados, 0 aprovações, falhas/warnings
de teste não avaliados. Os 66 passed/3 warnings da ETAPA 004 são históricos
do operador e não constituem regressão executada da ETAPA 005.
Tentativa sudo -n docker compose logs --tail=100 signage-app também bloqueada;
nenhum log real da aplicação obtido naquela sessão. Build/up não executados
pelo agente na implementação inicial. A validação operacional pelo operador
resolveu as pendências de build, suíte, inicialização e logs, conforme abaixo.

### Segurança, problemas e pendências

Sem autenticação, autorização ou CSRF; controles obrigatórios na ETAPA 006,
antes da liberação institucional. Testes somente com operadores confiáveis;
não expor à Internet. O operador decidiu manter temporariamente o binding
10.4.254.202:8080 durante os testes, como risco temporariamente aceito;
isso não protege o acesso nem autoriza liberação institucional.
.env, dados persistentes e configurações globais não alterados pelo agente.
Spool multipart do framework precede a validação incremental por arquivo;
não há quota global ou controle de concorrência. Monitorar espaço temporário
e dos volumes. O backup local do SQLite anterior à ETAPA 005 foi criado pelo
operador antes da implantação, conforme abaixo. Backup consistente dos dois
volumes após inclusão de mídias e ensaio de restauração isolada estão
documentados, mas continuam sem confirmação de execução.

Pendências de implementação da ETAPA 005: nenhuma identificada nos resultados
informados. Build, suíte completa, metadados de mídias reais, Range 206/416,
regressão, healthy/logs, os 14 itens do checklist pelo navegador, persistência,
backup SQLite pré-implantação e permissões foram confirmados pelo operador.
Essas validações não permanecem pendentes.

Pendências reais: compatibilidade com TV Boxes; autenticação, autorização e
CSRF na ETAPA 006; confirmação de backup conjunto de banco/mídias e ensaio
de restauração. Monitoramento de espaço temporário e dos volumes permanece
como rotina operacional. O warning de depreciação Starlette/AnyIO não causou
falhas e não foi corrigido nesta atualização. SVG seguro, playlists,
associações e player continuam não implementados e fora do escopo da etapa.

Próximo passo recomendado: auditoria do diff e versionamento pelo operador.
Nenhuma etapa posterior foi iniciada, nem playlists, associações ou player/TV
Box implementados. Nenhuma cópia alternativa do projeto, mudança global,
tentativa de contorno sudo, git add, commit ou push pelo agente.

## Validação operacional da ETAPA 005

ETAPA 005 concluída e validada com sucesso, conforme resultados reais
fornecidos pelo operador e registrados em 2026-10-14. Todos os comandos,
testes e observações operacionais desta seção foram executados ou confirmados
pelo operador; não foram executados nem reexecutados pelo Codex nesta
atualização documental.

### Build, Docker e armazenamento

- `docker compose config --quiet`: aprovado;
- `docker compose build`: aprovado;
- imagem: `digital-signage:etapa005`;
- container: `digital-signage-app`, estado `healthy`;
- binding: `10.4.254.202:8080`;
- logs apresentados: inicialização normal, sem erros;
- aplicação executando como `uid=10001(signage) gid=10001(signage)`;
- `/app/data` e `/app/media` pertencem a `signage:signage`;
- volume SQLite existente `signage-data` preservado;
- volume `signage-media` criado.

### Testes automatizados

Comando executado pelo operador:

```bash
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
```

Resultado: **149 passed, 1 warning**, duração **18.60 segundos**, nenhuma
falha. O warning é de depreciação Starlette/AnyIO; não impediu a aprovação
da suíte. Nenhuma correção de código ou dependências nesta atualização.

### Regressão

| Verificação | Resultado confirmado pelo operador |
|---|---|
| GET `/` | HTTP 200 |
| GET `/health` | HTTP 200 |
| GET `/api/screens` | HTTP 200 |
| Telas TV Piloto e TV do Pátio | Preservadas |

### Validação pelo navegador

Os 14 itens do checklist foram aprovados pelo operador:

1. Funcionamento do catálogo.
2. Formulário de upload.
3. Cadastro de imagens.
4. Cadastro de MP4 H.264.
5. Identificação de dimensões, duração e codecs.
6. Pré-visualização de imagens.
7. Reprodução de vídeos.
8. Aceitação de WebP/GIF.
9. Rejeição de arquivos inválidos.
10. Rejeição explícita de SVG.
11. Preservação do painel administrativo de telas.
12. Persistência após restart.
13. Persistência após force-recreate.
14. Responsividade da interface.

Vídeos MP4 H.264 reais e uma imagem WebP foram cadastrados e pré-visualizados,
conforme evidências fornecidas pelo operador. Isso confirma a validação no
navegador; a compatibilidade com TV Boxes permanece pendente.

### HTTP Range

- Requisição de intervalo válido: HTTP 206, aprovada pelo operador;
- requisição de intervalo fora do arquivo: HTTP 416, aprovada pelo operador.

### Backup pré-implantação

O operador criou, antes da implantação:

`/home/administrador/signage-backups/signage-before-005.db`

Esse é um backup local do SQLite anterior à ETAPA 005. A pendência desse
backup pré-implantação está resolvida. O resultado informado não comprova
backup conjunto de banco e mídias da ETAPA 005 nem ensaio de restauração;
essas confirmações permanecem pendentes.

### Segurança administrativa

O operador decidiu manter temporariamente o binding `10.4.254.202:8080`
durante os testes. A condição é registrada como **risco temporariamente
aceito**, pois autenticação, autorização e proteção CSRF ainda não existem.
O binding não constitui proteção de acesso nem autorização para liberar
o sistema institucionalmente. Esses controles permanecem obrigatórios na
ETAPA 006, antes da liberação institucional. Uso somente com operadores
confiáveis em ambiente restrito; não expor à Internet.

### Registro desta atualização documental

Nenhum arquivo criado. Alterados somente README.md, docs/STATUS.md,
docs/ARCHITECTURE.md, docs/DEPLOYMENT.md, docs/OPERATIONS.md e docs/SECURITY.md.
Decisões: registrar os resultados fornecidos pelo operador, remover as
pendências efetivamente resolvidas, preservar o bloqueio sudo inicial como
histórico e atualizar o checklist para os 14 itens confirmados. O backup foi
registrado com seu alcance real e a decisão de binding como risco temporário.

Verificação documental: diff revisado e `git diff --check` aprovado. Os testes
operacionais, comandos Docker e validações pelo navegador não foram
reexecutados; seus resultados são os fornecidos pelo operador.
Problema registrado: 1 warning de depreciação Starlette/AnyIO, sem falhas.
Pendências: compatibilidade com TV Boxes, segurança administrativa obrigatória
na ETAPA 006 e confirmação de backup conjunto/restauração. Próximo passo
recomendado: revisão do diff e versionamento pelo operador.

Nenhuma funcionalidade implementada, alteração de código, Docker, banco ou
configuração do servidor nesta atualização; alterações de implementação
preexistentes no working tree foram preservadas. A ETAPA 006 não foi iniciada.
Nenhum git add, git commit ou git push executado.

## Registro da ETAPA 006

Registro histórico da implementação inicial. O bloqueio sudo, os testes não
executados e as pendências descritos nessa ocasião são preservados para
rastreabilidade. A validação posterior pelo operador está registrada em
[Validação operacional da ETAPA 006](#validação-operacional-da-etapa-006),
com distinção entre testes automatizados e manuais e limites da conclusão.

### Estado inicial, leituras e inspeções

pwd confirmou /home/administrador/digital-signage; branch main, working tree
limpa, HEAD 0c9bb18. git log -3: 0c9bb18 (prompt 006), 15de5c7 (ADR 0006)
e 3166a7d (biblioteca de mídias). Referência local origin/main alinhada.
AGENTS.md, README.md, STATUS, ARCHITECTURE, SECURITY, DEPLOYMENT, OPERATIONS,
os seis ADRs e docs/prompts/etapa006.md lidos integralmente. Inspecionados
todos os modelos, configuração, engine/get_session, schemas, rotas, serviços,
templates/CSS, upload/FileResponse, testes, dependências, Dockerfile, Compose
e arquivos de ignore/.env.example. Não havia autenticação/middleware de
sessão. Não identificada divergência relevante que impedisse a implementação.
.env não foi exibido nem editado; nenhum segredo operacional registrado.

sudo -n docker compose ps foi bloqueado por no new privileges. Estado real
de containers, redes, volumes, binding e logs não confirmado nesta sessão;
nenhuma tentativa de contorno. A validação da ETAPA 005 continua sendo a
fornecida pelo operador, sem representar regressão executada da ETAPA 006.

### Arquivos criados

- app/services/auth.py;
- app/security.py;
- app/routes/admin/auth.py;
- app/scripts/__init__.py;
- app/scripts/bootstrap_admin.py;
- app/templates/admin/auth/login.html;
- tests/helpers.py;
- tests/test_auth.py.

### Arquivos modificados

- app/config.py;
- app/models.py;
- app/main.py;
- app/routes/admin/screens.py;
- app/routes/admin/media.py;
- app/templates/base.html;
- app/templates/admin/screens/form.html;
- app/templates/admin/screens/list.html;
- app/templates/admin/media/form.html;
- app/static/admin.css;
- requirements.txt;
- Dockerfile;
- compose.yaml;
- .dockerignore;
- .env.example;
- tests/conftest.py;
- tests/test_screens.py;
- tests/test_admin_screens.py;
- tests/test_media.py;
- README.md;
- docs/ARCHITECTURE.md;
- docs/SECURITY.md;
- docs/DEPLOYMENT.md;
- docs/OPERATIONS.md;
- docs/STATUS.md.

### Implementação e decisões de segurança

Dependência nova: argon2-cffi==25.1.0, somente na imagem. Argon2id explícito:
m=19456 KiB, t=2, p=1, salt=16 bytes e hash=32 bytes, mínimo ADR/OWASP com
memória limitada por verificação. APIs e versão consultadas nas fontes
primárias listadas em ARCHITECTURE; instalação/imports aguardavam build na
implementação inicial. Build e suíte foram posteriormente aprovados pelo operador.

Tabelas adicionais: users (username normalizado/único, hash, role admin/viewer,
active e timestamps UTC); auth_sessions (FK usuário, hash SHA-256 do token,
CSRF secreto, criação, atividade, expiração absoluta e revoked); login_challenges
(hashes separados de cookie/CSRF, criação e expiração); login_limits (chave
hash, contador e expiração). create_all incremental preserva screens e
media_assets, sem Alembic, recriação ou alteração do banco real nesta sessão.

Bootstrap: python -m app.scripts.bootstrap_admin no container, interativo,
sem argumentos, com getpass/confirmação e recusa de terminal sem entrada
oculta. Username trim/lowercase ASCII de 3–64 caracteres; senha de 16–128
caracteres e três classes entre minúsculas/maiúsculas/números/símbolos.
BEGIN IMMEDIATE serializa concorrência, recusa usuário existente ou qualquer
admin já criado; não sobrescreve nem cria conta no startup. Comando previsto
somente para o operador, após testes, backup e transporte seguro:

```bash
sudo docker compose exec -it signage-app python -m app.scripts.bootstrap_admin
```

Esse comando não foi executado pelo Codex em produção. Testes do bootstrap
foram definidos exclusivamente com engine SQLite temporário. Posteriormente,
o operador confirmou a criação do primeiro administrador com sucesso.

GET /admin/login cria desafio persistente de 10min; cookie/CSRF independentes
com 256 bits cada, armazenados como hashes. POST valida CSRF e consome o
desafio atomicamente, inclusive em falha de senha; sucesso gera nova sessão
opaca com 256 bits, nunca reaproveita pré-sessão. Corpo de login urlencoded
limitado a 8 KiB/três campos únicos, sem reflexão de senha em erros.
POST /admin/logout exige sessão/CSRF, revoga no banco e expira os cookies.

Middleware ASGI verifica transporte e usuário ativo admin antes de ler
corpos de caminhos protegidos, incluindo acesso direto a todas as ações.
API exige X-CSRF-Token antes de ler JSON; dependência compartilhada confere
CSRF HTML de criação/edição/toggle/upload/logout antes dos serviços.
GET /admin/csrf entrega o token somente ao admin autenticado em JSON no-store.
CSRF é validado com comparação resistente a diferenças de tempo; tokens não
são aceitos em URL/query string. Formulários incluem campo oculto e Sair usa POST.

Cookies HTTPS __Host-signage-session/__Host-signage-login, Secure por padrão,
HttpOnly, SameSite=Lax, Path=/, sem Domain. Modo local usa nomes distintos.
Timeout absoluto 8h, inatividade 30min, conferidos no servidor. Mutações
autorizadas bem-sucedidas renovam atividade a cada 5min, sem estender prazo
absoluto. GETs protegidos e acessos negados não escrevem no SQLite ou mídias;
leituras contínuas não renovam inatividade. GET login é a criação de desafio
explicitamente exigida pelo fluxo CSRF. Logout invalida cópia do mesmo cookie,
sem revogar outras sessões da conta; expiradas/revogadas não autorizam acesso.

Brute force: 5 tentativas/conta e 20/origem em janela fixa de 15min, persistentes,
inclusive logins corretos; 429 genérico ao atingir limite. Reservas são atômicas
antes de verificar Argon2, sem lock durante hashing; usuário inexistente usa
hash fictício em memória e mensagem genérica como usuário inválido/inativo.
Origem usa request.client; X-Forwarded-For não é lido diretamente. Limpeza de
desafios/limites/sessões expirados tem teto de 100 registros por operação.
Senha, cookie, CSRF e hashes não são registrados; Uvicorn sem access log e
erros SQL de autenticação têm resposta genérica, sem traceback/parâmetros.

### Mudanças intencionais de contrato HTTP

| Acesso em transporte permitido | Resultado implementado |
|---|---|
| GET /admin, telas, mídias ou /admin/csrf sem sessão | 303 para /admin/login |
| POST administrativo sem sessão | 401, sem executar ação |
| API de telas, inclusive GET, sem sessão | 401 JSON |
| Download de mídia sem sessão | 401 JSON |
| Usuário ativo com papel insuficiente | 403 |
| Escrita autenticada sem CSRF válido | 403, sem mutação |
| Login com credencial incorreta/inativa/inexistente | 401 com mensagem genérica |
| Login limitado | 429 com mensagem genérica |
| Login/áreas protegidas em HTTP com Secure=true | 503, sem emitir cookie |
| Saúde / e /health; CSS necessário | Permanecem públicos |
| /docs, /redoc, /openapi.json | Permanecem desabilitados (404) |

Semântica funcional das rotas autorizadas é preservada, inclusive FileResponse,
HTTP Range 206/416/400, uploads e administração de telas. Escape HTML, CSP
de arquivos e nosniff preservados; HTML sensível recebe CSP compatível com
CSS/img/video local. Respostas protegidas têm Cache-Control: no-store.

### Testes definidos e verificações da implementação inicial

149 casos anteriores preservados: 2 base, 21 API de telas, 43 administrativos
e 83 mídias. Cliente de regressão usa login real em HTTPS simulado e CSRF,
sem override de autorização. Testes de persistência foram adaptados para
login apropriado; assertivas funcionais anteriores mantidas. 118 novos casos
cobrem bootstrap/concorrência/entrada oculta, Argon2id, login genérico,
pré-sessão/CSRF/replay/concorrência, entropia/hashes/cookies, limites persistentes
e expiração, rotas anônimas/roles, negação sem mutação, CSRF API/formulários,
logout/cookie copiado, inatividade/expiração absoluta, frequência de atividade,
GET sem escrita, persistência de sessão, URLs sem autenticação, saúde/docs,
configuração HTTP insegura e preservação de tabelas/registros anteriores.
Engine, diretório de mídias, configuração e relógio são isolados nos testes.

Executado pelo Codex na sessão de implementação inicial:

- ast.parse em 28 arquivos Python: aprovado;
- contagem por inspeção AST: 267 casos definidos, sem coleta pytest;
- docker compose config --quiet: aprovado sem sudo/daemon;
- comparação Compose normalizado com HEAD: serviço único, portas, volumes,
  redes, healthcheck, restart, container_name, build e variáveis anteriores
  preservados; tag 006 e configuração de autenticação validadas;
- AuthSettings via runpy/biblioteca padrão: 3 configurações válidas e
  9 recusas de configuração insegura/contraditória, aprovadas;
- revisão de diffs/arquivos novos e git diff --check: aprovados.

Preservação estática adicional: 20 arquivos de banco/schemas/API/serviços,
testes base, regras, ADRs e prompts permanecem idênticos a HEAD; classes
Screen/MediaAsset e funções dos testes anteriores preservadas, sem skip/xfail.
Whitespace dos oito arquivos novos também aprovado. A primeira checagem
no-index interpretou exit 1 (arquivos diferentes) como erro; o script foi
corrigido e reexecutado, sem erro de whitespace ou alteração de aplicação.

Resultado pytest da implementação inicial: **0 executados, 0 aprovações runtime**;
falhas/warnings de teste não avaliados. Build, coleta/suíte em container,
imports, geração real de cookies, Argon2id runtime, HTTP, logs e navegador
não executados pelo Codex naquela ocasião pela restrição sudo. Não houve
instalação de dependências no host para contornar. Os 149 passed/1 warning da
ETAPA 005 eram resultados históricos do operador, não regressão da ETAPA 006
naquele momento. Posteriormente, o operador executou a suíte da ETAPA 006:
267 passed, 1 warning em 172.98 segundos, sem falhas, conforme seção seguinte.

### Docker, transporte, riscos e pendências da implementação inicial

Imagem definida digital-signage:etapa006, ainda não construída naquela sessão
de implementação; posteriormente construída e aprovada pelo operador.
Um signage-app, UID/GID 10001, signage-data e signage-media, healthcheck e
binding preservados. .env.example/Compose documentam Secure/local mode,
binding declarado, IPs de proxy confiável, timeouts, janela e limites de login.
FORWARDED_ALLOW_IPS vazio na imagem/Compose significa nenhuma confiança em
headers encaminhados; aceita apenas IPs específicos, nunca '*'.
Configuração validada antes de criar tabelas, sem downgrade automático.

Institucional exige HTTPS válido. Exceção temporária exige escolha e alteração
manual pelo operador: binding efetivo 127.0.0.1:8080, Secure=false,
LOCAL_AUTH_TEST_MODE=true, nenhum proxy confiável, Host local e acesso por SSH.
A aplicação não inspeciona daemon/túnel; confirmar ports reais é obrigatório.
O binding HTTP da LAN aceito na ETAPA 005 não autoriza transmissão de credenciais
ou cookies na ETAPA 006. Nenhum TLS/proxy/certificado foi instalado aqui.

Pendências ao final da implementação inicial (histórico): build/suíte completa
e quantidade/falhas/warnings reais;
transporte seguro/binding/cookies efetivos; backup conjunto e restauração;
bootstrap pelo operador, login/limites/CSRF/autorização/logout/expiração no
navegador/API; Range autorizado e persistência de usuário/sessão/dados após
restart/recriação, preservando TV Piloto, TV do Pátio e mídias anteriores;
healthy/logs e registro das evidências operacionais em STATUS.
Build, suíte, transporte local/binding/cookies, bootstrap, autenticação,
autorização/CSRF/logout, persistência e Range foram posteriormente confirmados
pelo operador nos limites dos resultados da seção seguinte. Backup conjunto
e restauração continuam sem evidência de execução. A persistência após restart
respeitando expiração foi aprovada conforme checklist, sem registro de
medições manuais adicionais de cada timeout ou dos limites de login.

Riscos remanescentes: sem HTTPS institucional, MFA, recuperação web, auditoria
completa ou autorização específica para TV Boxes; limitação simples sujeita
a bloqueio deliberado de conta/origem e consumo de recursos sob carga;
desafios/volumes sem quota global, limpeza limitada sem job automático.
Backup SQLite contém hashes e segredos CSRF, exigindo acesso restrito.
Compatibilidade com TV Boxes permanece pendente. Na implementação inicial
não havia resultado de regressão runtime; a suíte posteriormente executada
pelo operador permaneceu integralmente aprovada. Isso não libera uso institucional.

Próximo passo indicado naquela ocasião: operador auditar diff, executar
build/pytest, selecionar transporte seguro e validar o checklist de OPERATIONS,
registrando evidências antes do versionamento. A validação foi posteriormente
concluída conforme abaixo; os próximos passos atuais estão no início deste
documento. Nenhuma etapa seguinte foi iniciada nesta atualização.

Nenhum git add, commit ou push; nenhuma branch criada ou histórico alterado.
Nenhum bootstrap/login no banco real pelo Codex, instalação de dependências
no host, mudança de .env/binding efetivo, firewall, SSH, sudoers, rede,
daemon Docker ou serviços externos. Nenhuma cópia alternativa do projeto,
remoção de volumes ou funcionalidade fora da ETAPA 006.

## Validação operacional da ETAPA 006

ETAPA 006 — Autenticação, autorização e segurança administrativa — concluída
e validada com sucesso pelo operador no ambiente local de testes por túnel SSH.
Fonte das evidências: resultados reais fornecidos pelo operador nesta
solicitação, registrados documentalmente em **2026-10-15**. Essa é a data do
registro, sem atribuir uma data de execução não informada.

Todos os comandos Docker, testes automatizados, bootstrap, requisições HTTP e
verificações pelo navegador desta seção foram executados ou confirmados pelo
operador. **O Codex não os executou nem reexecutou nesta atualização documental.**
As verificações do Codex nesta atualização se limitam à documentação e ao Git.

### Build, Docker e transporte confirmados pelo operador

- `sudo docker compose config --quiet`: aprovado;
- `sudo docker compose build`: aprovado;
- imagem: `digital-signage:etapa006`;
- container: `digital-signage-app`, estado `healthy`;
- logs apresentados: inicialização sem erros;
- binding efetivo: `127.0.0.1:8080`;
- acesso administrativo realizado através de túnel SSH;
- nenhuma exposição direta do serviço HTTP à rede institucional no ambiente
  validado.

Configuração temporária informada pelo operador, sem leitura ou alteração do
`.env` pelo Codex nesta atualização:

```text
SIGNAGE_BIND_IP=127.0.0.1
SIGNAGE_PORT=8080
SESSION_COOKIE_SECURE=false
LOCAL_AUTH_TEST_MODE=true
```

Destina-se exclusivamente aos testes locais através de túnel SSH. A aprovação
desse ambiente não constitui liberação para uso institucional amplo.

### Testes automatizados executados pelo operador

Comando executado:

```bash
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
```

Resultado real: **267 passed, 1 warning**, duração **172.98 segundos**,
**nenhuma falha**. Warning de depreciação Starlette/AnyIO, sem impedir a
aprovação; nenhuma correção de código ou dependências nesta atualização.
Todos os testes anteriores permaneceram aprovados. A contagem estática
anterior de 149 casos preservados e 118 novos foi sucedida por esse resultado
real da suíte em container. Os resultados manuais abaixo são registrados
separadamente e não compõem os 267 testes pytest.

### Autenticação e autorização confirmadas pelo operador

| Verificação | Resultado real |
|---|---|
| GET `/health` | HTTP 200 |
| GET `/admin/screens` sem sessão | HTTP 303, redirecionando para `/admin/login` |
| GET `/api/screens` sem sessão | HTTP 401 |
| GET `/media/1/file` sem sessão | HTTP 401 |
| Criação do primeiro administrador pelo operador | Aprovada |
| Login com credenciais corretas | Aprovado |
| Login com senha incorreta | Acesso recusado |
| Logout | Aprovado |
| Acesso administrativo após logout | Exige nova autenticação |

### Validação manual pelo navegador

O operador confirmou a aprovação dos 18 itens:

1. Página de login acessível sem autenticação: aprovado.
2. Login correto: aprovado.
3. Senha incorreta recusada: aprovado.
4. Painel de telas protegido: aprovado.
5. Painel de mídias protegido: aprovado.
6. API de telas sem sessão retorna 401: aprovado.
7. Download de mídia sem sessão retorna 401: aprovado.
8. Administrador autenticado consegue editar telas: aprovado.
9. Administrador autenticado consegue cadastrar mídia: aprovado.
10. Escrita na API sem token CSRF retorna 403: aprovado.
11. Logout encerra a sessão: aprovado.
12. Acesso após logout exige login novamente: aprovado.
13. Cookies conferidos no navegador: aprovado.
14. HTTP Range de MP4 com sessão válida: aprovado.
15. TV Piloto, TV do Pátio e mídias anteriores preservadas: aprovado.
16. Dados e sessão persistem após restart, respeitando as regras implementadas
    de expiração: aprovado conforme checklist do operador.
17. Recriação do container preserva usuários, telas e mídias: aprovado.
18. Interface utilizável em computador e janela estreita: aprovado.

### Resultados complementares de segurança no navegador

Evidências específicas do operador, detalhando os itens 10, 13 e 14:

| Verificação manual | Resultado real |
|---|---|
| Escrita autenticada sem `X-CSRF-Token` (item 10) | HTTP 403; proteção CSRF confirmada |
| Cookies em HTTP local (item 13) | HttpOnly habilitado; SameSite=Lax; Secure desabilitado conforme configuração temporária |
| Transporte de rede do teste local | Túnel SSH |
| MP4 com sessão válida e `Range: bytes=0-99` (item 14) | HTTP 206 Partial Content; 100 bytes recebidos |

O resultado de cookies refere-se ao modo local com Secure=false; não comprova
implantação HTTPS institucional. O item 16 é a confirmação do checklist do
operador, sem acrescentar medições manuais individuais de timeout. Range
206/416/400 tem cobertura automatizada descrita no registro de implementação;
o resultado manual específico da ETAPA 006 é 206 com 100 bytes.
Restart/recriação confirmam persistência, não execução de restauração.

### Segurança, limitações e pendências remanescentes

Não há liberação para uso institucional amplo. Antes dessa disponibilização,
permanecem necessários:

- HTTPS com certificado válido;
- `SESSION_COOKIE_SECURE=true`;
- `LOCAL_AUTH_TEST_MODE=false`;
- revisão das políticas de acesso;
- definição de autenticação específica para os futuros players das TV Boxes.

Validação de backup/restauração conjunta, MFA, recuperação administrativa e
auditoria de operações permanecem trabalhos futuros conforme decisões
existentes. Não houve evidência do operador de execução de backup conjunto ou
teste de restauração nesta validação. O backup SQLite anterior à ETAPA 005
continua registrado apenas com o alcance daquela evidência histórica.
Compatibilidade com TV Boxes também depende de validação específica futura.

O warning Starlette/AnyIO permanece registrado sem falhas e sem correção
nesta atualização. As demais limitações de recursos, quotas, limpeza e acesso
a backups descritas em SECURITY e no histórico da implementação permanecem.

### Registro desta atualização documental

- Arquivos criados: nenhum.
- Arquivos alterados nesta atualização: README.md, docs/STATUS.md,
  docs/SECURITY.md, docs/OPERATIONS.md, docs/ARCHITECTURE.md e docs/DEPLOYMENT.md.
- Decisões: registrar os resultados fornecidos pelo operador; separar suíte
  automatizada, checklist manual e verificações complementares; encerrar as
  pendências operacionais efetivamente resolvidas, preservando o bloqueio sudo
  e a ausência de execução pelo Codex na implementação inicial como histórico.
- Verificações documentais pelo Codex: diff revisado; `git diff --check`
  aprovado, sem saída e com código 0; comparação com o início da atualização
  confirmou os 68 demais arquivos versionados ou não ignorados intactos,
  além de HEAD e diff do índice inalterados. Testes operacionais e
  automatizados não reexecutados.
- Problema informado na validação: 1 warning de depreciação Starlette/AnyIO;
  nenhuma falha na suíte.
- Pendências: requisitos institucionais e trabalhos futuros listados acima;
  não permanecem pendentes build, pytest, bootstrap, login, CSRF, cookies,
  Range ou validação operacional no ambiente local confirmado.
- Próximo passo recomendado: revisão do diff documental pelo operador e
  preparação dos requisitos institucionais e da validação de backup/restauração,
  sem iniciar uma nova etapa nesta atualização.

Alterações preexistentes de implementação no working tree preservadas.
Nenhuma alteração funcional, de código Python, testes, Dockerfile,
compose.yaml, `.env`, credenciais ou registros do banco nesta atualização.
Nenhuma mudança operacional no servidor ou início da próxima etapa.
Nenhum `git add`, `git commit` ou `git push` executado.
