# ETAPA 006 — Autenticação, autorização e segurança administrativa

## 1. Contexto e objetivo

Projeto: **Digital Signage**  
Diretório: `/home/administrador/digital-signage`  
Repositório: `aclmedrado/digital-signage`  
Branch: `main`  
Servidor: `utilities` (`10.4.254.202`), Ubuntu, Docker Compose, FastAPI, SQLite, Jinja2.

As ETAPAS 001–005 estão concluídas, com a ETAPA 005 validada pelo operador: **149 testes aprovados**, upload e pré-visualização MP4/imagens, HTTP Range, persistência e preservação das telas. O commit da ETAPA 005 foi publicado; confirme o HEAD real, não presuma hash de commit.

**Objetivo:** proteger a administração de telas e mídias com login, sessões persistentes, controle de autorização, CSRF e bootstrap seguro do primeiro administrador. Manter a aplicação leve, server-rendered e com um único serviço.

**Alerta operacional:** a aplicação foi usada em `http://10.4.254.202:8080` sem autenticação. Não transmitir credenciais nesse HTTP da LAN. A validação real da nova autenticação exigirá HTTPS ou binding local com túnel SSH, escolhido e aplicado pelo operador antes do login.

## 2. Inspeção inicial obrigatória

Antes de qualquer alteração:

1. Confirme `pwd` e o diretório oficial.
2. Leia integralmente `AGENTS.md`, `README.md`, `docs/STATUS.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/DEPLOYMENT.md`, `docs/OPERATIONS.md`.
3. Leia todos os ADRs aplicáveis, principalmente `docs/adr/0006-authentication-authorization.md`.
4. Leia este prompt por completo.
5. Execute `git status --short`, `git log -3 --oneline`, confirme `main` e working tree limpa.
6. Inspecione todas as rotas, serviços, modelos, dependências, banco, templates, upload, FileResponse, middleware e testes existentes.
7. Inspecione Compose e `.env.example`; **não leia, divulgue nem modifique segredos de `.env` desnecessariamente**.
8. Se houver divergência relevante entre ADR, prompt e repositório, **pare e reporte**.

Não iniciar implementação com working tree suja. Não alterar a infraestrutura global.

## 3. Regras de escopo

Implementar somente autenticação, autorização, sessões, bootstrap e proteção CSRF em funcionalidades existentes. NÃO implementar:

- Caddy/HTTPS em produção, DNS, firewall, Nginx ou outro container;
- novo frontend, React, Vue, JS framework ou frontend separado;
- IFG ID, LDAP, OAuth, SSO, MFA, recuperação por e-mail;
- cadastro público, painel de múltiplos usuários ou redefinição de senha pelo navegador;
- JWT, Redis, PostgreSQL, Alembic;
- playlists, publicações, player, kiosk, API keys para TV Boxes;
- mudanças destrutivas no SQLite, exclusão de mídias ou alteração do formato de upload.

Nenhuma configuração global do host ou privilégios adicionais.

## 4. Modelos e persistência

Introduzir estruturas persistentes mínimas no SQLite para:

- `User`: `id`, `username` normalizado e único, `password_hash`, `role`, `active`, `created_at` e `updated_at` em UTC.
- `AuthSession`: vínculo a usuário, **hash do token** opaco, criação, última atividade, expiração absoluta e estado revogado/removido, mais metadados estritamente necessários.
- Desafio/pré-sessão para login CSRF: identificador imprevisível, hash de cookie/challenge, token CSRF vinculado e expiração curta. Não reaproveitar como sessão autenticada.
- Persistência mínima para limitação de tentativas de login, se necessária, com limpeza/expiração limitada.

Utilizar convenções existentes de SQLAlchemy/SQLite, `get_session` e inicialização idempotente. `create_all` pode criar tabelas novas, sem remover ou recriar `screens`, `media_assets` ou dados reais. Não introduzir migrações destrutivas nem Alembic.

## 5. Senhas e bootstrap do administrador

- Adicionar dependência mantida e com versão fixada para **Argon2id** (`pwdlib[argon2]` ou `argon2-cffi`). Seguir parâmetros no mínimo equivalentes aos recomendados pela OWASP; justificar escolha.
- Implementar verificação segura de senha e não gravar segredo em texto claro.
- Criar comando executável dentro do container, por exemplo `python -m app.scripts.bootstrap_admin`, compatível com o layout real.
- O comando solicita username e senha com `getpass`, confirmação e validação de força mínima; **não aceita senha pela linha de comando**.
- Não criar usuário nem senha padrão no startup e não permitir cadastro público.
- Repetir bootstrap não pode sobrescrever um administrador nem duplicar usuário silenciosamente. Se já existir, encerrar com mensagem clara.
- Não revelar senha, cookie, token ou hash no output do comando nem em logs.
- Não executar bootstrap no banco real nesta sessão do Codex: deixar para o operador, após os testes e a decisão de transporte.

## 6. Sessões e cookies

- Login com token de sessão imprevisível gerado por CSPRNG, com ao menos 256 bits. Persistir apenas SHA-256 (ou função apropriada) do token, nunca token bruto.
- Sessão vinculada a usuário ativo e papel autorizado. Timeout absoluto inicial 8h e inatividade 30min, configuráveis e conferidos no servidor.
- Refresh de último acesso com frequência moderada, sem trabalho desnecessário em toda requisição; não estender expiração absoluta.
- Logout via POST revoga a sessão no banco e remove cookie.
- Cookie por padrão `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/`, sem `Domain`; nome `__Host-...` em HTTPS se compatível. Não guardar privilégios ou senha no cookie.
- Em testes com `Secure=false`, exigir configuração explícita e verificar que o acesso está isolado em loopback + SSH; não fazer downgrade automático.
- Nenhum ID/token pode ser aceito via query string/URL. Evitar cache de páginas sensíveis: `Cache-Control: no-store` em respostas relevantes.
- Falhar de forma segura se configuração necessária estiver ausente ou contraditória. Não registrar segredos nem emitir cookies inseguros no binding HTTP da rede.

## 7. Login/logout e pré-sessão CSRF

Rotas esperadas, adaptáveis à estrutura real:

- `GET /admin/login`: formulário de login e pré-sessão CSRF temporária.
- `POST /admin/login`: valida pré-sessão e token CSRF; autentica; destrói pré-sessão; cria sessão **nova**; redireciona via 303 para `/admin/screens` ou `/admin`.
- `POST /admin/logout`: exige sessão, CSRF, revoga token e retorna ao login.

Para credenciais incorretas, exibir mensagem genérica e não criar sessão. Para CSRF inválido/ausente/expirado, retornar 403 e não autenticar. Não usar GET para logout.

As credenciais não podem aparecer em query string, log ou corpo de erro. Implementar limitação de tentativas repetidas (por conta e/ou origem, com tempo de expiração), testável, sem usar cegamente IP encaminhado pelo cliente. Não expor diferenças fáceis entre conta existente e inexistente.

## 8. CSRF autenticado

Usar token secreto aleatório associado à sessão no servidor, com validação segura. Incluir campo oculto em todos os formulários que alteram estado, incluindo:

- criação/edição/ativação/desativação de telas;
- upload de mídias;
- logout.

Exigir `X-CSRF-Token` na API de escrita autenticada por cookie (`POST /api/screens`, `PATCH /api/screens/{id}`, e futuras operações de escrita). O token deve ser obtido de forma segura por cliente autenticado; especificar mecanismo/documentação sem expô-lo publicamente.

Requisições sem CSRF, com token inválido ou de outra sessão devem retornar HTTP 403 **sem persistir mudanças**. `SameSite` e `Origin` podem complementar, mas não substituir CSRF. Não incluir token em links, URL ou logs.

## 9. Autorização de rotas

- Públicas: `GET /`, `GET /health`, `GET /admin/login`, `POST /admin/login` (com CSRF), e CSS mínimo necessário para login.
- `/admin`, `/admin/screens`, `/admin/media` e todas as ações: exigir usuário autenticado, ativo, papel `admin`.
- `/api/screens` (todos os métodos): exigir `admin`; sem sessão retornar 401 JSON, papel inadequado retornar 403 JSON, escrita sem CSRF retornar 403 JSON.
- `GET /media/{media_id}/file`: exigir `admin`, preservando a entrega por `FileResponse` e HTTP Range 206/416 para sessão autorizada. Sem sessão retornar 401; usuário sem papel retornar 403.
- `/docs`, `/redoc` e `/openapi.json`, se disponíveis, devem ser protegidos ou desabilitados ao anônimo.
- `GET` não pode modificar dados, mesmo quando autenticado. Acesso negado não pode modificar SQLite nem mídias.
- Para GET administrativo anônimo, redirecionar ao login de modo adequado; para API, retornar JSON (não HTML de login). Para POST administrativo anônimo, falhar sem efeitos colaterais, sem executar ação protegida.
- Garantir que o mecanismo de proteção abranja rotas atuais e não apenas a navegação do menu; proteger endpoints de acesso direto.
- Não criar nesta etapa endpoint público para TV Box ou liberar download anônimo de mídias. O futuro player usará autorização separada e escopo restrito a conteúdo publicado.

**Importante:** preservar nomes e semântica funcional dos endpoints já existentes, mas atualizar os testes para o **novo contrato de autenticação/CSRF**. Não remover testes antigos simplesmente porque agora exigem autenticação.

## 10. Interface

Continuar com Jinja2/HTML/CSS, reaproveitando `base.html` e `admin.css`. Adicionar login e uma indicação simples de usuário logado e ação Sair (form POST + CSRF). Não usar JS obrigatório nem CDN.

Tratar mensagens de credenciais inválidas, sessão expirada e acesso negado sem revelar detalhes internos. Formulários devem continuar responsivos e preservar a experiência das ETAPAS 004 e 005.

## 11. Segurança complementar

- Preservar CSP atual, `X-Content-Type-Options: nosniff`, validações de upload, proteção path traversal e limites de processamento.
- Nenhum log deve registrar senha, valores de cookies de sessão, tokens CSRF ou cabeçalhos sensíveis.
- Proteger de enumeração e repetição de tentativas de login.
- Não confiar em `X-Forwarded-For` ou `X-Forwarded-Proto` vindos de clientes não confiáveis. Não configurar `--forwarded-allow-ips=*`.
- Documentar limitações remanescentes: ausência de HTTPS institucional, MFA, recuperação de conta, trilhas completas de auditoria e tokens específicos para TV Boxes.

## 12. Docker e transporte seguro

Manter um único `signage-app`, usuário não-root, volume `signage-data` para SQLite e `signage-media` para arquivos. Atualizar tag, conforme convenção, para `digital-signage:etapa006`.

- Documentar variáveis de configuração em `.env.example`, sem valores secretos reais. `SESSION_COOKIE_SECURE=true` por padrão.
- **Não editar `.env` real nem trocar binding automaticamente.**
- Antes de demonstrar o login, o operador deverá decidir e aplicar uma das opções seguras:
  - HTTPS válido no ponto de acesso; ou
  - teste local isolado: `SIGNAGE_BIND_IP=127.0.0.1`, `SESSION_COOKIE_SECURE=false` e sinalização explícita de modo de testes locais, mais túnel SSH no cliente.
- Proibir recomendação de senha/login via `http://10.4.254.202:8080` enquanto não existir TLS.
- Se um requisito técnico impedir a configuração segura com os componentes atuais, **pare e reporte** antes de adaptar infraestrutura.
- Não instalar proxy, gerar certificado fictício para produção, mexer em SSH, UFW, sudoers ou daemon Docker.

## 13. Testes automatizados obrigatórios

Criar testes isolados (SQLite temporário e arquivos de mídia temporários), sem acesso aos volumes reais. Cobrir pelo menos:

1. Bootstrap do primeiro admin com senha oculta e hash Argon2id.
2. Bootstrap repetido não sobrescreve usuário e não cria conta padrão.
3. Login correto/incorreto, usuário inativo, username inexistente e mensagem genérica.
4. Login CSRF válido, ausente, expirado e pertencente a outra pré-sessão.
5. Destruição da pré-sessão e criação de sessão totalmente nova após login.
6. Cookie `HttpOnly`, `SameSite`, `Path`, `Secure` padrão e modo local explícito.
7. Token com entropia adequada e apenas hash persistido.
8. Expiração por inatividade e expiração absoluta controladas por relógio injetável/mocks.
9. Logout por POST, CSRF e invalidação real da sessão.
10. Tentativas repetidas bloqueadas conforme política; limpeza ou expiração do bloqueio.
11. GETs administrativos anônimos redirecionados ao login.
12. POSTs administrativos anônimos ou com CSRF inválido não alteram dados.
13. Proteção de criar/editar/alternar telas, upload MP4 e imagens.
14. Proteção de todos os endpoints `/api/screens`, incluindo leitura; retorno JSON 401/403.
15. Requisições API de escrita com e sem `X-CSRF-Token`.
16. Proteção de `/media/{id}/file`, inclusive `Range` 206 e 416 quando autorizado.
17. Usuário com papel insuficiente não altera nem lê áreas restritas.
18. `/`, `/health` e CSS do login continuam acessíveis.
19. `/docs`, `/redoc`, `/openapi.json` sem exposição anônima.
20. Regressão dos testes das etapas anteriores com autenticação válida quando aplicável; nenhuma regressão funcional.
21. Volume SQLite e diretório de mídias de produção não usados nos testes.
22. Configuração insegura padrão não é habilitada silenciosamente na LAN HTTP.

Não apagar ou desabilitar os 149 testes anteriores para obter resultado verde; ajustá-los ao novo contrato. Se precisar de alteração ampla na arquitetura ou se não for possível evitar uma vulnerabilidade relevante, pare e reporte.

## 14. Validação pelo operador após implementar

O Codex não deve presumir acesso sudo ao daemon Docker. Se houver restrição, não contornar; registrar como pendência do operador.

Após decisão explícita de transporte/binding, o operador executará:

```bash
cd /home/administrador/digital-signage
sudo docker compose config --quiet
sudo docker compose build
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
# Só após testes aprovados e configuração de acesso segura:
sudo docker compose up -d
sudo docker compose ps
sudo docker compose logs --tail=100 signage-app
```

**Não executar bootstrap/login em rede HTTP sem TLS.** Para modo de teste isolado, usar túnel SSH no computador do operador:

```powershell
ssh -N -L 18080:127.0.0.1:8080 administrador@10.4.254.202
```

Documentar o comando exato do bootstrap definido pela implementação (por exemplo, `sudo docker compose exec -it signage-app python -m app.scripts.bootstrap_admin`), mas **não executá-lo pelo Codex** e **não imprimir senha no comando**.

Checklist manual mínimo:

- Acesso anônimo ao `/admin` redireciona ao login e não mostra telas/mídias.
- Login inicial com administrador criado por CLI, via transporte seguro, funciona.
- Senha errada não autentica e tentativas repetidas são limitadas.
- Cadastro/edição/ativação de tela e upload MP4 funcionam com sessão válida.
- Logout impede acesso mesmo com cookie anterior; sessão expira.
- POST sem CSRF falha sem criar ou modificar dados.
- API anônima retorna 401; autorização insuficiente retorna 403.
- Arquivo MP4 não é servido anonimamente; autorizado continua aceitando HTTP Range.
- Após restart/recriação do container, usuário e dados permanecem; sessão comporta-se conforme política.
- TV Piloto e catálogo de mídias anteriores permanecem íntegros.
- Cookie e binding efetivos correspondem ao ambiente seguro selecionado.
- Backup consistente e procedimentos de recuperação documentados, sem apagar volumes.

## 15. Documentação

Atualizar apenas o necessário em `README.md`, `docs/STATUS.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/DEPLOYMENT.md`, `docs/OPERATIONS.md` e `.env.example`.

Explicitar: nova política de acesso; mudança intencional das respostas anônimas da API e dos downloads; requisitos de transporte seguro; como criar primeiro administrador sem senha na linha de comando; parâmetros de cookie; expiração/revogação de sessão; CSRF; limitações; resultados realmente executados e pendências do operador.

Não declarar proteção em produção nem conclusão operacional antes das evidências do operador. Não afirmar que `10.4.254.202:8080` em HTTP é seguro só porque está na rede local.

## 16. Git e relatório final

NÃO executar `git add`, `git commit`, `git push`, alterar histórico ou criar branch. O operador fará auditoria e versionamento.

Ao finalizar, informar:

1. Estado inicial, HEAD, arquivos inspecionados e divergências.
2. Arquivos criados e modificados.
3. Dependências novas e justificativa.
4. Tabelas e modelo de usuário/sessão/pré-sessão.
5. Bootstrap: funcionamento e comando previsto para operador (sem executar em produção).
6. Login, logout, CSRF e autorização em todas as rotas.
7. Gestão e expiração de cookies/sessões.
8. Proteção contra brute force, enumeração e vazamento de segredos.
9. Mudanças intencionais nos códigos HTTP das rotas existentes.
10. Testes **efetivamente executados**, quantidade de aprovados/falhas/warnings; testes não executados como pendentes.
11. Docker, volumes e variáveis; riscos e configuração de transporte seguro.
12. Regressões, pendências e próximos testes operacionais.
13. `git status --short`, `git diff --stat`, `git diff --check` (não omitir arquivos novos não rastreados).
14. Confirmação de que não houve git add, commit, push nem alteração de host.
15. Sugestão sucinta de próxima etapa, sem implementá-la.

Nenhuma modificação posterior à auditoria final sem registrá-la.
