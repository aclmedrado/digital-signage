# ETAPA 003 — Persistência SQLite e cadastro de telas

## Contexto

Estamos desenvolvendo o projeto **Digital Signage**, um sistema leve e aberto de sinalização digital para gerenciamento centralizado de conteúdo exibido em TVs através de TV Boxes reaproveitadas.

Diretório oficial:

`/home/administrador/digital-signage`

Repositório:

`aclmedrado/digital-signage`

Branch principal:

`main`

Servidor atual:

- hostname: `utilities`;
- IP: `10.4.254.202`;
- Ubuntu 26.04.1 LTS;
- Docker Engine 29.8.1;
- Docker Compose 5.5.1.

A ETAPA 002 está concluída e validada.

Estado atual:

- FastAPI funcional;
- aplicação containerizada;
- execução como usuário não-root;
- Docker Compose funcional;
- endpoint `/`;
- endpoint `/health`;
- healthcheck Docker;
- testes automatizados;
- container `digital-signage-app` em estado healthy;
- serviço acessível atualmente em `10.4.254.202:8080`.

---

# Instruções obrigatórias antes de qualquer alteração

Antes de modificar qualquer arquivo:

1. execute `pwd`;
2. confirme que está em `/home/administrador/digital-signage`;
3. leia integralmente `AGENTS.md`;
4. leia `README.md`;
5. leia `docs/STATUS.md`;
6. leia `docs/ARCHITECTURE.md`;
7. leia `docs/adr/0001-docker.md`;
8. leia `docs/adr/0002-fastapi.md`;
9. leia `docs/adr/0003-sqlite.md`;
10. execute `git status`;
11. confirme que a working tree está limpa;
12. inspecione os arquivos atuais antes de modificá-los.

Não presuma a arquitetura.

O conteúdo versionado no repositório é a fonte da verdade.

Se houver divergência entre este prompt e o estado real do projeto, interrompa a implementação e reporte a divergência.

---

# Objetivo desta etapa

Introduzir persistência utilizando SQLite e implementar o primeiro conceito de domínio do Digital Signage:

**Screen**, representando uma tela/TV gerenciada pelo sistema.

Ao final desta etapa deverá ser possível:

1. criar uma tela por API;
2. listar telas;
3. consultar uma tela individual;
4. atualizar uma tela;
5. ativar ou desativar uma tela;
6. manter os dados após reinicialização ou reconstrução do container.

---

# Fora do escopo

NÃO implementar nesta etapa:

- interface administrativa HTML;
- autenticação;
- usuários;
- upload de imagens;
- vídeos;
- playlists;
- conteúdo;
- player;
- Chromium kiosk;
- heartbeat;
- status online/offline;
- WebSocket;
- agendamentos;
- grupos de telas;
- Caddy;
- Nginx;
- PostgreSQL;
- Redis;
- Alembic;
- migrations complexas.

Não implementar funcionalidades futuras antecipadamente.

---

# Stack desta etapa

Utilizar:

- Python;
- FastAPI;
- SQLAlchemy 2.x;
- SQLite;
- Pydantic já utilizado pelo FastAPI;
- pytest;
- httpx.

Não utilizar SQLModel.

Não utilizar ORM adicional.

Não introduzir Alembic nesta etapa.

---

# Dependências

Adicionar somente as dependências necessárias.

Adicionar SQLAlchemy com versão fixada ou adequadamente restrita.

Preservar as dependências existentes.

Não instalar dependências Python no host.

As dependências devem continuar sendo instaladas somente dentro da imagem Docker.

---

# Configuração do banco

Adicionar variável de ambiente:

`DATABASE_URL`

Valor padrão/documentado:

`sqlite:////app/data/signage.db`

Atualizar `.env.example`.

A configuração real continuará sendo feita através do arquivo `.env`, que não é versionado.

Não colocar endereço IP ou caminhos específicos do servidor diretamente no código Python quando puderem ser configuráveis.

---

# Persistência Docker

O banco deverá sobreviver a:

- `docker compose restart`;
- recriação do container;
- rebuild da imagem;
- `docker compose down` seguido de `docker compose up`.

Não utilizar a camada gravável efêmera do container como armazenamento definitivo.

Utilizar persistência Docker apropriada.

## Atenção a permissões

A aplicação continua devendo executar como usuário não-root.

Não resolver problemas de permissão com:

- `chmod 777`;
- container privilegiado;
- execução permanente como root.

Se a estratégia atual de bind mount em `./data` gerar incompatibilidade com o usuário não-root, escolha uma solução segura e documentada.

Preferir simplicidade e portabilidade.

Explique a decisão tomada.

Não alterar permissões de diretórios externos ao projeto.

---

# Estrutura de código

Organizar a persistência sem criar arquitetura excessivamente complexa.

Estrutura sugerida:

```text
app/
├── __init__.py
├── main.py
├── config.py
├── database.py
├── models.py
├── schemas.py
└── routes/
    ├── __init__.py
    └── screens.py
```

Pode adaptar essa estrutura caso o estado atual do projeto justifique.

Evite criar:

- repository pattern;
- service layer;
- dependency injection framework;
- abstrações genéricas;
- interfaces desnecessárias.

Nesta fase queremos código simples e legível.

---

# Modelo Screen

Criar entidade persistente representando uma tela.

Campos mínimos:

## id

Tipo:

inteiro

Características:

- chave primária;
- gerado automaticamente.

## name

Tipo:

string

Obrigatório.

Exemplo:

`TV Recepção`

## slug

Tipo:

string

Obrigatório.

Exemplo:

`recepcao`

Deve ser único.

Será utilizado futuramente para identificar a URL do player.

Exemplo futuro:

`/player/recepcao`

O slug deverá possuir validação básica.

Aceitar somente caracteres adequados para URL, preferencialmente:

- letras minúsculas;
- números;
- hífen.

Não gerar automaticamente nesta etapa.

O cliente deverá fornecê-lo explicitamente.

## location

Tipo:

string

Obrigatório.

Exemplo:

`Recepção`

## active

Tipo:

boolean

Valor padrão:

`true`

Representa se a tela está habilitada administrativamente.

Não representa estado online/offline.

## created_at

Data/hora de criação.

Gerada pelo servidor.

## updated_at

Data/hora da última modificação.

Gerada e atualizada pelo servidor.

Utilizar timestamps coerentes.

Preferir UTC internamente.

---

# API

Todas as rotas desta funcionalidade devem utilizar prefixo:

`/api/screens`

---

# Endpoint 1 — Criar tela

Método:

`POST /api/screens`

Exemplo de entrada:

```json
{
  "name": "TV Recepção",
  "slug": "recepcao",
  "location": "Recepção"
}
```

Resposta esperada:

HTTP `201 Created`

Exemplo conceitual:

```json
{
  "id": 1,
  "name": "TV Recepção",
  "slug": "recepcao",
  "location": "Recepção",
  "active": true,
  "created_at": "...",
  "updated_at": "..."
}
```

---

# Endpoint 2 — Listar telas

Método:

`GET /api/screens`

Resposta:

HTTP `200`

Exemplo:

```json
[
  {
    "id": 1,
    "name": "TV Recepção",
    "slug": "recepcao",
    "location": "Recepção",
    "active": true,
    "created_at": "...",
    "updated_at": "..."
  }
]
```

Ordenar de maneira determinística.

Preferencialmente por `id`.

---

# Endpoint 3 — Consultar tela

Método:

`GET /api/screens/{screen_id}`

Tela existente:

HTTP `200`.

Tela inexistente:

HTTP `404`.

---

# Endpoint 4 — Atualizar tela

Método:

`PATCH /api/screens/{screen_id}`

Permitir atualização parcial de:

- name;
- slug;
- location;
- active.

Não permitir alterar:

- id;
- created_at.

Atualizar `updated_at`.

Tela inexistente:

HTTP `404`.

---

# Duplicidade de slug

O campo `slug` deve possuir restrição UNIQUE no banco.

Tentativa de criar ou atualizar uma tela utilizando slug já existente deverá produzir resposta HTTP adequada.

Preferência:

HTTP `409 Conflict`.

Não retornar traceback SQL para o cliente.

---

# Validação de slug

Aceitar somente formato equivalente a:

`^[a-z0-9]+(?:-[a-z0-9]+)*$`

Exemplos válidos:

- `recepcao`
- `biblioteca`
- `bloco-600`
- `tv-01`

Exemplos inválidos:

- `TV Recepção`
- `recepção`
- `tv_01`
- `tv 01`
- `-recepcao`
- `recepcao-`

Erros de validação devem utilizar o comportamento adequado do FastAPI/Pydantic.

---

# Banco e inicialização

Criar a estrutura necessária do banco automaticamente durante a inicialização da aplicação nesta etapa.

Não adicionar Alembic.

A inicialização deve ser idempotente.

Reiniciar a aplicação não deve apagar dados existentes.

Nunca recriar o banco destrutivamente.

---

# SQLite e FastAPI

Configurar corretamente o SQLite para uso com SQLAlchemy e FastAPI.

Considere especialmente o uso de:

`check_same_thread=False`

quando necessário para a configuração utilizada.

Gerenciar sessões corretamente.

Sessões devem ser fechadas após cada requisição.

Não utilizar conexão global aberta indefinidamente.

---

# Endpoints existentes

Preservar sem mudança de comportamento:

`GET /`

Resposta:

```json
{
  "name": "Digital Signage",
  "status": "running"
}
```

Preservar:

`GET /health`

Resposta:

```json
{
  "status": "ok"
}
```

Não fazer o `/health` depender de consultas complexas ao banco nesta etapa.

---

# Testes

Preservar os testes existentes.

Adicionar testes para a nova funcionalidade.

Os testes não devem modificar o banco de produção.

Utilizar banco SQLite isolado para testes.

Pode ser:

- SQLite em memória;
- arquivo temporário.

Escolher a abordagem mais simples e confiável.

---

# Testes mínimos obrigatórios

## Teste 1

Criar tela com sucesso.

Verificar:

- HTTP 201;
- dados retornados;
- active = true.

## Teste 2

Listar telas.

## Teste 3

Consultar tela existente.

## Teste 4

Consultar tela inexistente.

Esperado:

HTTP 404.

## Teste 5

Atualizar parcialmente uma tela.

## Teste 6

Desativar uma tela.

## Teste 7

Slug duplicado.

Esperado:

HTTP 409.

## Teste 8

Slug inválido.

Esperar resposta de validação.

## Teste 9

Persistência lógica.

Criar registro, realizar nova consulta e confirmar que permanece disponível no banco de teste.

Preservar também:

- teste de `/`;
- teste de `/health`.

---

# Testes no container

Os testes deverão ser executáveis com:

```bash
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
```

Não tornar `/app` gravável somente para permitir cache do pytest.

---

# Validação Docker

Antes de modificar ou subir containers:

1. inspecionar o estado atual;
2. executar:

```bash
sudo docker compose ps
```

O Codex provavelmente não terá acesso interativo ao `sudo`.

Se ocorrer erro de autenticação de terminal:

- não tentar contornar;
- não modificar grupos;
- não alterar sudoers;
- registrar os comandos que o operador deverá executar.

---

# Validação após implementação

Orientar o operador a executar:

```bash
sudo docker compose config
```

```bash
sudo docker compose build
```

```bash
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
```

```bash
sudo docker compose up -d
```

```bash
sudo docker compose ps
```

---

# Teste manual da API

Depois da implantação:

## Criar

```bash
curl -i \
  -X POST \
  http://10.4.254.202:8080/api/screens \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TV Recepção",
    "slug": "recepcao",
    "location": "Recepção"
  }'
```

## Listar

```bash
curl -i http://10.4.254.202:8080/api/screens
```

## Consultar

```bash
curl -i http://10.4.254.202:8080/api/screens/1
```

Não assumir que o ID será obrigatoriamente 1 se já existirem dados.

---

# Teste de persistência real

Após criar uma tela de teste:

1. consultar a tela;
2. executar:

```bash
sudo docker compose restart signage-app
```

3. aguardar o container ficar healthy;
4. consultar novamente a tela;
5. confirmar que o registro permaneceu.

A persistência deve também sobreviver à recriação normal do container.

Não executar `docker compose down -v`.

---

# Segurança

Não:

- alterar firewall;
- alterar SSH;
- alterar UFW;
- alterar interfaces de rede;
- adicionar usuário ao grupo docker;
- modificar sudoers;
- modificar Docker daemon global;
- remover containers externos;
- remover imagens externas;
- remover volumes externos;
- executar `docker system prune`;
- executar `docker volume prune`;
- executar `docker network prune`;
- executar `docker compose down -v`;
- instalar banco no host;
- instalar dependências Python no host.

---

# Documentação

Atualizar somente o necessário.

## README.md

Documentar resumidamente:

- persistência SQLite;
- configuração DATABASE_URL;
- API de telas.

## docs/STATUS.md

Registrar precisamente o que foi implementado.

Não marcar validações Docker como concluídas antes de o operador realizá-las.

## docs/ARCHITECTURE.md

Adicionar o banco SQLite e a entidade Screen à arquitetura real.

## docs/DEPLOYMENT.md

Documentar persistência e variável DATABASE_URL.

## docs/OPERATIONS.md

Adicionar somente operações realmente úteis relacionadas ao banco.

Não sugerir edição manual do SQLite como operação cotidiana.

---

# ADR

`docs/adr/0003-sqlite.md` já deverá conter a decisão de adoção do SQLite.

Leia o ADR antes da implementação.

A implementação deve permanecer coerente com ele.

Não alterar o status do ADR sem necessidade.

---

# STATUS da etapa

Ao terminar a implementação em arquivos, mas antes da validação manual do operador, diferenciar claramente:

- implementado;
- testado automaticamente;
- validado em Docker;
- pendente de validação operacional.

Não declarar sucesso de uma validação que não foi realmente executada.

---

# Git

Não executar:

```bash
git commit
```

Não executar:

```bash
git push
```

Não executar:

```bash
git add .
```

O operador fará auditoria antes.

Não modificar histórico Git.

---

# Controle de escopo

Se durante a implementação surgir uma necessidade que implique:

- nova tecnologia;
- novo container;
- mudança relevante de arquitetura;
- mudança de banco;
- execução como root;
- mudança global no servidor;

pare e reporte.

Não tome decisão estrutural silenciosamente.

---

# Relatório final obrigatório

Ao terminar, apresente:

## 1. Estado inicial

Resuma o estado encontrado.

## 2. Arquivos criados

Liste todos.

## 3. Arquivos modificados

Liste todos.

## 4. Modelo Screen

Descreva campos e restrições efetivamente implementados.

## 5. Banco

Informe:

- biblioteca utilizada;
- localização lógica;
- mecanismo de persistência Docker;
- DATABASE_URL;
- estratégia de inicialização.

## 6. API

Liste todos os endpoints existentes e respectivos métodos.

## 7. Testes

Informe:

- quantidade de testes;
- resultados efetivamente executados;
- validações pendentes.

## 8. Docker

Informe qualquer alteração em:

- Dockerfile;
- compose.yaml;
- volumes;
- environment;
- usuário do container.

## 9. Segurança

Informe explicitamente se houve alterações fora de:

`/home/administrador/digital-signage`

A resposta esperada é:

`não`

Caso contrário, explique.

## 10. Git

Apresente:

```bash
git status --short
```

e:

```bash
git diff --stat
```

Também executar:

```bash
git diff --check
```

## 11. Pendências

Liste problemas ou validações que dependam do operador.

## 12. Próxima etapa

Sugira somente.

Não implemente a próxima etapa.