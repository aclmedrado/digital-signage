# ETAPA 008 — Prompt de implementação: Player Web e Pareamento Seguro de TVs

**Projeto:** Digital Signage — IFG Câmpus Inhumas  
**Data:** 2026-10-15  
**Documento normativo:** `docs/adr/0008-web-player-and-device-pairing.md`  
**Etapa anterior:** 007, concluída e versionada em `32925f4`  
**Estado anterior validado:** 439 testes aprovados e 20 testes operacionais, imagem `digital-signage:etapa007`  
**Imagem alvo:** `digital-signage:etapa008`

## 0. Contrato obrigatório de execução

Você é o Codex trabalhando **exclusivamente** no repositório oficial `/home/administrador/digital-signage`, no host `utilities`. Antes de alterar arquivos:

1. Confirme `pwd`, `git branch --show-current`, `git status --short`, `git log -1 --oneline`, `git diff --check`.
2. Exija branch `main`, working tree limpa, ADR 0008 e este prompt **já versionados**. Em caso de divergência, pare e informe ao operador; não apague ou sobrescreva alterações de terceiros.
3. Leia integralmente `AGENTS.md`, `README.md`, `docs/STATUS.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, `docs/OPERATIONS.md`, `docs/SECURITY.md`, os ADRs 0001–0008, além do presente prompt. Inspecione contratos reais de `app/security.py`, `app/services/auth.py`, `app/routes/admin/auth.py`, `app/services/media.py`, `app/routes/media.py`, `app/services/playlists.py`, `app/database.py`, `app/models.py`, `app/main.py`, templates e testes antes de planejar alterações.
4. Registre diferenças entre premissas deste documento e repositório real; adapte detalhes internos **sem fragilizar os requisitos**. Se existir conflito arquitetural ou necessidade de alteração destrutiva, não improvise: pare e peça orientação.
5. Não execute `git add`, `git commit`, `git push`, `git reset`, trocas de branch, instalações globais, `sudo`, bootstrap no banco real, `docker compose down -v`, nem modifique configurações globais do host.
6. Não acesse o `.env` real, senhas, cookies, sessões de produção ou mídias privadas para depurar. Não modifique `.env`, DNS, portas, binding, Caddy, nginx, firewall, SSH, certificados, proxy global ou serviços institucionais.
7. Não declare build/pytest/validação operacional concluídos se não os executou efetivamente. A restrição conhecida `sudo: no new privileges` não deve ser contornada.
8. **Não iniciar ETAPA 009.** O teste físico das BTV13/H6+ e a exposição por HTTPS na LAN ficam para a integração posterior.

## 1. Objetivo e escopo

Implementar a primeira versão funcional do player HTML/CSS/JavaScript para reprodução contínua das playlists da ETAPA 007 e um fluxo **seguro, exclusivo e revogável de pareamento por tela**, sem contas administrativas nos dispositivos.

Entrega desta etapa:

- Página de ativação de dispositivo por código temporário, com CSRF pré-sessão e limitação de tentativas.
- Tela administrativa por TV para gerar código, visualizar estado e revogar acesso, autenticada e protegida por CSRF.
- Cookie persistente de dispositivo, armazenando apenas token opaco no navegador; hash no SQLite; autorização limitada a uma TV específica.
- Player em tela cheia e manifesto JSON por tela; entrega restrita das mídias da playlist vinculada com suporte HTTP Range.
- Reprodução sequencial e looping, com imagens cronometradas e MP4 até o evento `ended`, atualização de conteúdo em transições, tolerância a falhas e sinalização neutra em ausência de conteúdo.
- Testes completos e documentação consistente com os requisitos de segurança das etapas 005–007.

Não entregar: Chromium kiosk, instalação de Debian/TV Box, autopartida do sistema operacional, infraestrutura HTTPS, áudio automático, offline/service worker, agendamentos, DRM, telemetria, fila de tarefas, múltiplos containers ou frontend framework.

## 2. Invariantes que não podem sofrer regressão

- Administração de telas, mídias e playlists intacta: rotas, autenticação administrativa, autorização por papel e CSRF.
- `/media/{media_id}/file` mantém exigência de administrador. **Nunca** permitir cookie de dispositivo nesse endpoint.
- `/api/screens` e `/admin/**` não aceitam cookie de dispositivo como autorização; `/docs`, `/redoc`, `/openapi.json` seguem indisponíveis conforme ETAPA 006.
- `/health` continua público e não toca dados sensíveis.
- `Screen`, `MediaAsset`, `Playlist`, `PlaylistItem` e `ScreenPlaylistAssignment` preservados, bem como usuários e sessões já existentes; sem DROP/ALTER destrutivo.
- Um serviço Compose, `signage-app`, imagem `digital-signage:etapa008`, volumes persistentes `signage-data` e `signage-media`, UID/GID 10001, healthcheck e portas existentes. Não instalar dependências JS nem novo banco.
- A configuração HTTPS obrigatória e o modo de teste local isolado da ETAPA 006 **não** podem ser afrouxados. Nenhuma senha/token/código em URL ou log.

## 3. Modelo persistente e operações atômicas

Introduza, pelo `Base.metadata.create_all`, tabelas novas (nomes SQL legíveis e consistentes). Referência de modelos:

### 3.1. `ScreenPairingCode`

- `screen_id`: PK e FK para `screens.id`; no máximo um código pendente por tela.
- `code_hash`: SHA-256 do código secreto, único e indexado; código real gerado com `secrets` e entropia >= 128 bits; representação legível sem reduzir entropia.
- `created_by_user_id`: FK para administrador que o emitiu, se houver suporte coerente com User.
- `created_at`, `expires_at` (10 minutos).
- Gerar novo código invalida somente o código pendente anterior, **não** revoga a sessão atual.
- Somente exibir o código na resposta imediata ao POST do administrador, jamais em GET futuro ou log; resposta com `Cache-Control: no-store`.
- Consumo bem-sucedido elimina o código da tabela na mesma transação que cria/substitui a sessão do dispositivo.

### 3.2. `ScreenDeviceSession`

- `screen_id`: PK e FK para `screens.id`, garantindo no máximo uma sessão por tela.
- `token_hash`: SHA-256 exclusivo de token gerado com `secrets` com entropia >= 256 bits, jamais token puro no DB.
- `created_at`, `expires_at`: validade absoluta **90 dias** (não renovável silenciosamente nesta etapa); campo de revogação opcional se revogar por exclusão.
- Na ativação com novo código válido: substituir em transação a sessão anterior da mesma tela. O dispositivo antigo perde autorização na próxima solicitação.
- Na revogação administrativa: remover/inutilizar sessão e código pendente de forma atômica. Não interferir nas sessões de outras TVs.
- Cookie persistente por `Max-Age`/`Expires` compatível com validade de servidor. A sessão deve sobreviver à recriação do container graças ao SQLite persistente.

### 3.3. Limitação de tentativas

- Persistência de contador/expiração por **origem real** derivada de conexão confiável, sem confiar em `X-Forwarded-*` arbitrário. Não compartilhar chave de limite com o login administrativo sem namespace isolado.
- Política de referência: até 10 códigos inválidos por origem em janela de 15 minutos; após isso, HTTP 429 e resposta genérica. Limpar/expirar registros sem crescimento ilimitado a longo prazo.
- Testar concorrência, expiração e transação rollback. Falhas de banco devem resultar em indisponibilidade controlada, nunca bypass.

Use `BEGIN IMMEDIATE` quando pertinente às leituras e escritas concorrentes, conciliando com o gerenciamento de sessões do SQLAlchemy já existente; garanta que uma corrida para consumir o mesmo código não resulte em duas ativações.

## 4. Segurança de cookies, transporte e ativação

**Não mudar configurações do servidor.** Reutilize `AuthSettings` para selecionar nomes e atributos consistentes:

| Ambiente | Nome sugerido | Secure | Demais atributos |
|---|---|---|---|
| HTTPS institucional | `__Host-signage-device` | `true` | `HttpOnly`, `SameSite=Lax`, `Path=/`, sem Domain |
| Teste local com túnel | `signage-local-device` | `false` | `HttpOnly`, `SameSite=Lax`, `Path=/`, sem Domain |

O modo local só é autorizado se `SIGNAGE_BIND_IP=127.0.0.1`, `SIGNAGE_PORT=8080`, `SESSION_COOKIE_SECURE=false`, `LOCAL_AUTH_TEST_MODE=true`, nenhum proxy confiável e túnel SSH, conforme ETAPA 006. Não inventar exceção para HTTP em IP da LAN.

Fluxo explícito:

1. Administrador autenticado abre `GET /admin/screens/{screen_id}/player` e observa instruções e estado (pareado/não pareado; expiração quando conveniente, nunca mostrar hash ou token).
2. Administrador envia `POST /admin/screens/{screen_id}/player/pairing` com CSRF existente; vê novo código de uso único e validade de 10 minutos. O código **não** aparece no endereço do navegador nem em templates posteriores.
3. Dispositivo abre `GET /device/activate`, recebe pré-sessão de CSRF apropriada e apresenta formulário com campo para código; `POST /device/activate` recebe código via corpo, valida CSRF e rate limit, verifica validade e consome em transação.
4. Servidor responde com cookie de dispositivo e redirecionamento 303 para `/player/s/{slug}`. O código deixa de funcionar. O dispositivo tem acesso **somente** à tela vinculada.
5. Administração consegue revogar por `POST /admin/screens/{screen_id}/player/revoke` com CSRF, sem expor cookie ou sessão; um futuro reparing também invalida a sessão antiga ao consumir o novo código.
6. `GET /player/s/{slug}` também pode ser acessado por administrador autenticado para **prévia**, sem ativação nem novo cookie de dispositivo. A prévia não transforma um cookie admin em identidade de TV.

Importante: implementar CSRF de ativação anônima corretamente. Inspecione `LoginChallenge`/funções de login e reutilize o padrão seguro de desafio pré-sessão se aplicável, sem compartilhar estado de forma que um desafio de login possa ser usado indevidamente na ativação. `SameSite=Lax` sozinho não basta. Normalizar códigos inseridos apenas de maneira explicitamente documentada (ex.: espaços e hífens); hashing/validação não devem reduzir segurança. Usuários não autorizados não descobrem tela/slug pela ativação. Incluir headers de cache e segurança. Não imprimir cookies nem códigos em testes reais/relatório.

## 5. Rotas e política de acesso

Implante os seguintes contratos, podendo ajustar nomes internos de funções mas **não enfraquecer o esquema de autorização**:

| Rota | Quem acessa | Comportamento |
|---|---|---|
| `GET /admin/screens/{screen_id}/player` | Admin | Página de administração/pareamento/prévia |
| `POST /admin/screens/{screen_id}/player/pairing` | Admin + CSRF | Emite código, mostra uma vez |
| `POST /admin/screens/{screen_id}/player/revoke` | Admin + CSRF | Revoga sessão e código pendente |
| `GET /device/activate` | Público | Página mínima e desafio CSRF |
| `POST /device/activate` | Público + CSRF + limite | Troca código por cookie de TV |
| `GET /player/s/{slug}` | Admin ou sessão **da mesma tela** | HTML de reprodução |
| `GET /player/s/{slug}/manifest` | Admin ou sessão **da mesma tela** | JSON de programação |
| `GET /player/s/{slug}/media/{media_id}` | Admin ou sessão **da mesma tela** | Mídia pertencente à playlist **atual**, com Range |

Para identidade com slug não existente, não autorizado ou outra tela, responda com 401/403/404 coerentes, sem revelar atributos de telas protegidas. HTML anônimo pode redirecionar à página de ativação; manifesto e mídia nunca fazem downgrade para conteúdo público. Admin no papel não autorizado (`viewer` nos testes) não equivale a admin.

Reveja especificamente `AuthMiddleware` e dependências para que as rotas novas não sejam bloqueadas por engano nem eximidas em excesso. **Preferir negação por padrão e allowlist explícita.** Cookies de dispositivo **nunca** satisfazem `require_form_csrf`, APIs administrativas ou sessão administrativa. Se alterar a middleware, amplie cuidadosamente testes negativos das rotas antigas.

### 5.1. Media guard

A rota de mídia do player:

- Revalida sessão e `screen_id` em **cada requisição**, inclusive Range.
- Revalida `Screen.active`, `ScreenPlaylistAssignment`, `Playlist.active` e presença do `media_id` entre `PlaylistItem` da playlist atual; mídia inativa/ausente não é exposta.
- Reutiliza mecanismo seguro de armazenamento e `FileResponse` da ETAPA 005, valida caminhos, MIME e codificação já existentes; não gera caminho físico a partir de parâmetro arbitrário.
- Preserva `Range: bytes=0-99` => 206, 100 bytes quando arquivo >= 100 bytes, e intervalo inválido => 416; `HEAD` somente se explicitamente autorizado e testado.
- `Cache-Control: private, no-store` (ou política estrita e equivalente justificada), `nosniff`; CORS aberto, listagem de diretórios e downloads públicos proibidos.

Uma playlist compartilhada não autoriza usar cookie da TV A no endpoint da TV B, mesmo quando o `media_id` é idêntico.

## 6. Manifesto e atualização de conteúdo

Implemente função de serviço específica para manifesto que utilize modelos existentes e gere uma representação **estável, ordenada e testável**. Contrato de referência:

```json
{
  "screen": {"slug": "tv-piloto", "name": "TV Piloto"},
  "state": "playing",
  "revision": "sha256-deterministico",
  "poll_after_seconds": 20,
  "items": [
    {"id": 21, "kind": "image", "duration_seconds": 15, "url": "/player/s/tv-piloto/media/7"},
    {"id": 22, "kind": "video", "duration_seconds": null, "url": "/player/s/tv-piloto/media/8"}
  ]
}
```

Regras:

- O manifesto somente descreve a playlist ativa associada àquela `Screen` ativa. Sem associação, tela inativa ou playlist indisponível => `items: []`, estado neutro e não expor caminhos de mídia.
- Preservar `PlaylistItem.position`, inclusive duas instâncias de um mesmo `MediaAsset` com `id` de item diferente.
- Imagem usa duração armazenada, vídeo com `duration_seconds: null` e termina naturalmente.
- `revision` é hash determinístico do conteúdo e vínculo relevante (screen_id, estado, playlist_id, IDs de itens, mídia, ordem e duração, versões pertinentes), não um valor aleatório por chamada. Testes comprovam que não muda sem alteração e muda ao editar, trocar vínculo, reordenar ou desativar.
- A resposta não contém nome físico do arquivo, caminho `/app/media`, credencial, hash de sessão, tabelas de usuário ou dados de outras telas.
- Polling a cada ~20 segundos (documentar tolerância/jitter); evitar múltiplas chamadas concorrentes e requisições de checagem rápidas em loop.
- Mudança normal de conteúdo deve ser aplicada no limite do item em reprodução (imagem após duração; vídeo após `ended`). Revogação, perda de autorização ou desativação da tela devem interromper imediatamente o que for exibido.
- Evitar prender o cliente para sempre em manifesto/cache antigo após recuperar a rede.

## 7. Player visual e máquina de estados JS

Arquivos sugeridos (ajuste à organização real):

- `app/routes/player.py` — endpoints do player/manifesto/mídia.
- `app/routes/device.py` — ativação anônima e sessão do dispositivo.
- `app/routes/admin/device.py` — operações protegidas no painel.
- `app/services/player.py` ou `app/services/device_auth.py` — domínio e autorização, sem lógica de frontend.
- `app/templates/player/index.html`, `app/templates/player/activate.html` e páginas/admin fragmentos correspondentes.
- `app/static/player.css`, `app/static/player.js` — código JS próprio, sem CDN.
- Novos testes `tests/test_player.py`, `tests/test_device_auth.py` (ou nomes equivalentes).

Comportamento obrigatório:

1. **Layout:** fullscreen, fundo escuro, imagem/vídeo centralizados com `object-fit: contain`; indicador neutro de carregamento/sem conteúdo; sem botões administrativos visíveis; sem layouts que deixem barras de rolagem na TV.
2. **Vídeo:** `<video muted autoplay playsinline>` ou atributos equivalentes, ocultar controles padrão, iniciar `.play()` e tratar rejeição da Promise; continuar só no evento `ended`; repetir vídeo desde zero quando reaparece na playlist. Não prometer áudio autoplay.
3. **Imagem:** aguardar carregamento e exibir pelo número de segundos do item; descarregar e avançar corretamente. Duração de imagens repetidas é por item, não por mídia.
4. **Loop:** após o último item, retornar ao primeiro; não criar timers duplicados nem reutilizar listeners antigos.
5. **Manifesto:** carregar ao iniciar, reconsultar periodicamente, armazenar nova revisão pendente, aplicar na próxima transição. Caso a TV seja desativada ou o acesso revogado, interromper imediatamente, limpar mídia e mostrar estado seguro.
6. **Falhas:** imagem inexistente, vídeo erro de rede, MP4 incompatível, `.play()` rejeitado ou travamento não geram loop rápido. Timeout limitado e estratégia de pular item; se todos os itens falharem, exibir estado neutro e tentar novamente depois de intervalo >= 15 segundos. Rede desconectada => tentativas com backoff, sem polling por segundo e sem cache offline.
7. **Desempenho:** não carregar todos os MP4 antecipadamente, limpar `src` dos elementos anteriores quando conveniente, lidar com aba em segundo plano, evitar vazamento de timers/listeners. Contagem de tempo é do cliente, não confiar nela para autorização.
8. **Autorização:** fetch e elementos de mídia utilizam cookies da mesma origem. Não colocar tokens de sessão no DOM, `localStorage`, cabeçalho personalizado lido pelo JS ou string de query.
9. **Conteúdo não confiável:** interpolação de nomes e títulos deve usar escape adequado e APIs de DOM seguras; nunca injetar HTML derivado do banco via `innerHTML` desprotegido. Recursos estáticos locais compatíveis com a CSP existente; quando a CSP atual `script-src 'none'` impedir player, criar política **restrita e específica apenas para páginas de player**, autorizando JS de mesmo domínio sem `unsafe-inline`/`unsafe-eval`, preservando as páginas administrativas.
10. **Experiência de teste:** permitir navegador desktop; tela cheia pode ser ativada via F11 manual, sem assumir que a API fullscreen funciona sem gesto de usuário.

Observação: a validação de reprodução real de MP4/H.264 em hardware BTV13/H6+ não deve ser inferida a partir de testes HTTP ou do navegador desktop.

## 8. Integração administrativa e documentação

- Acrescentar link de **Player / Pareamento** à listagem de telas ou página pertinente, preservando navegação existente e responsividade.
- Exibir estado da tela, validade do dispositivo, ação de emitir novo código e revogar, explicando que o código expira e que nova ativação substitui acesso anterior.
- Exibir link de prévia de cada tela; ao usar a sessão administrativa, não emitir cookie de dispositivo nem confundir prévia com pareamento real.
- Tratar páginas de erro sem expor stack trace, hash, cookie ou dados internos. Usar PRG 303 após ações administrativas quando possível; exibição única do código pode exigir resposta 200 em POST, documentar conscientemente.
- Atualizar `README.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, `docs/OPERATIONS.md`, `docs/SECURITY.md`, `docs/STATUS.md`, registrando precisamente o que é **implementado** e o que está **pendente de execução pelo operador**.
- Adicionar instrução de teste com dois perfis de navegador, usando `http://localhost:18080` através de `ssh -N -L 18080:127.0.0.1:8080 administrador@10.4.254.202`. **Não** liberar IP LAN por HTTP e não modificar `.env`.

## 9. Testes automatizados exigidos

Preserve toda a suíte anterior (439 casos), atualizando expectativas legítimas do esquema/rotas apenas quando necessário, sem remover testes, `skip`, `xfail` ou relaxar assertions. Adicione testes de unidade/integração FastAPI + SQLAlchemy e teste com DB SQLite temporário/isolado, cobrindo ao menos:

**Pareamento e credenciais**

- Código gerado somente por admin logado e com CSRF; POST anônimo 401, papel insuficiente 403, CSRF inválido 403.
- CSPRNG/entropia da geração, hash em repouso, código não reaparece em GET nem em log ou URL.
- Código válido, expirado, reutilizado, trocado por nova emissão, inexistente e com formato errado; resposta genérica quando inválido.
- CSRF pré-sessão exigido no POST público de ativação; origem sem sessão recusada.
- Limite por origem, HTTP 429 e não confiar em cabeçalhos `X-Forwarded-For` do cliente.
- Consumo concorrente único; reemissão não revoga dispositivo já pareado; novo pareamento bem-sucedido substitui sessão anterior.
- Revogação administrativa desautoriza imediatamente a próxima requisição; não afeta outras telas.
- Cookie com nome/Path/HttpOnly/SameSite/Secure corretos tanto em modo HTTPS simulado quanto no modo local, e expiração coerente; não aceitar cookie alterado, expirado, revogado ou hash da base como token.
- Persistência de sessão de dispositivo no SQLite entre conexões/instâncias de app; lógica absoluta de 90 dias com relógio controlável em testes (não esperar 90 dias reais).

**Isolamento e regressão**

- Dispositivo da TV Piloto não abre player, manifesto nem mídia da TV do Pátio; mesmo arquivo presente nas duas playlists não amplia autorização.
- Cookie de dispositivo não autoriza `/admin`, `/api/screens` e `/media/{id}/file`; admin continua podendo fazer prévia sem virar dispositivo; papel `viewer` não equivale a admin.
- Manifesto sem autenticação ou acesso a outra tela retorna recusa apropriada; nenhum item público é vazado.
- Tela desativada, sem atribuição, playlist indisponível, playlist com itens, repetição e ordenação.
- `revision` estável e variando após alterações relevantes de ordem, item, duração, playlist/vínculo/tela.
- Mídia de outra playlist, arquivo não listado, arquivo removido/inexistente ou tela inativa: acesso negado sem revelar paths.
- Range autorizado HTTP 206 (100 bytes para bytes=0-99), Range inválido HTTP 416 e acesso anônimo negado; contrato admin da ETAPA 005 preservado.
- Testes de não retrocesso de login, CSRF administrativo, sessões antigas, API de telas, upload de mídia e operações de playlists.
- Falha SQL e rollback das mutações; FKs habilitadas e `create_all` incremental; sem modificar dados existentes em criação de tabelas.
- Headers de cache e CSP com script local estrito para player e política administrativa preservada.

Testes automatizados do servidor **não substituem** os testes manuais da máquina de estados JavaScript no navegador. Se houver ferramenta de browser existente e utilizável sem novas dependências, aproveite; não alegue teste de browser se apenas compilou templates ou inspecionou JavaScript.

## 10. Validações estáticas pelo Codex

Se ambiente permitir sem sudo, execute testes específicos e completos **apenas se realmente possíveis**. Caso `sudo docker compose` permaneça bloqueado, não tente contornar. Faça, quando disponíveis:

- `python -m compileall -q app tests` ou AST, sem poluir repo com `__pycache__` rastreado.
- Compilação/renderização Jinja2 em ambiente que já tenha dependências disponíveis.
- `docker compose config --quiet` sem sudo se acessível; não fingir sucesso se indisponível.
- `git diff --check`, revisão de diff e checagem de escopo, no working tree e em todos os arquivos novos.
- Inventário de funções/parametrizações de testes como **estimativa**, jamais como execução ou aprovação.

Não editar documentos normativos versionados (`docs/adr/0008-*`, `docs/prompts/etapa008.md`) para acomodar decisões de implementação sem aprovação do operador.

## 11. Implantação e validação reservadas ao operador

**Não executar estas ações pelo Codex nem dizer que já ocorreram.** Documente os comandos e aguarde as evidências do operador:

```bash
cd /home/administrador/digital-signage

git diff --check
git status --short
sudo docker compose config --quiet
sudo docker compose build
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
```

Somente após build e pytest passarem, e após **backup conjunto apropriado do SQLite, mídias e `.env` fora do Git**, o operador executará:

```bash
sudo docker compose up -d
sudo docker compose ps
sudo docker compose logs --tail=100 signage-app
```

Conferir imagem etapa008, estado `healthy`, binding `127.0.0.1:8080`, os modelos/tabelas adicionais, autorização, cookies e persistência. Não executar `docker compose down -v`.

### 11.1. Checklist operacional sugerido (executado pelo operador)

1. Login administrativo e telas/mídias/playlists anteriores intactos.
2. Visualização da área de pareamento da TV Piloto e da TV do Pátio.
3. Emissão de código temporário por administrador autenticado; código não reaparece ao atualizar GET.
4. Geração de novo código invalida o anterior, sem desconectar sessão previamente válida.
5. Acesso à página pública de ativação em perfil de navegador separado.
6. Ativação com código correto e redirecionamento para player da TV Piloto.
7. Reuso do mesmo código e código incorreto recusados.
8. Cookie de dispositivo `HttpOnly`, `SameSite=Lax` e `Secure` coerente com teste local.
9. Perfil do dispositivo não acessa painel, API ou endpoint admin de mídia.
10. Perfil da TV Piloto não abre player/manifesto/mídias da TV do Pátio.
11. Administrador consegue pré-visualizar player sem gerar sessão de dispositivo.
12. Imagem aparece pelo tempo configurado, incluindo repetição com duração própria.
13. Vídeo MP4 inicia mudo, reproduz até o final e passa ao item seguinte.
14. Após último item, player volta ao primeiro.
15. Alteração de ordem/duração aparece no player na transição apropriada.
16. Troca da playlist da tela reflete-se no player sem reset imediato desnecessário.
17. Tela desativada/sem playlist mostra estado neutro, sem mídia exposta.
18. Mídia com Range autenticado: HTTP 206 e 100 bytes; Range inválido HTTP 416.
19. Mídia ausente ou falha de reprodução não produz loop rápido nem tela permanentemente quebrada.
20. Revogação administrativa interrompe acesso do dispositivo na próxima verificação; outro dispositivo não é afetado.
21. Reparar a mesma TV substitui a sessão anterior; código expira após 10 min (testes de tempo automatizados aceitáveis).
22. Restart e `up -d --force-recreate` preservam pareamento ativo e dados existentes.
23. Testes de largura estreita e modo tela cheia em navegador desktop.
24. O serviço continua acessível **somente via 127.0.0.1 e túnel SSH**, sem publicação de login HTTP na LAN.

Os passos de reprodução de mídia requerem que a TV de teste tenha playlist com imagem e MP4 reais; não declarar aprovado sem verificação.

## 12. Relatório obrigatório ao fim da implementação

Ao concluir o código, entregue um relatório completo, **não um anúncio de conclusão operacional**, com:

1. Confirmação de diretório, branch, HEAD inicial/final e estado inicial limpo.
2. Arquivos novos e modificados e justificativa de mudanças sensíveis em autenticação/middleware.
3. Esquema/tabelas criados, constraints, geração e hashing de código/token, revogação, CSRF, rate limit, tratamento de concorrência.
4. Rotas, regras de acesso administrativo versus dispositivo e decisões do manifesto/media guard.
5. Máquina de reprodução JS e comportamento em erros, polling, atualização, loop, `muted`, CSS e CSP.
6. Testes definidos, testes **realmente executados** com contagem e warnings (ou expressamente zero executados), e verificações estáticas efetivas.
7. Limitações remanescentes e riscos de segurança, sem afirmar acesso LAN/HTTPS, restauração ou teste BTV13 realizados.
8. Comandos de build/pytest/deploy e roteiro operacional para o operador, sem executá-los se sem privilégio.
9. `git diff --check`, `git diff --stat`, `git status --short`, incluindo arquivos não rastreados no relatório.
10. Confirmação de não ter executado `git add`, commit, push, bootstrap, alteração do `.env` ou modificações globais.

**Pare após apresentar o relatório.** A validação, atualização documental pós-homologação e commit final serão orientados separadamente pelo operador.
