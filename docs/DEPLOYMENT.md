# Implantação

Execute no diretório oficial /home/administrador/digital-signage.
Docker e Docker Compose devem estar disponíveis; o usuário operacional utiliza
sudo, com autenticação realizada no próprio terminal. A configuração real usa .env não versionado, conforme .env.example.
Na ETAPA 006, antes de subir ou executar bootstrap/login, cumprir a escolha de
transporte seguro e backup da seção específica abaixo. A implementação não
modifica o .env operacional nem o binding do host.

O binding padrão é 127.0.0.1:8080, acessível somente no host. As variáveis
SIGNAGE_BIND_IP e SIGNAGE_PORT estão documentadas em .env.example. Para usar
outros valores sem criar .env, passe-os após sudo em cada comando Compose que
valida ou cria containers. Exemplo histórico do binding da ETAPA 005, sem
autorizar login/sessões em HTTP na LAN:

```bash
sudo SIGNAGE_BIND_IP=10.4.254.202 SIGNAGE_PORT=8080 docker compose config --quiet
```

Execute a inspeção, o build e os testes abaixo antes do comando up.

Antes de subir, inspecione containers, redes, volumes e a porta:

```bash
sudo docker ps -a
sudo docker network ls
sudo docker volume ls
ss -tulpn
```

Se a porta escolhida (padrão 8080) estiver ocupada ou o nome digital-signage-app já pertencer a
outro projeto, pare e reporte o conflito sem interromper outros processos.

```bash
sudo docker compose config --quiet
sudo docker compose build
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
sudo docker compose up -d --wait
sudo docker compose ps
sudo docker compose logs --tail=100 signage-app
curl --fail --noproxy '*' http://127.0.0.1:8080/
curl --fail --noproxy '*' http://127.0.0.1:8080/health
```

A imagem construída e validada da ETAPA 006 é digital-signage:etapa006,
conforme resultados fornecidos pelo operador: compose config --quiet e build
aprovados, 267 passed, 1 warning de depreciação Starlette/AnyIO em 172.98
segundos, sem falhas. O container digital-signage-app ficou healthy, com
inicialização sem erros nos logs apresentados. O binding efetivo confirmado
é 127.0.0.1:8080, com acesso administrativo por túnel SSH e sem exposição
direta do HTTP à rede institucional no ambiente validado. O operador aprovou
os 18 itens manuais. Esses resultados não foram reexecutados pelo Codex nesta
atualização documental; evidências e histórico das etapas anteriores em
[docs/STATUS.md](STATUS.md#validação-operacional-da-etapa-006).
O único serviço signage-app executa como
UID/GID 10001, com porta interna 8000 e binding configurável, por padrão
127.0.0.1:8080. Ajuste as URLs de teste ao IP e à porta escolhidos. O healthcheck usa Python
para verificar HTTP 200 e o JSON de /health. Aguarde o estado healthy.

O banco fica no volume nomeado signage-data em /app/data e os arquivos de
mídia em signage-media:/app/media. O Compose gerencia
somente a rede própria do projeto; não alterar configurações globais do Docker.

A ETAPA 002 foi validada operacionalmente com a imagem digital-signage:etapa002,
container digital-signage-app healthy e binding 10.4.254.202:8080 -> 8000/tcp.
Os dois testes passaram e GET / e GET /health retornaram HTTP 200 nesse endereço.
O registro completo dos resultados está em docs/STATUS.md.

## Persistência da ETAPA 003

DATABASE_URL é repassada pelo Compose, com padrão sqlite:////app/data/signage.db.
Configure-a no .env não versionado; para SQLite persistente, mantenha o arquivo
sob /app/data. Mudar a URL para fora desse volume elimina essa garantia.
A imagem prepara /app/data para UID/GID 10001; o volume novo herda a propriedade
no primeiro uso. Não usar chmod 777 nem executar a aplicação como root.
Volume nomeado evita depender das permissões de um bind mount ./data no host.
Rebuild, restart, recriação e down sem -v preservam o volume. Não executar down -v.
create_all cria tabelas ausentes; não é ferramenta de migração de esquema.

A ETAPA 003 foi validada pelo operador: config e build aprovados, imagem
digital-signage:etapa003, 23 passed e 1 DeprecationWarning de Starlette/AnyIO,
sem falhas. Naquela validação, o container ficou healthy em
10.4.254.202:8080 -> 8000/tcp, com
UID/GID 10001; /app/data pertence a signage:signage e signage.db foi criado
no volume signage-data. A API e os quatro ciclos de persistência foram
validados; o registro completo está em docs/STATUS.md.

Para futuras implantações ou revalidações, inspecione primeiro sudo docker
compose ps, containers, redes, volumes e binding atual. Preserve no .env o IP
e porta da implantação antes de recriar o container (127.0.0.1:8080 no
ambiente validado da ETAPA 006; 10.4.254.202:8080 é histórico da ETAPA 003).
Execute no terminal do operador:

```bash
sudo docker compose config
sudo docker compose build
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
sudo docker compose up -d
sudo docker compose ps
sudo docker compose logs --tail=100 signage-app
```

Aguarde healthy e valide também GET / e GET /health. Na ETAPA 006, testes da
API exigem sessão admin por transporte seguro e X-CSRF-Token nas escritas;
consulte docs/OPERATIONS.md. Sem sessão, a API retorna 401 JSON em transporte
permitido; em HTTP com configuração Secure padrão, retorna 503.
Use o id retornado pelo POST autenticado nas consultas GET /api/screens/{id} e PATCH
/api/screens/{id}. Verifique 201 na criação, 200 nas consultas/atualizações,
404 para id ausente, 409 para slug duplicado e 422 para slug inválido.
Exemplo de atualização: PATCH com {"active":false}, seguido de GET.
Consulte docs/OPERATIONS.md para repetir a verificação de persistência real,
já concluída com sucesso nesta etapa.

## Implantação da biblioteca — ETAPA 005

ETAPA 005 implantada e validada com sucesso pelo operador. Os 14 itens do
checklist pelo navegador, imagens e vídeos MP4 H.264 reais, metadados,
Range 206/416, regressão e persistência após restart/force-recreate foram
aprovados. TV Piloto e TV do Pátio foram preservadas. O bloqueio sudo da
implementação inicial permanece apenas como histórico em docs/STATUS.md;
os resultados operacionais foram fornecidos pelo operador.

O operador decidiu manter temporariamente 10.4.254.202:8080 durante os testes
da ETAPA 005, como risco temporariamente aceito. Naquela etapa, painel, API
e upload não possuíam autenticação, autorização ou CSRF: esse binding não é proteção de acesso
nem autorização para liberação institucional. Os controles são obrigatórios
na ETAPA 006, antes dessa liberação; não expor à Internet.

Antes desta implantação, o operador criou o backup local do SQLite anterior
à ETAPA 005 em /home/administrador/signage-backups/signage-before-005.db.
Esse arquivo não comprova backup conjunto de banco e mídias nem restauração.
Para futuras implantações, após construir a imagem e antes de recriar o
serviço, faça backup consistente dos dois volumes conforme docs/OPERATIONS.md.
Preserve signage-data e DATABASE_URL. A imagem prepara /app/media para
UID/GID 10001; o volume novo signage-media recebe essas
permissões no primeiro uso. Não alterar volumes existentes ou usar chmod 777.
O startup cria media_assets sem modificar screens. Os limites configuráveis
e o perfil MP4 estão em README.md e .env.example; confira também espaço
disponível antes dos uploads.

Para futuras implantações ou revalidações, execute as inspeções e os comandos
Docker acima no terminal do operador, confira healthy/logs, regressão e o
checklist em docs/OPERATIONS.md. Registre novos resultados em docs/STATUS.md.
Não instalar Pillow/FFmpeg no host para testar. A compatibilidade com TV Boxes
continua pendente. A ETAPA 006 foi implementada e validada operacionalmente
pelo operador no ambiente local com túnel SSH, conforme abaixo.

## Implantação administrativa — ETAPA 006

Validação concluída pelo operador com SIGNAGE_BIND_IP=127.0.0.1,
SIGNAGE_PORT=8080, SESSION_COOKIE_SECURE=false e LOCAL_AUTH_TEST_MODE=true.
O primeiro administrador foi criado com sucesso pelo operador; login/logout,
CSRF, cookies, Range autenticado e persistência foram aprovados. Essa
configuração é temporária e exclusiva de testes locais por túnel SSH.
Não há liberação para uso institucional amplo. Antes dessa disponibilização,
permanecem HTTPS com certificado válido, SESSION_COOKIE_SECURE=true,
LOCAL_AUTH_TEST_MODE=false, revisão das políticas de acesso e definição de
autenticação específica para os futuros players. Na validação da ETAPA 006,
backup/restauração conjunta ainda não tinham confirmação; o backup anterior
à ETAPA 007 foi posteriormente criado, conforme abaixo. Restauração formal,
MFA, recuperação administrativa e auditoria de operações permanecem futuros.

Os procedimentos abaixo são mantidos para futuras implantações e revalidações.
Não enviar credenciais/cookies por http://10.4.254.202:8080. O operador deve
decidir e aplicar o transporte antes do bootstrap/login e do deploy da etapa:

- Institucional: HTTPS com certificado válido, SESSION_COOKIE_SECURE=true,
  LOCAL_AUTH_TEST_MODE=false. Se houver ponto TLS confiável previamente
  autorizado, configurar FORWARDED_ALLOW_IPS somente com seus IPs exatos.
  A configuração/instalação de TLS e proxy pertence a procedimento próprio;
  não foi realizada nesta etapa. Vazio significa nenhum proxy confiável.
- Teste temporário isolado: editar manualmente .env para SIGNAGE_BIND_IP=127.0.0.1,
  SIGNAGE_PORT=8080, SESSION_COOKIE_SECURE=false, LOCAL_AUTH_TEST_MODE=true,
  FORWARDED_ALLOW_IPS vazio; acessar exclusivamente por túnel SSH no cliente.
  Não tratar como configuração institucional. Não usar IP da LAN ou 0.0.0.0
  nesse modo, nem alterar SSH/firewall para viabilizá-lo.

Inspecione primeiro containers, redes, volumes e ports existentes; preserve
signage-data, signage-media e DATABASE_URL. Faça backup conjunto consistente
conforme docs/OPERATIONS.md antes da recriação e da criação de tabelas novas.
O backup SQLite anterior à ETAPA 005 não substitui esse backup da implantação.

No terminal do operador, no diretório oficial:

```bash
sudo docker compose config --quiet
sudo docker compose build
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
# Somente com testes aprovados, backup e transporte seguro selecionado:
sudo docker compose up -d --wait
sudo docker compose ps
sudo docker compose logs --tail=100 signage-app
```

Compose config valida sintaxe/interpolação, não comprova isolamento/TLS.
Antes do login, conferir ports efetivos em compose ps/inspect e porta no host
com ss. No teste local, confirmar exatamente 127.0.0.1:8080 -> 8000/tcp, sem
publicação em IP da LAN ou 0.0.0.0. O Compose repassa a mesma SIGNAGE_BIND_IP
à aplicação; não há inspeção automática do daemon ou comprovação do túnel.
Configuração insegura/contraditória é recusada antes da criação de tabelas.
Em Secure=true com acesso HTTP, login e áreas protegidas retornam 503 sem
cookies; /health continua 200. Não interpretar healthy como autenticação/TLS
validados. Não confiar em X-Forwarded-Proto sem origem de proxy autorizada.

No computador do operador, para a opção local isolada:

```powershell
ssh -N -L 18080:127.0.0.1:8080 administrador@10.4.254.202
```

Use http://127.0.0.1:18080/admin/login no navegador desse computador. O HTTP
local atravessa o túnel; não substituir a URL pelo IP da LAN. Na opção
institucional, usar a URL HTTPS válida definida pelo operador.

Após essas verificações e a aprovação da suíte, o operador cria o primeiro
administrador, sem senha em argumento, no terminal do servidor:

```bash
sudo docker compose exec -it signage-app python -m app.scripts.bootstrap_admin
```

O primeiro administrador já foi criado pelo operador na validação registrada;
o Codex não executou esse comando no banco real. Não há usuário padrão no
startup. Repetição encerra com mensagem clara e não sobrescreve contas.
Para futuras revalidações, repita o checklist de docs/OPERATIONS.md, incluindo
cookies, CSRF, logout, regras de expiração, Range autorizado, usuário/dados
após restart/recriação e preservação de TV Piloto, TV do Pátio e mídias
anteriores. Registre novos resultados, quantidade de testes, falhas e warnings
em docs/STATUS.md. Não instalar dependências no host nem contornar sudo.

## Implantação de playlists — ETAPA 007

ETAPA 007 implementada e validada operacionalmente pelo operador. Config e
build aprovados; imagem construída `digital-signage:etapa007`. O operador
executou `sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider`:
**439 passed, 1 warning em 515.73 segundos (8min35s)**, sem falhas. Warning
conhecido de depreciação Starlette/AnyIO; autenticação, API, telas e biblioteca
multimídia anteriores continuam aprovadas. Separadamente, 20/20 itens manuais
aprovados. O bloqueio sudo do Codex na implementação inicial permanece como
histórico em STATUS; nenhum desses testes ou procedimentos foi reexecutado
pelo Codex nesta atualização documental.

O container digital-signage-app executa a imagem etapa007, com serviço único
signage-app, binding de teste 127.0.0.1:8080, acesso por túnel SSH e volumes
preservados. Restart retornou healthy e force-recreate foi executado, com
persistência de playlists, itens e associações após ambos os ciclos. O operador
confirmou `Foreign keys habilitadas: True` na engine implantada e as tabelas
playlists, playlist_items e screen_playlist_assignments.

Backup anterior à implantação criado pelo operador em
`/home/administrador/signage-backups/before-007-20261015-145745`, com SQLite
consistente por API de backup, arquivos de mídia e configuração .env fora do
repositório. O Codex não acessou o backup ou seus conteúdos. O teste formal de
restauração conjunta continua pendente.

Sem novas dependências ou volumes. Dockerfile, UID/GID 10001, serviço
signage-app, healthcheck, portas e configuração de binding foram preservados;
.dockerignore inclui os novos templates. O esquema adiciona apenas playlists,
playlist_items e screen_playlist_assignments via create_all. PRAGMA
foreign_keys=ON passa a ser habilitado/verificado em cada conexão SQLite;
isso não altera registros ou recria tabelas existentes.

Para futuras implantações ou revalidações, depois de revisar o diff e
providenciar backup consistente apropriado de signage-data e signage-media,
inspecione o ambiente Docker e execute no terminal do operador, no diretório
oficial, preservando .env e nome do projeto:

```bash
cd /home/administrador/digital-signage
sudo docker compose config --quiet
sudo docker compose build
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
# Executar up somente se build e pytest forem aprovados e houver backup:
sudo docker compose up -d
sudo docker compose ps
sudo docker compose logs --tail=100 signage-app
```

Não executar up se build ou pytest falharem. Não executar down -v, remover
volumes, alterar binding ou repetir bootstrap administrativo. Confirmar
healthy, logs e binding efetivo 127.0.0.1:8080 nas futuras revalidações; o
binding foi confirmado pelo operador, sem reinspeção do Codex aqui. Usar o túnel
SSH já documentado, sem enviar credenciais/cookies em HTTP na LAN.

Para futuras revalidações, conferir FKs com o comando de OPERATIONS e repetir
os 20 itens já aprovados do
[checklist](OPERATIONS.md#checklist-manual-confirmado-pelo-operador--etapa-007),
incluindo CSRF/autorização, ordenação, uma playlist por tela,
compartilhamento, recusas de negócio, regressão e persistência após restart e
recriação sem apagar volumes. Registrar saída real do pytest, duração,
falhas/warnings e novas evidências operacionais em STATUS. O resultado real da
ETAPA 007 é 439 passed; os 267 da ETAPA 006 permanecem históricos.

Nenhuma reprodução em TV Box pode ser alegada: player, credenciais de
dispositivos e agendamento não foram implementados. Sem liberação
institucional ampla; permanecem HTTPS válido, Secure=true,
LOCAL_AUTH_TEST_MODE=false, revisão de políticas e autenticação futura
específica e limitada dos dispositivos. Player web, integração/validação real
com BTV13 e H6+, restauração conjunta formal, auditoria e recuperação
administrativa permanecem futuros. Nenhuma ETAPA 008 iniciada aqui.
