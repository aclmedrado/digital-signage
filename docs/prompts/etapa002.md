# ETAPA 002 — Docker + FastAPI mínimo

## Contexto

Estamos desenvolvendo o projeto **Digital Signage**, um sistema leve e aberto de sinalização digital para gerenciamento centralizado de conteúdo exibido em TVs através de TV Boxes reaproveitadas.

O projeto está hospedado em:

`/home/administrador/digital-signage`

Repositório GitHub:

`aclmedrado/digital-signage`

Branch principal:

`main`

Servidor atual:

- hostname: `utilities`
- IP principal: `10.4.254.202`
- sistema operacional: Ubuntu 26.04.1 LTS
- arquitetura: x86_64
- Docker Engine: 29.8.1
- Docker Compose: 5.5.1
- containerd: 2.3.6

O servidor hospeda ou poderá hospedar outras aplicações.

Portanto, qualquer alteração deve respeitar rigorosamente o isolamento deste projeto.

---

# Instrução obrigatória inicial

Antes de modificar qualquer arquivo:

1. execute `pwd`;
2. confirme que está em `/home/administrador/digital-signage`;
3. leia integralmente `AGENTS.md`;
4. leia `README.md`;
5. leia `docs/STATUS.md`;
6. leia `docs/ARCHITECTURE.md`;
7. leia `docs/adr/0001-docker.md`;
8. execute `git status`;
9. inspecione a estrutura atual do projeto.

Não presuma conteúdo ou estado de arquivos.

Não continue se estiver fora do diretório oficial do projeto.

---

# Objetivo desta etapa

Criar a primeira aplicação funcional do Digital Signage utilizando:

- Python;
- FastAPI;
- Uvicorn;
- Docker;
- Docker Compose.

A aplicação desta etapa será deliberadamente mínima.

Ela deverá possuir somente:

- página inicial;
- endpoint de healthcheck;
- execução em container;
- healthcheck Docker;
- testes básicos.

NÃO implementar ainda:

- SQLite;
- banco de dados;
- autenticação;
- painel administrativo;
- upload;
- cadastro de TVs;
- player;
- vídeos;
- imagens;
- agendamentos;
- grupos;
- heartbeat;
- monitoramento.

Esses itens pertencem a etapas futuras.

---

# Arquivos esperados

A implementação deverá resultar, no mínimo, nos seguintes arquivos:

```text
app/
├── __init__.py
└── main.py

tests/
├── __init__.py
└── test_main.py

Dockerfile
compose.yaml
requirements.txt
.env.example
```

Pode criar arquivos adicionais somente quando houver justificativa técnica clara.

Evite abstrações prematuras.

---

# FastAPI

Criar uma aplicação FastAPI mínima.

## Endpoint `/`

Método:

`GET`

Resposta esperada:

```json
{
  "name": "Digital Signage",
  "status": "running"
}
```

Código HTTP:

`200`

---

## Endpoint `/health`

Método:

`GET`

Resposta esperada:

```json
{
  "status": "ok"
}
```

Código HTTP:

`200`

Este endpoint será utilizado pelo healthcheck do container.

---

# Dependências

Manter dependências mínimas.

Inicialmente são esperadas apenas dependências equivalentes a:

- fastapi;
- uvicorn;
- pytest;
- httpx.

Fixar ou restringir versões de maneira razoável para permitir builds reproduzíveis.

Não instalar dependências diretamente no Python do host.

---

# Dockerfile

Criar um Dockerfile simples, seguro e pequeno.

Requisitos:

1. utilizar imagem oficial Python adequada;
2. preferir variante slim;
3. definir diretório de trabalho;
4. copiar e instalar dependências de forma eficiente para aproveitar cache de build;
5. copiar somente o necessário;
6. executar a aplicação com Uvicorn;
7. expor internamente a porta `8000`;
8. executar a aplicação como usuário não-root.

Não utilizar:

- `privileged`;
- Docker socket;
- acesso desnecessário ao host;
- instalação de ferramentas sem necessidade.

Não incluir segredos na imagem.

---

# Docker Compose

Configurar o serviço com nome lógico:

`signage-app`

Utilizar apenas um serviço nesta etapa.

Não criar PostgreSQL, Redis, Nginx, Caddy ou outros serviços.

Configurar:

```text
container_name: digital-signage-app
```

ou justificar caso seja melhor não fixar `container_name`.

Definir:

```text
restart: unless-stopped
```

Publicar inicialmente a aplicação em:

`10.4.254.202:8080`

mapeada para:

`8000`

dentro do container.

Preferência:

```yaml
ports:
  - "10.4.254.202:8080:8000"
```

Não usar `network_mode: host`.

---

# Healthcheck Docker

Configurar healthcheck do container utilizando:

`GET /health`

O healthcheck deve verificar se a aplicação realmente está respondendo.

Evitar instalar ferramentas desnecessárias somente para realizar o healthcheck caso seja possível utilizar Python ou ferramenta já existente na imagem.

---

# Arquivo .env

O arquivo real `.env` NÃO deve ser criado ou versionado com dados sensíveis.

Atualizar `.env.example` somente se necessário.

Nenhum valor específico do servidor deve ficar codificado no código Python.

O IP `10.4.254.202` pertence à implantação atual e não à aplicação genérica.

---

# Testes

Criar testes automatizados para:

## Teste 1

`GET /`

Deve:

- retornar HTTP 200;
- retornar o nome Digital Signage;
- retornar status `running`.

## Teste 2

`GET /health`

Deve:

- retornar HTTP 200;
- retornar `{"status": "ok"}`.

Utilizar pytest.

Os testes devem poder ser executados de forma reproduzível.

---

# Testes com Docker

Depois da implementação, construir a imagem.

Antes de executar qualquer operação Docker que exija privilégios, informar claramente o comando necessário.

O usuário operacional não pertence deliberadamente ao grupo `docker`.

Portanto, comandos Docker serão executados com:

```bash
sudo docker ...
```

ou:

```bash
sudo docker compose ...
```

Não tentar alterar os grupos do usuário.

Não executar:

```bash
sudo usermod -aG docker administrador
```

Não modificar `/etc/docker/daemon.json`.

Não modificar configurações globais do Docker.

---

# Verificação de porta

Antes de subir o container, verificar se a porta `8080` está livre.

Pode utilizar:

```bash
ss -tulpn
```

Não interromper processos existentes para liberar portas.

Se `8080` estiver ocupada, pare e reporte o conflito.

---

# Segurança

O servidor é compartilhado.

Não:

- alterar firewall;
- ativar/desativar UFW;
- alterar SSH;
- alterar interfaces de rede;
- remover pacotes;
- remover containers externos;
- remover imagens externas;
- remover volumes externos;
- executar `docker system prune`;
- executar `docker volume prune`;
- executar `docker network prune`;
- executar `docker compose down -v`;
- alterar outros projetos em `/home/administrador`.

Toda operação deve permanecer dentro do escopo deste projeto.

---

# Documentação

Atualizar:

## `README.md`

Adicionar instruções mínimas para:

- build;
- inicialização;
- parada;
- logs;
- teste do endpoint;
- execução dos testes.

## `docs/STATUS.md`

Registrar:

- FastAPI implementado;
- Dockerfile implementado;
- Compose implementado;
- endpoints disponíveis;
- testes realizados;
- estado atual.

## `docs/ARCHITECTURE.md`

Atualizar apenas o necessário para refletir a aplicação containerizada.

## `docs/DEPLOYMENT.md`

Documentar os comandos básicos de implantação com Docker Compose.

## `docs/OPERATIONS.md`

Documentar:

```bash
sudo docker compose ps
sudo docker compose logs
sudo docker compose logs -f
sudo docker compose restart
sudo docker compose stop
sudo docker compose start
```

Não documentar comandos destrutivos como rotina operacional.

---

# ADR FastAPI

Preencher:

`docs/adr/0002-fastapi.md`

Formato esperado:

```markdown
# ADR 0002 - Uso de FastAPI

Status: Aceito

## Contexto

...

## Decisão

...

## Motivos

...

## Consequências

...
```

Registrar por que FastAPI foi escolhido para o backend inicial.

---

# Não alterar ADR SQLite

Não preencher nem marcar como aceito:

`docs/adr/0003-sqlite.md`

SQLite ainda será tratado em etapa posterior.

---

# Validação final

Ao concluir a implementação, executar ou orientar a execução de:

```bash
git status
```

```bash
git diff
```

Executar os testes Python.

Construir a imagem Docker.

Subir a aplicação.

Verificar:

```text
http://127.0.0.1:8080/
```

quando aplicável pelo binding configurado, ou diretamente:

```text
http://10.4.254.202:8080/
```

e:

```text
http://10.4.254.202:8080/health
```

Verificar também:

```bash
sudo docker compose ps
```

O container deverá apresentar estado saudável.

---

# Git

NÃO realizar:

```bash
git commit
```

NÃO realizar:

```bash
git push
```

Nesta etapa.

O usuário revisará as alterações antes do commit.

Não modificar histórico Git.

---

# Relatório final obrigatório

Ao terminar, apresente:

## 1. Estado inicial encontrado

Informe resumidamente o que existia antes das alterações.

## 2. Arquivos criados

Liste todos.

## 3. Arquivos modificados

Liste todos.

## 4. Implementação

Explique resumidamente o que foi implementado.

## 5. Docker

Informe:

- nome da imagem;
- nome do serviço;
- nome do container, se aplicável;
- portas;
- status;
- healthcheck.

## 6. Testes

Liste os testes executados e resultados.

## 7. Endpoints

Liste URLs disponíveis.

## 8. Segurança

Informe se houve qualquer alteração fora do diretório do projeto.

A resposta esperada é:

`não`

Caso contrário, explicar detalhadamente.

## 9. Git

Apresente:

```bash
git status
```

e resumo de:

```bash
git diff --stat
```

## 10. Pendências

Liste qualquer problema ou decisão necessária.

## 11. Próxima etapa sugerida

Não implementar.

Apenas sugerir.
