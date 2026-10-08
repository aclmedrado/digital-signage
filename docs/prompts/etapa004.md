# ETAPA 004 — Interface administrativa de telas

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
- Docker;
- Docker Compose.

As ETAPAS 001, 002 e 003 estão concluídas.

Estado funcional atual:

- FastAPI containerizado;
- aplicação executando como usuário não-root;
- SQLite persistente;
- SQLAlchemy;
- volume Docker persistente;
- entidade `Screen`;
- API de telas;
- testes automatizados;
- healthcheck;
- persistência validada operacionalmente.

A aplicação está atualmente acessível em:

`http://10.4.254.202:8080`

---

# Instruções obrigatórias antes de qualquer alteração

Antes de modificar qualquer arquivo:

1. execute `pwd`;
2. confirme que está em `/home/administrador/digital-signage`;
3. leia integralmente `AGENTS.md`;
4. leia `README.md`;
5. leia `docs/STATUS.md`;
6. leia `docs/ARCHITECTURE.md`;
7. leia os ADRs existentes;
8. leia especialmente `docs/adr/0004-server-rendered-admin.md`;
9. execute `git status`;
10. confirme que a working tree está limpa;
11. inspecione o código atual relacionado a:
    - aplicação FastAPI;
    - banco;
    - modelos;
    - schemas;
    - rotas de screens;
    - testes;
    - templates e static existentes.

Não presuma a estrutura atual.

O repositório é a fonte da verdade.

Se houver divergência relevante entre este prompt e o estado real, pare e reporte.

---

# Objetivo

Implementar uma interface administrativa web mínima para gerenciamento de telas.

Ao final desta etapa, um usuário deverá conseguir utilizar o navegador para:

1. visualizar telas cadastradas;
2. cadastrar uma nova tela;
3. editar uma tela;
4. ativar uma tela;
5. desativar uma tela.

Não será mais necessário utilizar `curl` para essas operações básicas.

---

# Fora do escopo

NÃO implementar nesta etapa:

- autenticação;
- autorização;
- usuários;
- exclusão de telas;
- upload de imagens;
- vídeos;
- conteúdos;
- playlists;
- player;
- TV Box;
- Chromium kiosk;
- heartbeat;
- online/offline;
- WebSocket;
- grupos;
- agendamento;
- Caddy;
- Nginx;
- JavaScript framework;
- Alembic;
- PostgreSQL.

Não iniciar funcionalidades pertencentes a etapas futuras.

---

# Tecnologia da interface

Utilizar:

- FastAPI;
- Jinja2;
- HTML;
- CSS;
- formulários HTML tradicionais.

Adicionar somente as dependências realmente necessárias.

É aceitável adicionar:

- Jinja2;
- `python-multipart`, caso necessário para processamento seguro dos formulários pelo FastAPI.

Não adicionar Node.js.

Não criar frontend separado.

---

# Estrutura sugerida

Adaptar à estrutura real existente.

Estrutura conceitual:

```text
app/
├── main.py
├── routes/
│   ├── screens.py
│   └── admin/
│       ├── __init__.py
│       └── screens.py
├── templates/
│   ├── base.html
│   └── admin/
│       └── screens/
│           ├── list.html
│           └── form.html
└── static/
    └── admin.css
```

Pode utilizar outra organização simples se houver razão técnica clara.

Não criar estruturas excessivas.

---

# Princípio de reutilização

A interface administrativa e a API trabalham sobre o mesmo domínio `Screen`.

Não realizar requisições HTTP da aplicação para sua própria API.

Exemplo de prática proibida:

```python
requests.post("http://localhost:8000/api/screens", ...)
```

A interface deve acessar a mesma persistência e regras utilizadas pela API.

Evitar duplicação significativa.

Se for necessário extrair pequenas funções compartilhadas para tratar:

- busca;
- criação;
- atualização;
- conflito de slug;

isso é aceitável.

Não introduzir:

- repository pattern;
- service framework;
- dependency injection framework;
- arquitetura hexagonal;
- CQRS;

somente para esta etapa.

---

# Rotas administrativas

Utilizar prefixo:

`/admin`

---

## GET /admin

Redirecionar para:

`/admin/screens`

Preferir redirect HTTP apropriado.

---

## GET /admin/screens

Exibir lista das telas cadastradas.

Para cada tela apresentar pelo menos:

- nome;
- slug;
- localização;
- estado ativa/inativa;
- ação Editar;
- ação Ativar ou Desativar.

Ordenar telas de maneira determinística.

Preferencialmente por `id`.

Disponibilizar botão/link:

`Nova tela`

---

## GET /admin/screens/new

Exibir formulário para criação de tela.

Campos:

- name;
- slug;
- location.

O estado inicial será ativo.

Não exigir campo active no formulário de criação.

---

## POST /admin/screens

Criar tela.

Em caso de sucesso:

1. persistir;
2. redirecionar para `/admin/screens`.

Preferir padrão:

POST → Redirect → GET.

Não retornar JSON para o usuário da interface administrativa.

---

## GET /admin/screens/{screen_id}/edit

Exibir formulário preenchido com os dados atuais.

Campos editáveis:

- name;
- slug;
- location.

A ativação/desativação deverá permanecer como ação separada.

Tela inexistente:

HTTP 404.

---

## POST /admin/screens/{screen_id}/edit

Atualizar:

- name;
- slug;
- location.

Em sucesso:

redirecionar para `/admin/screens`.

Atualizar `updated_at`.

Tela inexistente:

HTTP 404.

---

# Ativação e desativação

Implementar ação via POST.

Pode utilizar rota semelhante a:

`POST /admin/screens/{screen_id}/toggle`

ou rotas explícitas:

`POST /admin/screens/{screen_id}/activate`

`POST /admin/screens/{screen_id}/deactivate`

Escolha a solução mais simples e clara.

Não utilizar GET para modificar estado.

Após a alteração:

redirecionar para `/admin/screens`.

---

# Não implementar DELETE

Nesta etapa não deverá existir botão ou endpoint administrativo para excluir telas.

Uma tela pode ser desativada.

Isso evita remoção acidental e mantém o escopo reduzido.

---

# Formulários

Os formulários deverão:

- possuir labels;
- manter organização visual simples;
- usar tipos HTML apropriados;
- utilizar atributos de validação quando útil;
- preservar valores preenchidos quando ocorrer erro;
- exibir mensagens de erro compreensíveis.

O campo slug deve respeitar a mesma regra da API:

`^[a-z0-9]+(?:-[a-z0-9]+)*$`

Não criar regra divergente da API.

---

# Slug duplicado

Se o usuário tentar criar ou editar uma tela com slug já existente:

- não exibir traceback;
- permanecer ou retornar ao formulário;
- apresentar mensagem clara, por exemplo:

`Já existe uma tela com esse slug.`

Não criar registro duplicado.

---

# Validação

Erros de formulário devem ser apresentados em HTML.

Evitar devolver resposta JSON do FastAPI para erros normais do formulário administrativo.

A interface deve ser compreensível para usuário não técnico.

---

# Aparência

Criar uma aparência institucional simples e limpa.

Não tentar reproduzir identidade visual complexa nesta etapa.

Requisitos:

- conteúdo centralizado em largura confortável;
- cabeçalho simples com nome `Digital Signage`;
- navegação mínima;
- tabela ou cards para telas;
- diferenciação visual entre ativa e inativa;
- formulários legíveis;
- botões claros;
- bom espaçamento;
- layout utilizável em desktop e tablet;
- responsividade básica.

Não utilizar CSS externo ou CDN.

Todo CSS deverá estar no projeto.

---

# JavaScript

JavaScript não deve ser necessário para as funcionalidades desta etapa.

Se nenhuma necessidade concreta surgir, não criar arquivos JavaScript.

---

# StaticFiles

Se necessário, montar diretório estático usando FastAPI `StaticFiles`.

Não alterar `/health`.

O healthcheck deve continuar independente da interface administrativa.

---

# Templates

Utilizar Jinja2.

Criar template base para evitar repetição desnecessária.

Exemplo conceitual:

```text
base.html
   |
   +-- admin/screens/list.html
   |
   +-- admin/screens/form.html
```

Não duplicar cabeçalho, estrutura HTML e CSS entre páginas.

---

# Segurança

A interface administrativa ainda NÃO possui autenticação.

Isso deve ser documentado claramente.

Enquanto não houver autenticação:

- considerar a interface restrita à rede interna;
- não afirmar que ela é segura para exposição pública;
- não expor deliberadamente a aplicação à Internet.

Não implementar autenticação improvisada nesta etapa.

Não alterar:

- firewall;
- UFW;
- SSH;
- sudoers;
- grupos;
- Docker daemon;
- rede do host.

---

# API existente

Preservar integralmente:

- GET `/`;
- GET `/health`;
- POST `/api/screens`;
- GET `/api/screens`;
- GET `/api/screens/{screen_id}`;
- PATCH `/api/screens/{screen_id}`.

Nenhuma regressão é aceitável.

---

# Banco

Preservar:

- SQLite;
- DATABASE_URL;
- volume `signage-data`;
- dados existentes;
- `TV Piloto`, caso ainda esteja presente no banco real.

Não apagar nem recriar o banco.

Não executar migração destrutiva.

Não implementar Alembic.

---

# Docker

Manter um único serviço.

Não criar novo container.

Atualizar a tag da imagem para:

`digital-signage:etapa004`

somente se essa for a convenção atual adotada no projeto.

Inspecione primeiro.

Não modificar persistência existente.

---

# Testes

Todos os testes existentes devem continuar passando.

Adicionar testes para interface administrativa.

Os testes administrativos devem utilizar banco isolado e não alterar o banco de produção.

---

# Testes mínimos obrigatórios

## 1. Admin redirect

`GET /admin`

deve redirecionar para:

`/admin/screens`.

---

## 2. Lista vazia

`GET /admin/screens`

deve responder HTTP 200 mesmo sem telas.

---

## 3. Listagem

Com tela cadastrada:

`GET /admin/screens`

deve incluir no HTML:

- nome;
- slug;
- localização;
- estado.

---

## 4. Formulário de criação

`GET /admin/screens/new`

deve responder HTTP 200.

---

## 5. Criação

`POST /admin/screens`

com dados válidos deve:

- persistir tela;
- responder com redirect;
- permitir localizar a tela após o redirect.

---

## 6. Slug duplicado

Criação com slug existente deve:

- não gerar registro duplicado;
- apresentar mensagem HTML adequada.

---

## 7. Formulário de edição

`GET /admin/screens/{id}/edit`

deve apresentar dados atuais.

---

## 8. Edição

POST de edição válido deve:

- alterar dados;
- atualizar `updated_at`;
- redirecionar.

---

## 9. Edição inexistente

Tela inexistente deve retornar HTTP 404.

---

## 10. Ativação/desativação

A ação administrativa deve alterar corretamente `active`.

---

## 11. Método seguro

A alteração de `active` não deve ocorrer através de GET.

---

## 12. Regressão da API

Os testes existentes da API e dos endpoints `/` e `/health` devem continuar passando.

---

# Execução dos testes

Utilizar:

```bash
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
```

Se o Codex não possuir acesso ao sudo interativo:

- não contornar;
- não alterar permissões;
- registrar o comando para execução pelo operador.

---

# Validação operacional

Após implementação e testes:

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

```bash
sudo docker compose logs --tail=100 signage-app
```

---

# Validação manual pelo navegador

Após implantação, deverão ser acessíveis:

`http://10.4.254.202:8080/admin`

e:

`http://10.4.254.202:8080/admin/screens`

O operador deverá conseguir:

1. visualizar `TV Piloto`, caso exista;
2. cadastrar uma nova tela;
3. editar essa tela;
4. desativá-la;
5. reativá-la;
6. atualizar a página sem reenvio indevido do formulário.

---

# Teste por curl opcional

A interface é destinada ao navegador, mas respostas podem ser verificadas com:

```bash
curl -I http://10.4.254.202:8080/admin
```

e:

```bash
curl -i http://10.4.254.202:8080/admin/screens
```

Não é necessário validar visualmente CSS através de curl.

---

# Documentação

Atualizar somente o necessário.

## README.md

Registrar que existe painel administrativo inicial.

## docs/STATUS.md

Registrar precisamente:

- interface implementada;
- funcionalidades disponíveis;
- testes executados;
- validações pendentes ou concluídas.

## docs/ARCHITECTURE.md

Adicionar interface server-rendered à arquitetura.

## docs/DEPLOYMENT.md

Alterar somente se houver nova necessidade real.

## docs/OPERATIONS.md

Adicionar URL administrativa e observação sobre ausência atual de autenticação.

Não documentar funcionalidade inexistente.

---

# ADR

Ler:

`docs/adr/0004-server-rendered-admin.md`

A implementação deve ser coerente com essa decisão.

---

# Controle de escopo

Se surgir necessidade de:

- frontend separado;
- Node.js;
- novo container;
- autenticação;
- tecnologia JavaScript;
- proxy reverso;
- nova infraestrutura;
- alteração global do servidor;

pare e reporte.

Não decida silenciosamente.

---

# Git

Não executar:

`git add`

Não executar:

`git commit`

Não executar:

`git push`

O operador fará a auditoria e versionamento.

Não modificar o histórico Git.

---

# Relatório final obrigatório

Ao terminar, apresente:

## 1. Estado inicial

Resuma o estado encontrado.

## 2. Arquivos criados

Liste todos.

## 3. Arquivos modificados

Liste todos.

## 4. Dependências

Liste dependências adicionadas e motivo.

## 5. Rotas administrativas

Liste método e URL.

## 6. Interface

Descreva:

- páginas;
- formulários;
- ações disponíveis;
- tratamento de erros;
- comportamento POST → Redirect → GET.

## 7. Reutilização

Explique como as regras existentes da entidade Screen foram reutilizadas sem chamada HTTP interna.

## 8. Testes

Informe:

- total de testes;
- resultado efetivamente executado;
- validações pendentes.

## 9. Docker

Informe alterações realizadas.

## 10. Segurança

Confirme:

- autenticação ainda não implementada;
- interface destinada somente ao ambiente interno nesta fase;
- nenhuma alteração global do servidor.

## 11. Git

Apresente:

`git status --short`

`git diff --stat`

`git diff --check`

## 12. Pendências

Liste somente pendências reais.

## 13. Próxima etapa sugerida

Sugira somente.

Não implemente.