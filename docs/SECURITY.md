# Segurança

## Player e dispositivos — ETAPA 008 (homologação funcional local)

Implementação, build, regressão completa, implantação e homologação funcional
no navegador confirmados pelo operador no ambiente HTTP local por túnel SSH.
Não há liberação institucional ampla nem publicação de HTTP na LAN. O modo
local e AuthSettings da ETAPA 006 permanecem os da implementação; neste
fechamento não houve alteração de .env, binding, proxy ou infraestrutura.
Cookies de dispositivo jamais autorizam `/admin/**`, `/api/screens` ou
`/media/{id}/file`. Administrador ativo pode fazer prévia sem se parear.
Viewer não equivale a administrador. Cada requisição de manifesto/mídia
exige sessão da própria tela; compartilhar playlist não compartilha autorização.

Código: CSPRNG de 128 bits, Base32 ASCII, caixa indiferente, espaços ASCII e
hífens opcionais, hash SHA-256 em repouso, 10 minutos, uso único. POST admin
com CSRF mostra o código somente na resposta 200/no-store; GET não recupera.
Novo código preserva dispositivo atual até o consumo transacional bem-sucedido.
Sessão opaca de 256 bits, somente hash no SQLite, 90 dias absolutos, persistente
e revogável/substituível. Cookies HttpOnly/SameSite=Lax/Path=/, sem Domain,
Secure e prefixo __Host- em HTTPS; nomes distintos no teste local existente.
Sem tokens em URLs, JS, localStorage ou logs. Revogação com confirmação e CSRF
remove sessão e código da tela, sem afetar outras.

Ativação tem desafio CSRF próprio (cookie e CSRF de 256 bits com hashes,
10 minutos, consumo atômico), separado do login. Corpo POST limitado a 2 KiB,
campos únicos, sem refletir segredo. Até 10 códigos inválidos por origem real
em 15 minutos; posteriores recebem 429 genérico, inclusive código válido até
expiração. Não lê X-Forwarded-For arbitrário. Contadores são persistentes e
independentes do login; sucessos não incrementam. BEGIN IMMEDIATE serializa
emissão/consumo/revogação; SQL indisponível causa recusa genérica/rollback.

Mídia exige vínculo atual, tela/playlist ativas e item presente; arquivo deve
existir em caminho UUID confinado. MediaAsset não possui flag active; não há
mudança no seu esquema. Range é autorizado a cada GET, HEAD não foi habilitado.
Manifesto não contém caminhos físicos nem credenciais. Respostas têm
private/no-store e nosniff. CSP de script/connect self é específica do HTML do
player, sem unsafe-inline/eval; política admin/ativação mantém script none.
Polling de 20–22 s mais latência significa que revogação/desativação é percebida
na próxima verificação; bytes já recebidos não podem ser revogados retroativamente.
Falhas de rede limpam a mídia; não há garantia offline, DRM ou atestação.

O operador confirmou imagem `digital-signage:etapa008` construída, container
healthy após recriação, `/health` HTTP 200, logs de inicialização sem erros,
binding exclusivo `127.0.0.1:8080`, acesso pelo navegador via túnel SSH,
FKs iguais a 1 e quatro tabelas de pareamento/dispositivos. Suíte em container
executada pelo operador: **555 passed, 1 warning de depreciação Starlette/AnyIO
em 821.67 segundos, zero falhas**. O caso corrigido de cookie contendo hash
e as cinco parametrizações passaram separadamente; histórico em
[STATUS](STATUS.md#investigação-do-pytest--cookie-contendo-hash).

Manualmente, o operador confirmou isolamento entre TVs, recusa de página/
manifesto/mídia da outra tela, bloqueio administrativo do dispositivo,
revogação sem afetar outras TVs, novo pareamento invalidando sessão antiga,
reemissão e invalidação do código anterior, código inválido recusado, prévia
sem cookie de dispositivo e persistência após restart/recriação, além da
reprodução e recuperação de rede. Não foram informadas saídas HTTP manuais
individuais para esses cenários.

Os 13 testes JS anteriores do Codex usam DOM/relógio simulados; falhas
artificiais de mídia são evidências automatizadas. Expiração do código em
10 minutos é coberta em Python com relógio simulado. Emissão com CSRF e código
ausente no GET, atributos do cookie de dispositivo e Range 206/100 bytes e 416
têm cobertura Python aprovada, mas aguardam confirmação manual identificada.
As propriedades técnicas descritas acima são contratos da implementação;
não são novas medições manuais de cookies/HTTP. A
[matriz dos 24 itens](OPERATIONS.md#evidências-por-item-do-checklist-008)
discrimina a origem e os detalhes sem confirmação; não se declara 24/24 manuais.

Backup pré-implantação confirmado pelo operador em
`/home/administrador/signage-backups/before-008-20261016-171852`, com SQLite
consistente, mídias e `.env` fora do repositório, sem restauração conjunta
formal. Nenhum resultado foi reexecutado pelo Codex neste fechamento e não
houve acesso a banco real, backup, credenciais, cookies ou `.env`.
Não se infere suporte físico BTV13/H6+, Chromium kiosk ou HTTPS institucional.
Não há armazenamento offline de mídias; revogação não elimina bytes já
transferidos. O acesso permanece somente pelo túnel SSH no HTTP local.
Limitação de tentativas/desafios não resolve DoS ou quotas globais; backup
contém dados sensíveis. HTTPS institucional, restauração conjunta, MFA,
recuperação administrativa e auditoria continuam pendentes.
Este fechamento não inicia nem conclui a ETAPA 009.

## Segurança administrativa — ETAPA 006

Implementada conforme ADR 0006 e validada operacionalmente pelo operador
no ambiente local com túnel SSH. Config/build aprovados, imagem
digital-signage:etapa006, container digital-signage-app healthy e inicialização
sem erros nos logs apresentados. Testes automatizados: 267 passed, 1 warning
de depreciação Starlette/AnyIO em 172.98 segundos, sem falhas; todos os testes
anteriores permaneceram aprovados. Separadamente, os 18 itens manuais foram
aprovados pelo operador. Os resultados são os fornecidos pelo operador nesta
solicitação, sem execução ou reexecução pelo Codex nesta atualização documental.
Evidências e bloqueio sudo inicial preservados em
[STATUS](STATUS.md#validação-operacional-da-etapa-006).

O ambiente validado usa temporariamente:

```text
SIGNAGE_BIND_IP=127.0.0.1
SIGNAGE_PORT=8080
SESSION_COOKIE_SECURE=false
LOCAL_AUTH_TEST_MODE=true
```

O operador confirmou binding efetivo 127.0.0.1:8080 e acesso administrativo
por túnel SSH, sem exposição direta do HTTP à rede institucional nesse ambiente.
Esse modo destina-se exclusivamente aos testes locais por túnel SSH; não
constitui liberação para uso institucional amplo. Antes dessa disponibilização,
permanecem necessários HTTPS com certificado válido, SESSION_COOKIE_SECURE=true,
LOCAL_AUTH_TEST_MODE=false, revisão das políticas de acesso e definição de
autenticação específica para os futuros players das TV Boxes.

Resultados manuais de segurança confirmados pelo operador:

- primeiro administrador criado com sucesso; login correto aprovado, senha
  incorreta recusada e logout seguido de exigência de nova autenticação;
- GET /health: 200; GET /admin/screens sem sessão: 303 para /admin/login;
  GET /api/screens e GET /media/1/file sem sessão: 401;
- escrita autenticada sem X-CSRF-Token: 403, confirmando proteção CSRF;
- cookies conferidos no navegador: HttpOnly habilitado, SameSite=Lax e Secure
  desabilitado conforme a configuração temporária de HTTP local; transporte
  de rede por túnel SSH. Isso não valida cookies Secure em HTTPS institucional;
- MP4 com sessão válida e Range: bytes=0-99: 206 Partial Content, 100 bytes;
- telas e mídias anteriores preservadas; dados e sessão persistem após restart
  conforme checklist do operador e regras implementadas de expiração;
  recriação preserva usuários, telas e mídias. Persistência não comprova restauração.

Painel, API de telas (inclusive GET) e arquivos de mídia exigem usuário ativo
admin. API/download: 401 JSON sem sessão e 403 JSON sem papel; escrita da API
exige X-CSRF-Token. GET administrativo anônimo redireciona para login em
transporte permitido; POST administrativo anônimo retorna 401 sem executar
ação. CSRF ausente/inválido/de outra sessão retorna 403 sem alterar dados.
Somente saúde, login protegido por pré-sessão e CSS necessário são públicos;
/docs, /redoc e /openapi.json continuam desabilitados. Não há mídia pública
nem uso de cookies administrativos nas futuras TV Boxes.

Senhas: argon2-cffi==25.1.0, Argon2id m=19456 KiB, t=2, p=1, salt aleatório;
bootstrap CLI interativo, entrada oculta e confirmação, sem senha em argv,
sem conta padrão nem cadastro público. Critério: 16–128 caracteres, ao menos
três classes entre minúsculas/maiúsculas/números/símbolos. Senhas não são
aparadas ou truncadas. Usuários normalizados em ASCII, 3–64 caracteres.
Bootstrap repetido recusa sobrescrita; recuperação exige procedimento futuro
específico. Nunca executar bootstrap no banco real pelo Codex.

Tokens de cookie/sessão têm 256 bits gerados com secrets; somente SHA-256 do
identificador é persistido. CSRF de sessão fica secreto no servidor e é
entregue em campos ocultos ou GET /admin/csrf autenticado com no-store.
Pré-sessão usa hashes separados de cookie/CSRF, expira em 10min e é consumida
atomicamente no POST login; nunca é promovida a sessão autenticada.
Cookies: Secure por padrão, HttpOnly, SameSite=Lax, Path=/, sem Domain e
prefixo __Host- em HTTPS. Sessão: 8h absolutas e 30min de inatividade,
configuráveis e validadas no servidor. Apenas mutações autorizadas com sucesso
renovam atividade, a cada 5min; GETs protegidos não escrevem no banco e leituras
contínuas não renovam o prazo. Logout POST com CSRF revoga a sessão atual,
inclusive para cópia do mesmo cookie. Não revoga outras sessões da conta.

Limitação persistente em janela fixa de 15min: 5 tentativas por conta e 20
por origem, inclusive logins corretos. Usuários inexistentes/inativos/papel
insuficiente têm mensagem genérica; inexistentes também passam por Argon2id.
429 indica limite, sem detalhar conta. IP encaminhado não é lido diretamente.
Cookies, senhas, CSRF e hashes não são registrados. Corpo de login é limitado
a 8 KiB, sem reflexão de entrada; logs de acesso Uvicorn desabilitados e
erros SQL de autenticação retornam mensagem genérica sem parâmetros.

Não transmitir credenciais/cookies por http://10.4.254.202:8080. HTTP com
configuração padrão recebe 503 em login/áreas protegidas, sem emitir cookies;
saúde permanece pública. HTTPS institucional exige certificado válido e
decisão própria do operador. FORWARDED_ALLOW_IPS é vazio por padrão; só aceita
IPs explícitos de proxies TLS confiáveis, nunca '*'. O servidor usa scheme
ASGI e não interpreta X-Forwarded-Proto fornecido diretamente pelo cliente.
Nenhum proxy, certificado, binding ou .env operacional foi alterado pelo
Codex nesta atualização documental.

Exceção temporária: operador configura manualmente SIGNAGE_BIND_IP=127.0.0.1,
SIGNAGE_PORT=8080, SESSION_COOKIE_SECURE=false, LOCAL_AUTH_TEST_MODE=true e
FORWARDED_ALLOW_IPS vazio, confirma publicação efetiva apenas em loopback e
usa SSH no cliente. Configuração contraditória falha no startup; Host externo
também é recusado nesse modo. A aplicação não consegue comprovar o túnel ou
inspecionar binding do daemon; essa confirmação é obrigatória pelo operador.
Não apresentar esse modo de testes como configuração institucional.

Riscos remanescentes: transporte/TLS institucional não implantado, políticas
de acesso ainda sujeitas a revisão, ausência de MFA, recuperação administrativa
e auditoria de operações; limitação simples sujeita a bloqueio deliberado
de conta/origem, consumo de
CPU/SQLite e criação de desafios sob carga, sem quotas globais. Limpeza é
limitada a 100 registros expirados por operação; não há job de manutenção.
O backup anterior à ETAPA 007 foi confirmado pelo operador, incluindo SQLite
consistente, mídias e .env fora do repositório. Restauração conjunta formal
continua sem teste; backups contêm hashes de senha, segredos CSRF e configuração
sensível e devem ter acesso restrito.
Compatibilidade física de TV Boxes continua pendente; a identidade limitada
de dispositivo implementada na 008 está descrita no início deste documento.

## Playlists e associações — ETAPA 007

Implementadas e validadas operacionalmente pelo operador: config/build
aprovados, imagem digital-signage:etapa007 e suíte com 439 passed, 1 warning
em 515.73 segundos (8min35s), sem falhas. Warning conhecido Starlette/AnyIO;
os testes anteriores de autenticação, API, telas e biblioteca multimídia
continuam aprovados. Separadamente, os 20/20 itens manuais foram aprovados,
incluindo autenticação e CSRF das operações administrativas. Os resultados
são fornecidos pelo operador, sem execução ou reexecução pelo Codex nesta
atualização documental; [evidências](STATUS.md#validação-operacional-da-etapa-007).

Todas as novas rotas ficam sob /admin, herdando o middleware de transporte,
sessão e papel admin. O router exige require_form_csrf em todos os POSTs;
formulários incluem o token da sessão, sem criar outro mecanismo de segurança.
GET administrativo anônimo mantém 303 para login; POST anônimo 401; papel
insuficiente e CSRF inválido 403. Cookies, expiração/logout, CSP/no-store,
upload e downloads protegidos, inclusive Range, permanecem com o código anterior.

Regras são verificadas no serviço dentro de BEGIN IMMEDIATE e protegidas por
FKs, UNIQUE e CHECKs. Playlists vazias/inativas não podem ser associadas;
vínculos impedem desativação e remoção do último item. Limite de 100 itens,
duração inteira 5–600 para imagens e recusa de duração enviada para vídeo.
Erros de banco são genéricos, sem traceback ou parâmetros. Templates escapam
nomes/descrições/metadados. Não se copiam nem apagam arquivos de mídia.

O listener de conexão habilita e verifica PRAGMA foreign_keys=ON também para
as FKs de autenticação já existentes. Os testes verificam FKs em
múltiplas conexões, reconexão, transações, conflitos concorrentes, ausência de
escrita em GET/negações e controles de sessão/CSRF, com a suíte aprovada pelo
operador. Na engine implantada, o operador confirmou
`Foreign keys habilitadas: True` e as três novas tabelas. O bloqueio sudo e a
ausência de pytest pelo Codex na implementação inicial permanecem históricos
em STATUS.

Na entrega 007 não havia manifesto, player ou credenciais de dispositivos;
a implementação 008 está descrita no início deste documento. Não há
agendamento ou compartilhamento de cookies administrativos com TV Boxes.
O operador confirmou binding de teste 127.0.0.1:8080 com túnel SSH, volumes
preservados e persistência após restart/recriação. O Codex não alterou binding,
.env, volumes ou infraestrutura nem fez inspeção operacional nesta atualização.
Preservar 127.0.0.1:8080 com túnel SSH no teste local. Uso institucional amplo
continua dependendo de HTTPS válido, Secure=true, LOCAL_AUTH_TEST_MODE=false,
revisão de políticas e autenticação específica dos futuros players.
O backup anterior à implantação está registrado em OPERATIONS e STATUS;
nenhum conteúdo do backup ou .env foi acessado pelo Codex. O teste formal de
restauração conjunta, MFA, recuperação administrativa e auditoria de operações
permanecem pendentes. Player web e credenciais limitadas foram implementados
na 008, com homologação funcional local nos limites descritos acima;
integração real BTV13/H6+ permanece futura.
Esse registro histórico não comprova reprodução em TVs ou homologação da 008.

## Biblioteca de mídias — ETAPA 005

Na validação da ETAPA 005, painel, API e upload ainda não possuíam autenticação,
autorização ou CSRF. A ETAPA 006 implementou esses controles, validados pelo
operador no ambiente local com túnel SSH conforme acima; HTTPS institucional
e demais requisitos de disponibilização continuam necessários antes da liberação.
Utilizar apenas com operadores confiáveis; não expor diretamente à Internet.
O operador decidiu manter temporariamente o binding 10.4.254.202:8080 durante
os testes da ETAPA 005, como risco temporariamente aceito diante da ausência
desses controles. O binding não constitui proteção de acesso nem autorização
para liberação institucional nem transmissão de credenciais na ETAPA 006.

Controles de upload: título limitado, extensões permitidas, tamanho real em
blocos de 1 MiB, MIME derivado da validação, Pillow com limite por quadro,
quantidade de quadros e pixels acumulados, ffprobe sem shell com timeout e
saída limitada. MP4 exige H.264 yuv420p/Full HD/30 FPS e AAC opcional;
outros codecs/trilhas são recusados. Protocolos externos e referências
externas de MOV são desabilitados. Não há execução de uploads nem conversão.

SVG bruto é recusado, inclusive com mensagem explícita para .svg. SVG
renomeado como imagem ou MP4 também deve falhar na validação de conteúdo.
Sua ingestão/exibição exige nova decisão de sanitização ou rasterização segura;
nenhuma biblioteca adicional de SVG foi incorporada.

Nomes originais são somente metadados escapados pelo Jinja2. Arquivos usam
UUID no volume /app/media, temporários 0600, publicação sem sobrescrita,
rollback/limpeza em falha tratável e entrega por id do banco. A entrega
confirma confinamento do caminho e usa MIME validado, nosniff e CSP restritiva.
A aplicação permanece UID/GID 10001; volumes, healthcheck e binding anterior
são preservados. A ETAPA 006 acrescenta autenticação/autorização à entrega de
arquivos; HTTP Range continua disponível para administrador autorizado.

Limites individuais não são quota global nem controle de concorrência. O
framework recebe multipart em spool temporário antes da validação por arquivo;
uploads concorrentes, exaustão de disco e entradas malformadas ainda exigem
restrição operacional. Análise por ffprobe não garante decodificação completa
de um vídeo nem compatibilidade com uma TV Box. Queda abrupta entre arquivo
e commit pode deixar resíduos para conferência manual. Não excluir arquivos
automaticamente nesta etapa. Monitorar espaço, logs e backups consistentes.

Config/build, suíte em Docker (149 passed, 1 warning), regressão HTTP,
os 14 itens do checklist pelo navegador, Range 206/416 e persistência após
restart/force-recreate foram aprovados pelo operador, conforme docs/STATUS.md.
Esses resultados foram fornecidos pelo operador, sem reexecução nesta
atualização; não demonstram proteção administrativa ou adequação para acesso
institucional amplo. A compatibilidade com TV Boxes continua pendente.
