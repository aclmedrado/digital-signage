# Segurança

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
Backup conjunto e restauração continuam sem confirmação; backups agora
contêm hashes de senha e segredos CSRF e devem ter acesso restrito.
Compatibilidade e autorização específica de TV Boxes continuam pendentes.

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
