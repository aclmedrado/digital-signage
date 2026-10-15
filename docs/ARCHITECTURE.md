# Arquitetura

## Visão geral

O Digital Signage será composto inicialmente por dois elementos principais:

1. servidor central;
2. players instalados em TV Boxes.

## Servidor

Responsável por:

- interface administrativa;
- API;
- banco de dados;
- gerenciamento de mídia;
- programação das telas.

A aplicação é definida para execução através de Docker e Docker Compose.

## Implementação da ETAPA 002

FastAPI em app/main.py atende somente GET / e GET /health em JSON, via
Uvicorn na porta interna 8000. O único serviço Compose é signage-app, com
container digital-signage-app e publicação configurável por SIGNAGE_BIND_IP e
SIGNAGE_PORT, com padrão 127.0.0.1:8080 (somente acesso local no host).
O IP da implantação não é fixado no Compose nem no código Python.

A imagem usa Python 3.12 slim e usuário não-root (UID/GID 10001). O healthcheck
consulta /health usando a biblioteca padrão Python. Na ETAPA 002 não havia banco ou volumes. Não há montagens do host
ou outros serviços. A configuração usa a rede própria do
Compose e restart unless-stopped. Os testes pytest são executados na imagem.

Build, dois testes em container e implantação foram validados operacionalmente.
Na ETAPA 002, o container ficou healthy, com binding histórico
10.4.254.202:8080 para a porta interna 8000 e ambos os endpoints retornando
HTTP 200, conforme docs/STATUS.md. O ambiente validado da ETAPA 006 usa
127.0.0.1:8080 com túnel SSH, conforme seção específica abaixo.
O player continua previsto para o MVP. A biblioteca de mídias é implementada
na ETAPA 005, conforme seção específica abaixo.


## Implementação da ETAPA 003

SQLite acessado por SQLAlchemy 2.x, configurado por DATABASE_URL, com padrão
sqlite:////app/data/signage.db. O volume nomeado signage-data do Compose é
montado em /app/data. A imagem prepara apenas esse diretório com propriedade
UID/GID 10001; o volume novo recebe esse conteúdo e suas permissões no primeiro
uso. A aplicação permanece não-root, sem tornar /app gravável.

Screen contém id inteiro gerado, name e location obrigatórios, slug obrigatório
único com formato ^[a-z0-9]+(?:-[a-z0-9]+)*$, active booleano com padrão true e
timestamps created_at/updated_at gerados pelo servidor em UTC. Strings têm
limite de 200 caracteres. active expressa habilitação administrativa.
SQLite armazena os timestamps em UTC sem offset; a API os devolve com offset UTC.

POST e GET /api/screens criam/listam; GET e PATCH /api/screens/{screen_id}
consultam/atualizam. Listagem ordenada por id; ausentes retornam 404, conflitos
de slug 409 e validação 422. PATCH aceita somente name, slug, location e active;
campos nulos e campos adicionais são rejeitados. Não há exclusão de telas.

O lifespan cria tabelas com metadata.create_all de forma idempotente, sem
apagar dados ou migrar esquemas existentes. SQLite usa check_same_thread=False;
cada requisição recebe sessão fechada ao final, com rollback em conflito.
Testes usam SQLite em arquivo temporário, substituindo engine de inicialização
e dependência de sessão para não tocar o banco de produção.
Não há Alembic. Alterações futuras de esquema exigirão decisão específica.
A ETAPA 003 foi concluída e validada operacionalmente pelo operador: 23 testes
aprovados, container healthy em 10.4.254.202:8080 e usuário efetivo UID/GID 10001.
A propriedade signage:signage de /app/data e a criação de signage.db foram
confirmadas. O registro id=1 persistiu após restart, recriação, down/up sem -v
e rebuild; created_at e updated_at foram preservados após rebuild/recriação.
Os resultados completos estão em docs/STATUS.md.

## Implementação da ETAPA 004

A interface administrativa é renderizada no servidor com FastAPI e Jinja2,
conforme ADR 0004, no mesmo serviço signage-app. As rotas ficam em
app/routes/admin/screens.py; os templates em app/templates usam base.html
para compartilhar cabeçalho e navegação. StaticFiles atende o CSS local em
/static/admin.css. Não há JavaScript, CDN, frontend separado ou novo serviço.

GET /admin redireciona para /admin/screens. A listagem é ordenada por id;
GET /admin/screens/new exibe criação e GET /admin/screens/{screen_id}/edit
exibe edição. POST /admin/screens cria uma tela ativa;
POST /admin/screens/{screen_id}/edit altera name, slug e location, preservando
active. POST /admin/screens/{screen_id}/toggle alterna active separadamente.
Não há exclusão. Operações bem-sucedidas retornam 303 para /admin/screens,
com parâmetro result para uma mensagem de confirmação escolhida de uma lista
fixa. O GET seguinte evita reenvio de formulário ao atualizar a página.

API e interface compartilham Screen, ScreenCreate, ScreenUpdate, get_session
e funções simples em app/services/screens.py para busca, listagem, criação,
atualização e commit com rollback em conflito. Não há chamadas HTTP internas
nem framework de serviços. updated_at continua gerado no servidor em UTC.
Os erros de validação são apresentados em HTML com status 422 e preservação
dos valores; slug duplicado retorna o formulário em HTML com status 409.
Telas ausentes nas rotas administrativas retornam página HTML com status 404.
O pattern do formulário é obtido do schema existente, sem uma segunda regra
de slug. Jinja2 mantém o escape automático dos valores nos templates HTML.

As rotas JSON existentes, /health e seu healthcheck foram preservados.
SQLite, DATABASE_URL, esquema, volume signage-data e usuário não-root não
mudaram. Jinja2 e python-multipart são instalados somente na imagem; o
.dockerignore inclui os templates e o CSS no contexto de build. A imagem
dessa etapa era digital-signage:etapa004; digital-signage:etapa006 foi
construída e validada operacionalmente pelo operador. A imagem atual
digital-signage:etapa007 também foi construída e validada operacionalmente
pelo operador, conforme registro da ETAPA 007 abaixo.

Na ETAPA 004 não havia autenticação ou autorização na interface nem na API.
O uso naquela fase era restrito ao ambiente interno controlado, sem exposição
direta à Internet. Os testes
administrativos reutilizam o banco temporário isolado dos testes existentes.
A ETAPA 004 foi concluída e validada operacionalmente, conforme resultados
fornecidos pelo operador: build aprovado, imagem digital-signage:etapa004,
66 testes aprovados, container healthy em 10.4.254.202:8080 e oito testes
pelo navegador aprovados. GET /, /health e /api/screens retornaram HTTP 200,
e TV Piloto permaneceu no SQLite. Resultados completos em docs/STATUS.md;
essas validações não foram reexecutadas nesta atualização documental.

## Implementação da ETAPA 005

Conforme ADR 0005, `MediaAsset` em `media_assets` unifica vídeos e imagens.
Campos: id, title (1–200 caracteres), kind (video/image), original_filename
(até 255 caracteres, somente exibição), stored_filename (UUID único),
mime_type validado, size_bytes positivo, width/height positivos,
duration_seconds, video_codec, audio_codec e created_at UTC. Metadados
adicionais: frame_rate para vídeos e frame_count para imagens. Restrições
CHECK vinculam os metadados ao tipo. O modelo Screen permanece intacto.
`metadata.create_all` cria somente a nova tabela ausente no próximo startup;
não há Alembic, migração destrutiva ou alteração dos registros existentes.

Rotas HTML em `app/routes/admin/media.py`: GET /admin/media (ordenado por id),
GET /admin/media/new e POST /admin/media. Templates Jinja2 compartilham
base.html, navegação e CSS local responsivo. UploadFile é lido em blocos
de 1 MiB, com tamanho real, ignorando MIME/Content-Length do cliente.
Título é validado e aparado; o nome original nunca determina caminhos.
Erros esperados retornam formulário HTML (422, 413, 500 ou 503) e sucesso
usa 303 para o catálogo. Falhas de estrutura dos campos do upload recebem
HTML 422, sem alterar o tratamento JSON da API de telas.

`app/services/media.py` recebe o arquivo em `.upload-*.tmp` dentro de
/app/media, com permissão 0600, valida e publica como UUID + extensão.
A publicação usa hard link exclusivo seguido de remoção do temporário:
operação no mesmo volume, sem copiar nem sobrescrever um nome existente.
Commit com falha faz rollback e remove o novo arquivo definitivo; finally
limpa os temporários. A integridade entre filesystem e SQLite é compensada
para falhas tratáveis, não uma transação distribuída: encerramento abrupto
do processo pode exigir conferência manual de arquivos órfãos antes de
qualquer remoção. Não há rotina automática de exclusão de mídias.

MP4 exige contêiner MP4 (marca validada, não MOV renomeado), uma trilha H.264
yuv420p de 8 bits, até 1920 × 1080, taxas média/nominal até 30 FPS, duração
finita positiva e AAC opcional. Outras trilhas são rejeitadas. ffprobe usa
argumentos em lista, shell=False, somente protocolo file e demuxer mov,
referências externas desabilitadas, timeout configurável (15 s), um thread,
sondagem limitada e teto conjunto de 64 KiB para stdout/stderr. Percorre
pacotes, rejeita stderr/retorno com erro e metadados/JSON inválidos; a
estrutura de boxes tem limite de 10.000 e detecta truncamentos declarados.
Não há transcodificação nem garantia de decodificação de todos os frames;
a reprodução no navegador foi confirmada pelo operador; a compatibilidade
com TV Boxes continua pendente de validação específica.

Pillow==12.3.0 verifica conteúdo e decodifica cada quadro de JPEG, PNG,
WebP e GIF, exigindo correspondência com a extensão. Limites configuráveis:
MAX_VIDEO_UPLOAD_MB=250 e MAX_IMAGE_UPLOAD_MB=10 (MiB de 1024 × 1024 bytes),
MAX_IMAGE_PIXELS=20000000 por quadro, MAX_IMAGE_FRAMES=100 e
MAX_IMAGE_TOTAL_PIXELS=100000000 por arquivo. A análise evita n_frames sem
limite e rejeita avisos de decompression bomb. GIF/WebP animados são
armazenados sem conversão. PNG animado também segue os limites por quadro.
SVG bruto é explicitamente rejeitado até nova decisão de tratamento seguro.

GET /media/{media_id}/file fica em router separado: resolve o registro e
valida caminho UUID confinado ao diretório, recusando links para fora.
FileResponse envia MIME validado, Content-Disposition inline com nome
interno, nosniff e CSP restritiva. Mantém HTTP Range: 206 para bytes=0-99,
416 para intervalo fora do arquivo e 400 para sintaxe inválida, conforme
Starlette. O catálogo usa img lazy e video controls muted preload=metadata,
sem autoplay nem carregamento integral de todos os vídeos.

Um único serviço signage-app, imagem digital-signage:etapa005. O volume
signage-data:/app/data permanece; adiciona-se signage-media:/app/media,
preparado no build para UID/GID 10001, sem chmod 777 ou bind mounts.
O pacote Debian ffmpeg (--no-install-recommends) fornece ffprobe e FFmpeg
para vídeos sintéticos dos testes; nenhum componente é instalado no host.
Binding, healthcheck, usuário e serviço existentes foram preservados.

Testes usam override de sessão/engine e MediaSettings com diretório
temporário. Os 149 testes (66 anteriores e 83 novos) foram executados e
aprovados pelo operador em 18.60 segundos, com 1 warning de depreciação
Starlette/AnyIO e nenhuma falha. A ETAPA 005 está concluída e validada
operacionalmente: config/build, container healthy, inicialização sem erros
nos logs apresentados, regressão HTTP, os 14 itens do checklist pelo navegador,
Range 206/416 e persistência após restart/force-recreate confirmados.
O volume SQLite existente foi preservado, signage-media foi criado e
/app/data e /app/media pertencem a signage:signage, com UID/GID 10001.
Esses resultados foram fornecidos pelo operador, sem reexecução nesta
atualização; registro completo em docs/STATUS.md.

O operador manteve temporariamente o binding 10.4.254.202:8080 durante os
testes como risco temporariamente aceito. O binding não protege o acesso
nem autoriza liberação institucional. Autenticação, autorização e CSRF
foram implementados e validados pelo operador na ETAPA 006 em ambiente local,
conforme abaixo; transporte institucional seguro permanece necessário antes
dessa liberação. A decisão de binding da ETAPA 005
não permite transmitir credenciais/cookies em HTTP da LAN na ETAPA 006.

Referências consultadas: [Pillow/PyPI](https://pypi.org/project/pillow/),
[Pillow verify/load](https://pillow.readthedocs.io/en/stable/reference/Image.html),
[ffprobe](https://ffmpeg.org/ffprobe.html),
[FileResponse](https://starlette.dev/responses/) e
[pacote Debian](https://packages.debian.org/trixie/amd64/ffmpeg/filelist).

## Implementação da ETAPA 006

Conforme ADR 0006, `users`, `auth_sessions`, `login_challenges` e `login_limits`
são tabelas adicionais criadas idempotentemente por `create_all`. Modelos e
dados de Screen/MediaAsset permanecem preservados. User possui username único
normalizado (trim/lowercase, ASCII, 3–64 caracteres), hash Argon2id, papel
admin/viewer, active e timestamps UTC. Não há usuário padrão no startup.

`app/services/auth.py` usa argon2-cffi==25.1.0, Argon2id m=19456 KiB, t=2,
p=1, salt de 16 bytes e hash de 32 bytes. O perfil atende ao mínimo do ADR/OWASP
com consumo de memória limitado por verificação. Usuário inexistente também
passa por verificação Argon2id com hash fictício mantido somente em memória.
Bootstrap interativo em `app/scripts/bootstrap_admin.py` valida senha de
16–128 caracteres e três classes, solicita confirmação oculta e serializa a
criação com BEGIN IMMEDIATE; nunca sobrescreve usuário ou cria segundo admin.

Pré-sessão de login: cookie e CSRF independentes, cada um com 256 bits, hashes
SHA-256 no SQLite e validade de 10min. POST login consome o desafio de forma
atômica, inclusive em falha de senha; após sucesso emite sessão totalmente
nova. O corpo urlencoded do login tem teto de 8 KiB e três campos únicos;
erros não refletem credenciais. Sessão armazena somente hash do identificador
opaco, user_id, CSRF secreto, criação, atividade, expiração absoluta e revoked.
Logout POST com CSRF revoga a sessão no banco e remove cookies.

`app/security.py` aplica middleware ASGI a todos os caminhos administrativos,
à API de telas e à entrega de mídias, antes de ler corpos protegidos. Consultas
de autenticação usam Session sobre o mesmo engine configurado em app.state;
as rotas funcionais continuam usando get_session. Apenas usuário ativo admin
é autorizado. CSRF da API é validado antes de ler JSON; CSRF HTML é conferido
por dependência compartilhada antes dos serviços de telas/upload/logout.
Formulários incluem campo oculto; GET /admin/csrf fornece o token somente à
sessão admin autorizada, em JSON sem cache e sem CORS permissivo.

GETs protegidos e acessos negados não escrevem no SQLite nem nas mídias.
GET /admin/login cria apenas o desafio temporário exigido para login CSRF.
Somente mutações autorizadas bem-sucedidas renovam last_activity_at, com
intervalo mínimo de 5min. Leituras contínuas não renovam inatividade e exigem
novo login após 30min desde a última atividade persistida. Expiração absoluta
de 8h nunca é estendida. Relógio é injetável nos testes; sessões revogadas,
expiradas, desconhecidas ou de usuários inativos não autorizam requisições.

Tentativas de login são limitadas de forma persistente a 5 por conta e 20 por
origem em janela fixa de 15min, inclusive credenciais válidas; limite retorna
429 com mensagem genérica. BEGIN IMMEDIATE reserva tentativas antes de Argon2,
sem manter lock durante a verificação. Origem usa request.client, sem ler
X-Forwarded-For diretamente. Limpezas expurgam até 100 registros expirados por
operação, sem rotina global de exclusão. Sessões apenas inativas/revogadas
podem permanecer até expiração absoluta e login posterior para limpeza.

Configuração validada antes de create_all. Secure=true é padrão e exige scheme
HTTPS reconhecido pelo servidor. FORWARDED_ALLOW_IPS vazio na imagem/Compose
desabilita confiança em headers encaminhados; IPs específicos de um ponto TLS
confiável somente após decisão do operador, nunca '*'. Modo local exige
Secure=false, LOCAL_AUTH_TEST_MODE=true, declaração de binding 127.0.0.1:8080,
nenhum proxy confiável e Host localhost/127.0.0.1. A aplicação não inspeciona
publicação de portas no daemon; Compose usa a mesma variável para ports e
ambiente e o operador deve confirmar o binding efetivo e o túnel SSH.

Cookies HTTPS: __Host-signage-session e __Host-signage-login; modo local:
signage-local-session e signage-local-login. HttpOnly, SameSite=Lax, Path=/,
sem Domain. Páginas sensíveis, JSON protegido e arquivos têm no-store;
HTML recebe CSP compatível com img/video/CSS local, sem scripts/frames.
CSP e nosniff do FileResponse são preservados. Uvicorn usa --no-access-log
para evitar registrar URLs com entradas sensíveis; erros SQL de autenticação
têm resposta genérica sem traceback/parâmetros. Não há credenciais em URLs.

Serviço único, UID/GID 10001, volumes, binding, healthcheck e endpoints base
preservados; imagem digital-signage:etapa006 construída e validada pelo
operador. Os 149 casos anteriores foram preservados e os novos testes usam
banco/mídias temporários, login real, CSRF e HTTPS simulado no TestClient.
A suíte em container teve 267 passed, 1 warning de depreciação Starlette/AnyIO
em 172.98 segundos, sem falhas. Config/build, estado healthy e inicialização
sem erros nos logs apresentados também foram confirmados pelo operador.

O operador criou o primeiro administrador e aprovou os 18 itens manuais,
incluindo login/logout, proteção das rotas, CSRF 403, cookies,
Range autenticado 206 com 100 bytes e persistência. O binding efetivo é
127.0.0.1:8080, com acesso por túnel SSH e sem exposição direta de HTTP à rede
institucional. Configuração temporária: SIGNAGE_BIND_IP=127.0.0.1,
SIGNAGE_PORT=8080, SESSION_COOKIE_SECURE=false e LOCAL_AUTH_TEST_MODE=true;
cookies observados com HttpOnly habilitado, SameSite=Lax e Secure desabilitado.
Esses resultados foram fornecidos pelo operador; o Codex não os reexecutou
nesta atualização documental. O bloqueio sudo inicial permanece como histórico
em [STATUS](STATUS.md#validação-operacional-da-etapa-006).

A conclusão operacional se restringe a esse teste local. Antes de uso
institucional amplo: HTTPS com certificado válido, SESSION_COOKIE_SECURE=true,
LOCAL_AUTH_TEST_MODE=false, revisão das políticas de acesso e definição da
autenticação específica dos futuros players das TV Boxes. Na validação da
ETAPA 006, backup/restauração conjunta ainda não tinham confirmação; o backup
anterior à ETAPA 007 foi posteriormente informado, conforme abaixo. Restauração
formal, MFA, recuperação administrativa e auditoria de operações permanecem
trabalhos futuros. Não há player nesta etapa.

Referências: [argon2-cffi](https://pypi.org/project/argon2-cffi/25.1.0/),
[API Argon2](https://argon2-cffi.readthedocs.io/en/stable/api.html),
[OWASP senhas](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html),
[OWASP login CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
e [Uvicorn](https://www.uvicorn.org/settings/).

## Implementação da ETAPA 007

Conforme ADR 0007, adicionam-se três tabelas, sem alterar Screen, MediaAsset
ou o contrato JSON da API de telas:

- `playlists`: id inteiro; name obrigatório, aparado, de 1–200 caracteres,
  sem unicidade; description opcional até 1000 caracteres; active com padrão
  true; created_at/updated_at UTC. CHECKs de comprimento no SQLite.
- `playlist_items`: id próprio; FKs obrigatórias para playlist e mídia,
  indexadas; position inteiro positivo; UNIQUE(playlist_id, position);
  duration_seconds NULL ou inteiro de 5–600; created_at UTC. CHECKs usam
  typeof para impedir posições e durações fracionárias no SQLite.
- `screen_playlist_assignments`: screen_id é PK e FK para screens, garantindo
  no máximo um vínculo por tela; playlist_id é FK indexada, sem unicidade;
  assigned_at/updated_at UTC. Trocar a playlist preserva assigned_at e
  Screen.active; desvincular remove somente essa linha.

Os novos modelos são importados pelos serviços/routers antes do create_all
existente no lifespan, que cria apenas tabelas ausentes, sem migração destrutiva.
make_engine agora registra PRAGMA foreign_keys=ON no evento connect e verifica
se o valor é 1 em cada conexão. Na implementação inicial, a engine anterior
não configurava esse PRAGMA e o SQLite temporário do host retornou 0, sem
medição da engine implantada pelo Codex. Posteriormente, o operador confirmou
na engine implantada `Foreign keys habilitadas: True` e identificou as tabelas
`playlists`, `playlist_items` e `screen_playlist_assignments`.

app/services/playlists.py concentra regras e transações. BEGIN IMMEDIATE
adquire a reserva de escrita SQLite antes de validar estado, contar itens ou
ler vínculos, serializando também associação versus remoção/desativação.
Commit é único por operação; erros fazem rollback. IntegrityError e
OperationalError retornam conflito compreensível (409); outros erros
SQLAlchemy retornam indisponibilidade genérica (503), sem parâmetros SQL.
Não há locks externos. Erros de campos são 422, ausentes são 404.

Itens entram no final, até 100 incluindo repetições. Para imagens, a duração
vazia/ausente usa 15 segundos e só aceita inteiros 5–600; vídeos persistem NULL
e recusam qualquer campo de duração enviado. A validação depende do kind da
mídia carregada dentro da transação. Não há cópia ou transformação de arquivos.
O swap usa posição auxiliar max(position)+1 e três flushes; a remoção faz
flush do DELETE e compacta sucessores em ordem crescente, com um flush por
item para respeitar UNIQUE inclusive durante a operação. Sucessos mantêm
posições 1..N; os limites de subir/descer não modificam os dados.

Playlist vazia pode ser criada/editada; somente ativa e não vazia pode ser
associada. Uma playlist associada não pode ser desativada nem perder seu
último item. Editar nome/descrição, adicionar e reordenar permanecem possíveis
quando inativa ou associada. A mesma mídia pode se repetir; várias telas podem
compartilhar uma playlist. Não há exclusão de playlists ou mídias nesta etapa.

app/routes/admin/playlists.py acrescenta catálogo, criação, edição, detalhe,
toggle, adição/remoção/subir/descer e associação/desassociação na tela, sob
/admin. Templates novos usam base.html e CSS local. A inclusão tem formulários
separados para imagem e vídeo, sem JavaScript e sem duração editável para vídeo.
Erros esperados são HTML com valores preservados; sucesso usa POST → 303 → GET.
A lista de telas mostra playlist atual ou Sem playlist e link de gerenciamento.
Todos os GETs funcionais são de leitura; todos os POSTs usam require_form_csrf
e o middleware existente exige usuário ativo admin antes de ler corpos.
Os handlers que leem formulários assincronamente executam mutações no threadpool.

Na implementação, Compose mudou apenas a tag para digital-signage:etapa007 e
.dockerignore incluiu o diretório dos templates, sem novas dependências,
serviços, volumes ou mudança de binding/usuário/healthcheck pelo Codex.
O operador construiu e implantou a imagem no container digital-signage-app,
preservando o serviço único signage-app, SQLite/mídias e o binding de teste
127.0.0.1:8080 com túnel SSH. Restart retornou healthy; force-recreate foi
executado, com persistência de playlists, itens e associações confirmada
após ambos os ciclos. Não há player, manifesto, API de dispositivos,
credenciais de TV Boxes ou agendamento. As associações são somente
configuração central; não comprovam reprodução em TV.

Há 39 novas funções de teste com parametrizações em tests/test_playlists.py.
A expectativa de tabelas no teste anterior de autenticação foi ampliada para
as três novas tabelas, preservando a comparação dos dados anteriores.
A implementação inicial teve apenas verificações estáticas e controles locais
limitados pelo Codex, devido ao bloqueio sudo preservado no histórico.
Posteriormente, o operador aprovou config/build e executou a suíte completa:
**439 passed, 1 warning em 515.73 segundos (8min35s)**, sem falhas. Warning
conhecido de depreciação Starlette/AnyIO; autenticação, API, telas e biblioteca
multimídia anteriores continuam aprovadas. Separadamente, confirmou os
**20/20 itens manuais** de configuração e associação, incluindo regras de
negócio, autenticação/CSRF e persistência. A ETAPA 007 está implementada e
validada operacionalmente pelo operador no ambiente local com túnel SSH.

Antes da implantação, o operador criou
`/home/administrador/signage-backups/before-007-20261015-145745`, com SQLite
consistente por API de backup, arquivos de mídia e .env fora do repositório.
O teste formal de restauração conjunta permanece pendente. O Codex apenas
registrou esses resultados, sem reexecutar testes ou operações e sem acessar
backup, credenciais, sessões ou banco real nesta atualização documental.
Evidências em [STATUS](STATUS.md#validação-operacional-da-etapa-007).

Player web, integração/validação real com BTV13 e H6+ e autenticação específica
e limitada dos dispositivos permanecem futuros. HTTPS institucional é
necessário antes de disponibilizar o painel na rede; auditoria, recuperação
administrativa e demais controles documentados permanecem pendentes.
Nenhuma ETAPA 008 iniciada; não há declaração de TVs reproduzindo playlists.

## TV Box

Responsável somente pela reprodução do conteúdo.

A TV Box deverá executar Chromium ou navegador compatível em modo kiosk.

O player deverá acessar uma URL fornecida pelo servidor.

Exemplo futuro:

http://SERVIDOR/player/recepcao

## Princípio arquitetural

A TV Box deve permanecer simples.

Regras de negócio, armazenamento e gerenciamento devem ficar no servidor.

## Persistência

Dados persistentes:

- banco;
- imagens;
- vídeos.

Eles devem sobreviver à reconstrução ou substituição de containers.

## MVP

Fluxo pretendido:

Administrador
    |
    v
Painel Web
    |
    v
FastAPI
    |
    +---- SQLite
    |
    +---- Media
    |
    v
Player Web
    |
    v
Chromium kiosk
    |
    v
TV
