# AGENTS.md

## Projeto

Digital Signage

Sistema leve e autônomo de sinalização digital para gerenciamento centralizado
de conteúdo exibido em TVs através de TV Boxes.

## Diretório oficial

/home/administrador/digital-signage

Este é o diretório raiz oficial do projeto no servidor de produção/desenvolvimento.

Não criar cópias alternativas em /opt, /srv, /root, /tmp ou outros diretórios
sem autorização explícita.

---

## Ambiente

Servidor atual:

- IP: 10.4.254.202
- usuário operacional: administrador
- o servidor hospeda outras aplicações
- alterações devem evitar impacto em aplicações externas ao projeto

A aplicação deverá ser executada através de Docker e Docker Compose.

---

## Regra fundamental

Antes de realizar qualquer alteração no projeto:

1. confirmar o diretório atual com `pwd`;
2. ler `AGENTS.md`;
3. ler `README.md`;
4. ler `docs/STATUS.md`;
5. ler `docs/ARCHITECTURE.md`;
6. executar `git status`;
7. inspecionar os arquivos envolvidos antes de modificá-los.

Nunca presumir o estado atual da aplicação.

---

## Princípios do projeto

### 1. Docker-first

Dependências da aplicação devem ficar dentro dos containers sempre que possível.

Não instalar bibliotecas Python, Node.js ou componentes da aplicação diretamente
no sistema operacional do servidor sem necessidade justificada.

### 2. Documentation-first

Mudanças arquiteturais, operacionais ou estruturais devem ser refletidas na
documentação correspondente.

### 3. Git-first

Toda mudança relevante deve ser versionável.

Evitar alterações grandes sem checkpoints claros.

### 4. Inspect before change

Antes de modificar:

- arquivos;
- portas;
- containers;
- volumes;
- redes Docker;
- serviços;
- permissões;

verificar primeiro o estado atual.

### 5. Small steps

Implementar funcionalidades em etapas pequenas, testáveis e reversíveis.

### 6. No secrets

Nunca adicionar ao Git:

- senhas;
- tokens;
- chaves privadas;
- certificados privados;
- arquivos `.env`;
- credenciais de banco;
- credenciais do GitHub.

Usar `.env.example` somente com valores de exemplo.

### 7. Proteção do servidor

O servidor hospeda outras aplicações.

Não:

- remover containers de outros projetos;
- modificar redes Docker externas;
- alterar firewall sem autorização;
- alterar SSH;
- alterar configuração de rede;
- remover pacotes;
- alterar serviços externos ao projeto;
- executar comandos destrutivos indiscriminadamente.

### 8. Docker safety

Não utilizar, salvo decisão arquitetural documentada:

- `privileged: true`;
- `network_mode: host`;
- montagem de `/var/run/docker.sock`;
- montagem ampla de diretórios do host;
- containers executando como root sem necessidade.

Nunca executar automaticamente:

`docker compose down -v`

porque este comando pode remover volumes e dados persistentes.

### 9. Persistência

Banco de dados e arquivos de mídia não devem depender da camada gravável
temporária de um container.

Dados persistentes devem permanecer em diretórios ou volumes explicitamente
definidos.

### 10. Testes

Após uma alteração:

1. executar os testes existentes;
2. validar a funcionalidade alterada;
3. verificar logs;
4. verificar `git diff`;
5. atualizar a documentação quando necessário.

---

## Fonte da verdade

A fonte da verdade do projeto é o conteúdo versionado neste repositório.

Em especial:

- `AGENTS.md` — regras para agentes e desenvolvimento;
- `README.md` — visão geral;
- `docs/ARCHITECTURE.md` — arquitetura;
- `docs/STATUS.md` — estado real do projeto;
- `docs/ROADMAP.md` — próximos passos;
- `docs/adr/` — decisões arquiteturais.

Não assumir que uma funcionalidade existe somente porque aparece no roadmap.

O arquivo `docs/STATUS.md` define o que está efetivamente implementado.

---

## Ao concluir uma etapa

Sempre registrar:

1. arquivos criados;
2. arquivos alterados;
3. decisões tomadas;
4. testes executados;
5. resultado dos testes;
6. problemas encontrados;
7. pendências;
8. próximo passo recomendado.

Atualizar `docs/STATUS.md`.

---

## Git

Branch principal:

`main`

Não executar push forçado na branch principal.

Não reescrever histórico compartilhado sem autorização.

Antes de commit:

`git status`

`git diff`

---

## Objetivo atual

Estamos construindo inicialmente um MVP.

O objetivo do MVP é permitir que:

1. um administrador envie conteúdo pelo navegador;
2. o servidor gerencie esse conteúdo;
3. uma TV Box consulte o servidor;
4. a TV Box exiba o conteúdo em uma TV através de Chromium em modo kiosk.

Não implementar funcionalidades avançadas antes que o MVP básico esteja
funcionando.
