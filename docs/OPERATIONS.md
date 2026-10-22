# Operações

## Homologação funcional — ETAPA 008

Player e pareamento implementados, com build, regressão completa, implantação
e homologação funcional real no navegador confirmados pelo operador no
ambiente HTTP local por túnel SSH. Suíte em container executada pelo operador:
**555 passed, 1 warning de depreciação Starlette/AnyIO em 821.67 segundos,
zero falhas**, com o comando
`sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider`.
O caso corrigido `test_invalid_device_cookie_denies_every_request[hash]` e
as cinco parametrizações passaram nas execuções separadas do operador.
Histórico da falha inicial e resultados finais em
[STATUS](STATUS.md#validação-operacional-da-etapa-008).

Imagem `digital-signage:etapa008`, container `digital-signage-app` healthy
após recriação, GET `/health` HTTP 200, logs de inicialização sem erros,
binding exclusivo `127.0.0.1:8080`, acesso via túnel SSH, FKs iguais a 1 e
quatro tabelas de pareamento/dispositivos confirmados pelo operador.
Backup pré-implantação: `/home/administrador/signage-backups/before-008-20261016-171852`,
com SQLite consistente, mídias e `.env` fora do repositório; restauração
conjunta formal ainda pendente.

O Codex havia executado separadamente 13 testes JS com DOM/relógio simulados;
não são homologação de navegador real. Nesta atualização documental não
reexecutou testes ou operações do operador, nem acessou banco real,
credenciais, cookies ou `.env`. A matriz abaixo distingue evidências manuais,
Python e JS simulado; não se declara 24/24 manuais.

Para futuras revalidações, seguir
[DEPLOYMENT](DEPLOYMENT.md#etapa-008--implantação-confirmada-pelo-operador),
preservando .env/portas/volumes. Não instalar dependências no host nem
contornar sudo. Node já disponível foi usado apenas na lógica isolada;
a aplicação não passa a depender de Node.
Nunca transmitir códigos/cookies em HTTP na LAN. No computador do operador:

```bash
ssh -N -L 18080:127.0.0.1:8080 administrador@10.4.254.202
```

Perfil A: `http://localhost:18080/admin/login`; abrir **Telas → Player /
Pareamento** da tela desejada. Preparar playlist com imagem e MP4 reais.
Gerar código (10 min, uso único) e digitá-lo no perfil B, separado, em
`http://localhost:18080/device/activate`. Usar sempre localhost nesses perfis;
não alternar com IP da LAN. O perfil B não precisa de conta administrativa.
Para simular outra TV simultaneamente, usar um terceiro perfil separado:
há um único cookie de dispositivo por perfil/origem e uma sessão por tela.

O código aparece somente na resposta POST; o link **Consultar estado sem
código** volta ao GET. Reenviar POST gera outro código. Reemissão não derruba
o dispositivo atual; consumo do novo código o substitui. Revogação exige a
opção explícita de confirmação e remove também código pendente. Estado da
sessão e validade são exibidos, sem recuperar código/token. Prévia usa o
perfil A e sua sessão administrativa (sujeita a inatividade normal); não
emite cookie de dispositivo.

Player usa contain, fundo escuro e F11 manual opcional. Vídeos são mudos e
terminam por ended; imagens usam a duração por item. Polling de 20–22 s mais
latência, sem sobreposição; atualização normal aguarda transição. Estado neutro
ou recusa 401/403/404 limpa a mídia ao receber a resposta. Falhas de rede
limpam o conteúdo e usam backoff até 120 s + até 2 s de jitter. Erro de mídia
pula após 2 s; sequência inteira falhando espera 20 s. Sem cache offline.
Tela inativa conserva sessão para manifesto neutro e pode retomar ao reativar,
sem liberar mídia enquanto inativa. Sessão expira em 90 dias absolutos.

### Checklist oficial 008 — 24 itens

Os critérios originais são preservados abaixo. A situação de cada item e de
seus subcenários está na matriz seguinte; esta lista não declara aprovação
manual integral.

1. Login e telas/mídias/playlists anteriores intactos.
2. Área de pareamento da TV Piloto e TV do Pátio acessível ao administrador.
3. Emissão com CSRF; código não reaparece ao abrir GET.
4. Reemissão invalida código anterior sem desconectar dispositivo válido.
5. Página pública de ativação em perfil separado.
6. Código correto ativa TV Piloto e redireciona ao player.
7. Reuso/código incorreto recusados genericamente.
8. Cookie persistente HttpOnly/Lax/Path=/, Secure coerente com o teste local.
9. Dispositivo não acessa painel, API ou mídia administrativa.
10. Perfil Piloto não abre página, manifesto ou mídia do Pátio, mesmo compartilhando playlist.
11. Prévia admin sem cookie de dispositivo.
12. Imagem pelo tempo configurado, incluindo repetição com duração própria.
13. MP4 real inicia mudo, termina integralmente e avança.
14. Último item volta ao primeiro.
15. Mudança de ordem/duração aplicada na transição.
16. Troca da playlist aplicada sem interromper vídeo saudável.
17. Tela inativa/sem playlist exibe estado neutro, sem mídia exposta.
18. Range com cookie do dispositivo retorna 206/100 bytes; fora do arquivo, 416.
19. Arquivo ausente, autoplay recusado e sequência defeituosa não produzem loop rápido; desconexão/retorno recuperam manifesto atual.
20. Revogação interrompe na próxima verificação; outra TV não é afetada.
21. Novo pareamento substitui sessão antiga; expiração de código de 10 min (testes automatizados com relógio são aceitáveis).
22. Restart e force-recreate preservam pareamento válido e todos os dados anteriores.
23. Janela estreita/F11, aba em segundo plano e retorno sem timers/listeners duplicados.
24. Binding continua 127.0.0.1:8080 e acesso exclusivamente por túnel SSH, sem HTTP na LAN.

### Evidências por item do checklist 008

**M**: teste/observação manual confirmado pelo operador nesta homologação.
**P**: cobertura Python inspecionada nos testes existentes, cuja suíte
completa foi executada pelo operador (555 aprovados), sem reexecução pelo
Codex. **J**: lógica automatizada executada anteriormente pelo Codex nos
13 testes com DOM/fetch/relógio simulados. P/J não comprovam resultado em
navegador real. Não foram fornecidas saídas manuais individuais para todos
os subcenários. A informação geral de que os complementares tiveram os
resultados esperados não elimina as confirmações específicas abaixo.

| Item | Origem e situação | Evidência e alcance / confirmação remanescente |
|---|---|---|
| 1 | P; M parcial | Fluxos administrativos utilizados na homologação; regressão completa de login/telas/mídias/playlists aprovada em Python. Sem registro manual individual de toda a regressão anterior. |
| 2 | M no fluxo; P | Pareamento da TV Piloto e operação com as duas TVs confirmados. Autorização/acesso à área administrativa cobertos em Python; abertura das duas áreas sem relato manual individual. |
| 3 | P; manual a confirmar | Emissão com CSRF e código ausente no GET cobertos em Python. Falta confirmação manual específica dessas duas verificações. |
| 4 | M + P | Reemissão e invalidação do código anterior confirmadas no navegador. Preservação da sessão válida até consumir o novo código coberta em Python, sem relato manual específico desse intervalo. |
| 5 | M no fluxo; P | Ativação real confirmada pelo pareamento. Acesso público sem sessão administrativa coberto em Python; uso de perfil separado sem registro manual individual. |
| 6 | M + P | TV Piloto pareada e playlist reproduzida. Redirecionamento coberto em Python; não se atribui código HTTP manual. |
| 7 | M + P | Código inválido recusado no navegador. Reuso e resposta genérica cobertos em Python, sem confirmação manual específica de reuso. |
| 8 | P; manual a confirmar | Persistência e atributos do cookie cobertos em Python nos modos HTTPS simulado e HTTP local. Falta inspeção manual identificada de HttpOnly/Lax/Path=/ e Secure do cookie de dispositivo. |
| 9 | M + P | Bloqueio administrativo do dispositivo confirmado. Painel, API e mídia administrativa individualizados em Python; sem saídas HTTP manuais atribuídas. |
| 10 | M + P | Página, manifesto e mídia da outra TV inacessíveis, conforme operador. Compartilhamento da mesma playlist coberto em Python; sem confirmação manual específica dessa condição. |
| 11 | M + P | Prévia administrativa sem emissão de cookie de dispositivo confirmada pelo operador e coberta em Python. |
| 12 | M + P/J | Imagens temporizadas e mesma imagem repetida com durações diferentes confirmadas no navegador. |
| 13 | M + J | MP4 real mudo, integral e avanço confirmados no navegador; lógica de `ended` também simulada. |
| 14 | M + J | Loop contínuo confirmado no navegador; retorno ao primeiro item também simulado. |
| 15 | M + P/J | Ordem/duração atualizadas sem atualização manual da página. Revisão e aplicação na transição cobertas em Python/JS simulado. |
| 16 | M + J | Substituição de playlist na transição após o vídeo confirmada no navegador e coberta em JS simulado. |
| 17 | M + P/J | Tela inativa/sem playlist com estado neutro confirmada no navegador. Ausência de URLs/acesso à mídia em estado neutro coberta em Python. |
| 18 | P; manual a confirmar | Range 206 com 100 bytes e fora do arquivo 416 cobertos em Python no endpoint do player. Não há saída manual identificada com cookie do dispositivo; resultados administrativos de etapas anteriores não a substituem. |
| 19 | M parcial + P/J | Interrupção de rede e recuperação confirmadas no navegador. Arquivo ausente coberto em Python; autoplay recusado, sequência defeituosa e prevenção de loop rápido em JS com falhas artificiais. Não se declaram esses últimos como testes manuais. |
| 20 | M + P/J | Revogação sem afetar outra TV e novo pareamento após revogação confirmados. Interrupção na próxima verificação coberta em JS/recusa em Python; sem tempo manual medido. |
| 21 | M + P | Novo pareamento invalidou a sessão antiga no navegador. Expiração do código em 10 minutos verificada em Python com relógio simulado, aceito pelo critério; não houve espera manual declarada. |
| 22 | M + P | Persistência após restart e force-recreate confirmada pelo operador. Preservação dos dados anteriores também coberta em Python isolado, sem inventário manual detalhado informado. |
| 23 | M + J | Janela estreita, F11, segundo plano e retorno sem duplicação aparente de timers/requisições confirmados. Limpeza de listeners/timers e ausência de sobreposição verificadas na simulação JS; sem contagem instrumental manual informada. |
| 24 | M operacional | Binding exclusivo `127.0.0.1:8080` e acesso pelo navegador somente via túnel SSH confirmados pelo operador. |

Rastreabilidade da cobertura automatizada existente, sem nova execução:

- Em [tests/test_device_auth.py](../tests/test_device_auth.py):
  `test_pairing_posts_require_admin_and_csrf`,
  `test_code_entropy_hash_and_one_response_only`,
  `test_admin_pairing_get_requires_admin_without_writes`,
  `test_valid_activation_hash_cookie_and_single_use`,
  `test_local_cookie_and_no_http_lan_exception`,
  `test_invalid_codes_are_generic_without_reflection`,
  `test_reissue_keeps_old_session_until_consumption`,
  `test_unusable_code_cannot_create_session` (expiração com relógio simulado)
  e `test_revoke_needs_confirmation_and_only_affects_target`.
- Em [tests/test_player.py](../tests/test_player.py):
  `test_same_shared_playlist_does_not_authorize_other_screen`,
  `test_device_cookie_never_authorizes_admin`,
  `test_admin_preview_does_not_pair_or_refresh_session`,
  `test_neutral_states_never_expose_media`,
  `test_range_revalidated_and_admin_download_stays_private`,
  `test_media_guard_denies_noncurrent_or_missing_media`,
  `test_absolute_expiry_not_renewed_and_persists_between_apps` e
  `test_incremental_schema_preserves_all_previous_data`.
- Em [tests/player_state.test.js](../tests/player_state.test.js): duração após
  load, vídeo até ended, loop/repetição, revisão na transição, recusa de
  autorização, estados neutros, sequência defeituosa, play rejeitado/listeners
  antigos, rede/recuperação e polling/pagehide. São simulações de lógica.

Permanecem confirmações manuais específicas dos itens 3, 8 e 18 e os detalhes
sem relato individual indicados nos itens compostos. Não há nova falha
funcional relatada pelo operador. Sem HTTPS institucional, integração física
BTV13/H6+, Chromium kiosk, restauração conjunta formal ou armazenamento offline
de mídias. Revogação não elimina bytes já transferidos. A homologação local
não libera uso institucional amplo e não conclui nem inicia a ETAPA 009.

### Procedimentos para futuras revalidações da 008

Para confirmar manualmente Range, usar DevTools do perfil B ou cookie jar
privado fora do Git, sem publicar cookies/códigos. Exemplo no computador do operador, substituindo
MEDIA_ID por um MP4 da playlist atual com pelo menos 100 bytes:

```bash
curl --cookie /CAMINHO/PROTEGIDO/device-cookies.txt --noproxy '*' -D - -o /dev/null -H 'Range: bytes=0-99' http://localhost:18080/player/s/tv-piloto/media/MEDIA_ID
```

Após autorização e inspeção dos dados de teste pelo operador, validar os
ciclos abaixo e aguardar healthy/conferir logs em cada ciclo:

```bash
sudo docker compose restart signage-app
sudo docker compose ps
sudo docker compose logs --tail=100 signage-app
# Conferir os dois perfis e os dados antes do próximo ciclo:
sudo docker compose up -d --force-recreate signage-app
sudo docker compose ps
sudo docker compose logs --tail=100 signage-app
```

Registrar novas evidências dos itens e suas origens, resultado/duração real
do pytest e warnings em STATUS, sem segredos. Os resultados já informados
constam acima; comandos desta seção são referências para futuras revalidações,
sem execução pelo Codex neste fechamento. Restauração conjunta segue pendente.
Não inferir BTV13/H6+, kiosk, HTTPS ou autorização para publicação na LAN.
Teste opcional da lógica JS, somente se Node já estiver disponível no ambiente
de desenvolvimento: `node tests/player_state.test.js`. Usa DOM simulado;
não substitui os itens manuais de reprodução. Nenhuma dependência JS é instalada.

As seções seguintes preservam o histórico/procedimentos das etapas anteriores.

Execute em /home/administrador/digital-signage, utilizando sudo no terminal.

Estado e logs:

```bash
sudo docker compose ps
sudo docker compose logs
sudo docker compose logs -f
```

Reiniciar, parar e iniciar o serviço do projeto:

```bash
sudo docker compose restart
sudo docker compose stop
sudo docker compose start
```

Após iniciar ou reiniciar, confira o estado healthy em compose ps e os logs.
O healthcheck executa a cada 30 segundos; considera três falhas consecutivas,
com timeout de cinco segundos e tolerância inicial de dez segundos.
O restart unless-stopped reinicia o processo se ele sair; um estado unhealthy
isoladamente não dispara reinício automático.

Validação HTTP e testes sem dependências no host:

```bash
curl --fail --noproxy '*' http://127.0.0.1:8080/
curl --fail --noproxy '*' http://127.0.0.1:8080/health
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
```

As URLs usam o binding padrão 127.0.0.1:8080, acessível somente no host.
Ajuste-as conforme SIGNAGE_BIND_IP e SIGNAGE_PORT da implantação. start e
restart mantêm o binding do container existente; para alterar o binding,
execute compose up -d --wait com as variáveis, conforme docs/DEPLOYMENT.md.

Consulte docs/DEPLOYMENT.md para build e primeira inicialização.
Para a ETAPA 006, cumprir primeiro transporte seguro, testes e backup conforme
a seção administrativa abaixo. Não transmitir login/cookies em HTTP da LAN.

O comando pytest desabilita o cache para evitar PytestCacheWarning por falta de
permissão de escrita em /app/.pytest_cache pelo usuário não-root. Na validação
operacional da ETAPA 002, esse warning não afetou os dois testes aprovados.
Não alterar permissões de /app para resolver o warning.

## Interface administrativa de telas — ETAPA 004

ETAPA 004 concluída e validada operacionalmente, conforme resultados
fornecidos pelo operador: config e build aprovados, imagem
digital-signage:etapa004, container digital-signage-app healthy em
10.4.254.202:8080 e logs de inicialização sem erros. Os resultados não foram
reexecutados nesta atualização documental; registro completo em docs/STATUS.md.
Para futuras implantações ou revalidações, siga os procedimentos de inspeção,
build e testes de docs/DEPLOYMENT.md, preservando o binding, o volume e a
configuração existente. Não contornar bloqueios de sudo nem alterar permissões.

Acesse /admin e /admin/screens somente pela URL HTTPS válida selecionada
pelo operador ou via http://127.0.0.1:18080 no teste local com túnel SSH e
binding 127.0.0.1:8080 confirmado, conforme docs/DEPLOYMENT.md.

Ajuste IP e porta conforme a implantação. O painel permite listar, cadastrar,
editar, ativar e desativar telas; não há exclusão. Cadastro e edição solicitam
nome, slug e localização. Novas telas ficam ativas; ativação e desativação
são ações separadas na listagem. Sucesso redireciona por HTTP 303 para a
listagem com uma mensagem; erros mantêm os valores no formulário HTML.

Na ETAPA 004, painel e API não possuíam autenticação/autorização. A ETAPA 006
implementa a política de acesso descrita abaixo, validada operacionalmente
pelo operador no ambiente local com túnel SSH. A disponibilização institucional
continua condicionada aos requisitos descritos na seção administrativa.

Comandos para futuras implantações ou revalidações, no terminal do operador:

```bash
sudo docker compose config
sudo docker compose build
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
sudo docker compose up -d
sudo docker compose ps
sudo docker compose logs --tail=100 signage-app
```

A suíte de 66 testes (23 existentes e 43 administrativos) passou na validação
do operador: 66 passed, 3 warnings, sem falhas. Dois warnings de cache do
pytest decorreram de erro de digitação no argumento utilizado; um
DeprecationWarning veio de Starlette/AnyIO. Para futuras execuções, use
exatamente o comando pytest acima, com -p no:cacheprovider, sem alterar
permissões. Os testes usam SQLite temporário isolado do banco real.

O operador confirmou HTTP 200 em GET /, /health e /api/screens, preservação
de TV Piloto no SQLite e aprovação dos oito testes pelo navegador: painel
com TV Piloto, formulário de nova tela, cadastro com slug diferente, edição
de nome e localização, ativação/desativação, mensagem de slug duplicado,
refresh sem duplicação e legibilidade em computador e tablet/janela estreita.

Para futuras revalidações, aguarde healthy, confira endpoints e logs e repita
o fluxo pelo navegador. Confira também erros de formulário, CSS local e
preservação dos valores preenchidos. Registre novos resultados em docs/STATUS.md.

## Banco SQLite e persistência

O banco configurado por DATABASE_URL reside, por padrão, no volume signage-data
em /app/data/signage.db. Não editar SQLite manualmente como rotina.
Não remover esse volume nem executar docker compose down -v.
Os testes automatizados usam banco temporário isolado, mesmo quando o volume
de produção está montado no container de testes.

A persistência da ETAPA 003 foi validada pelo operador com a tela TV Piloto
(id=1, slug=tv-piloto): o registro permaneceu disponível após restart,
recriação, down/up sem -v e rebuild seguido de recriação. Após o último ciclo,
o container voltou healthy e os mesmos created_at e updated_at foram
preservados. Resultados completos em docs/STATUS.md.

Para repetir a verificação na ETAPA 006, use sessão admin e CSRF na API por
transporte seguro, crie uma tela e anote o id retornado.
Consulte GET /api/screens/{id}, execute sudo docker compose restart signage-app,
aguarde healthy e repita a consulta, comparando os dados. Depois execute sudo
docker compose up -d --force-recreate signage-app, aguarde healthy e consulte
novamente. Para validar rebuild, execute sudo docker compose build seguido de
sudo docker compose up -d e repita a consulta. Para validar down/up, execute
sudo docker compose down (sem -v), sudo docker compose up -d, aguarde healthy
e consulte o mesmo id. Confira os logs após cada ciclo.
Mantenha a mesma configuração .env e o mesmo nome de projeto nesses comandos.
Registre os resultados de futuras revalidações.

## Biblioteca de mídias — ETAPA 005

ETAPA 005 concluída e validada operacionalmente, conforme resultados fornecidos
pelo operador: config/build aprovados, imagem digital-signage:etapa005,
container digital-signage-app healthy em 10.4.254.202:8080 e inicialização
normal, sem erros nos logs apresentados. Volume SQLite existente preservado,
signage-media criado e /app/data e /app/media pertencentes a signage:signage;
aplicação executando como UID/GID 10001. Os resultados não foram reexecutados
nesta atualização documental; registro completo em docs/STATUS.md.
Use /admin/media para catálogo e /admin/media/new para upload com
título. MP4/H.264 yuv420p, até Full HD/30 FPS, AAC opcional; JPEG, PNG,
WebP e GIF. SVG é rejeitado até tratamento seguro. Sem transcodificação,
exclusão ou player TV Box. Playlists/associações foram implementadas na
ETAPA 007 e validadas operacionalmente pelo operador, conforme abaixo.

Limites padrão ajustáveis em .env.example: 250 MiB/vídeo, 10 MiB/imagem,
20 milhões de pixels/quadro, 100 quadros/imagem e 100 milhões de pixels
acumulados. MiB usa 1024 × 1024 bytes. ffprobe tem timeout de 15 segundos
e saída limitada a 64 KiB. Imagens animadas permanecem no formato original.
O envio usa o spool temporário do framework antes da leitura incremental
para /app/media; o teto por arquivo é aplicado na leitura real, não pelo
Content-Length. Isso não constitui controle global de quota ou concorrência.
Monitore também o espaço temporário do container, além do volume de mídias.

O armazenamento permanente é signage-media:/app/media; metadados ficam
em signage-data:/app/data/signage.db. Temporários .upload-*.tmp são limpos
em sucesso/falha e falha no banco remove o novo arquivo final. Em queda
abrupta ou falta de permissão durante a limpeza, pode haver resíduo: conferir
logs e comparar com metadados antes de qualquer intervenção manual. Não
automatizar remoção nem editar registros reais como rotina nesta etapa.

Na ETAPA 005, autenticação, autorização e proteção CSRF estavam ausentes.
Foram implementadas e validadas pelo operador na ETAPA 006 em teste local com
túnel SSH; HTTPS institucional e os demais requisitos abaixo continuam
necessários antes da liberação institucional. Testar somente
com operadores confiáveis em ambiente restrito; não expor à Internet.
O operador decidiu manter temporariamente 10.4.254.202:8080 durante os testes,
como risco temporariamente aceito na ETAPA 005. Esse binding não constitui
proteção de acesso nem autorização para liberação institucional, nem permite
transmitir credenciais/cookies em HTTP da LAN na ETAPA 006.
Não alterar firewall, SSH, sudoers, grupos, Docker global ou permissões
para contornar bloqueios de sudo. O .env real e as portas foram preservados
pelo Codex na implementação da ETAPA 005; o binding validado da ETAPA 006 está
registrado na seção administrativa abaixo.

Comandos para futuras implantações ou revalidações, no terminal do operador,
após inspeção e backup:

```bash
sudo docker compose config --quiet
sudo docker compose build
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
sudo docker compose up -d
sudo docker compose ps
sudo docker compose logs --tail=100 signage-app
```

A suíte foi executada pelo operador com o comando pytest acima:
149 passed, 1 warning, em 18.60 segundos, sem falhas. O warning é de
depreciação Starlette/AnyIO. A cobertura inclui regressão, imagens,
animações, vídeos reais sintéticos H.264/AAC e sem áudio, Range, limites,
erros ffprobe, path traversal e rollback. As fixtures substituem engine,
sessão e diretório de mídia por áreas temporárias, mesmo com os volumes
montados no container de teste. FFmpeg gera vídeos pequenos temporários.
O bloqueio sudo da implementação inicial é histórico; os testes operacionais
foram executados pelo operador, sem reexecução nesta atualização documental.

### Checklist pelo navegador e futuras revalidações

Os 14 itens foram aprovados pelo operador. Para futuras revalidações:

1. Confirmar o funcionamento do catálogo em /admin/media.
2. Conferir o formulário de upload em /admin/media/new.
3. Cadastrar imagens válidas.
4. Cadastrar MP4 H.264 reais.
5. Conferir dimensões, duração e codecs nos metadados.
6. Pré-visualizar imagens.
7. Reproduzir vídeos no navegador.
8. Confirmar aceitação de WebP/GIF.
9. Conferir rejeição de arquivos inválidos.
10. Conferir rejeição explícita de SVG.
11. Confirmar o painel de telas e a preservação de TV Piloto e TV do Pátio.
12. Confirmar persistência após restart de signage-app.
13. Confirmar persistência após force-recreate, sem remover volumes.
14. Conferir a responsividade da interface.

Conforme evidências do operador, vídeos MP4 H.264 reais e uma imagem WebP
foram cadastrados e pré-visualizados. Range válido (HTTP 206) e intervalo
fora do arquivo (HTTP 416) também foram aprovados. Nas futuras revalidações,
confira adicionalmente UID/GID, permissões e espaço em disco nos dois volumes.

Para Range na ETAPA 006, use sessão admin válida. No computador do operador,
somente na opção de teste local com SSH, use cookie jar privado fora do Git,
sem divulgar seu conteúdo, e substitua 1 pelo id real de um MP4 com mais de
100 bytes (na opção institucional, substitua pela URL HTTPS válida):

```bash
curl --cookie /CAMINHO/PROTEGIDO/cookies.txt --noproxy '*' -D - -o /dev/null -H 'Range: bytes=0-99' http://127.0.0.1:18080/media/1/file
```

As verificações de serviço/armazenamento são no terminal do servidor:

```bash
sudo docker compose restart signage-app
sudo docker compose up -d --force-recreate signage-app
sudo docker compose exec signage-app id
sudo docker compose exec signage-app ls -ld /app/data /app/media
sudo docker compose exec signage-app df -h /app/data /app/media /tmp
```

Esperar 206, Accept-Ranges: bytes, Content-Range: bytes 0-99/TAMANHO e
Content-Length: 100. A suíte verifica também o corpo de 100 bytes.
Intervalo fora do arquivo retorna 416 e Content-Range: */TAMANHO;
sintaxe inválida retorna 400 pelo FileResponse de Starlette.
Após cada ciclo, aguardar healthy, consultar telas, catálogo/arquivos e logs.
Registrar os resultados reais; a compatibilidade com TV Box continua pendente
de etapa específica. Nunca usar down -v nem limpeza global Docker.

### Backup básico consistente dos dois volumes

Antes da implantação da ETAPA 005, o operador criou o backup local do SQLite
anterior à etapa em /home/administrador/signage-backups/signage-before-005.db.
O backup pré-implantação informado foi realizado; ele não equivale a backup
conjunto de SQLite e mídias da ETAPA 005 nem confirma restauração.

Antes da implantação da ETAPA 007, o operador criou:

`/home/administrador/signage-backups/before-007-20261015-145745`

Foram copiados o banco SQLite consistente por meio da API de backup, os
arquivos de mídia e a configuração .env, armazenada fora do repositório.
Essa evidência resolve a pendência de criação do backup anterior à implantação.
**O backup não foi submetido a teste formal de restauração conjunta**; essa
pendência permanece. O Codex não acessou esse diretório ou seus conteúdos,
credenciais, sessões ou banco real nesta atualização documental. O procedimento
genérico abaixo permanece para backups futuros; não é atribuído ao operador
como o comando usado para produzir esse backup.

Antes da implantação da ETAPA 008, o operador confirmou novo backup em
`/home/administrador/signage-backups/before-008-20261016-171852`, com SQLite
consistente, mídias e `.env` fora do repositório. Não foram informados os
comandos usados; nenhum conteúdo foi acessado pelo Codex. O ensaio formal de
restauração conjunta permanece pendente também para esse backup.

Procedimento para futuros backups consistentes, não executado nesta atualização.
No diretório oficial, inspecione o espaço disponível e reserve uma janela
sem uploads. A imagem
da etapa alvo (atualmente etapa008) deve estar construída antes de
usar compose run abaixo; build não
recria o serviço em produção. Pare apenas
signage-app, confira compose ps e gere um arquivo fora dos volumes, mantendo
o mesmo nome de projeto e .env. O comando Python abaixo não importa a
aplicação e não inicializa tabelas. Use um nome novo para cada backup, sem
sobrescrever um backup existente:

```bash
mkdir -p backups
sudo docker compose stop signage-app
sudo docker compose ps
sudo docker compose run --rm --no-deps -T signage-app python -c 'import sys, tarfile; archive = tarfile.open(fileobj=sys.stdout.buffer, mode="w|"); archive.add("/app/data", arcname="data"); archive.add("/app/media", arcname="media"); archive.close()' > backups/signage-YYYYMMDD-HHMMSS.tar
tar -tf backups/signage-YYYYMMDD-HHMMSS.tar
sudo docker compose start signage-app
sudo docker compose ps
sudo docker compose logs --tail=100 signage-app
```

Substitua YYYYMMDD-HHMMSS pela data/hora real. Confira exit code, tamanho
do arquivo e presença de data/signage.db e media antes de considerar o
backup válido. O tar deve conter o banco (e eventuais sidecars) e todas as
mídias da mesma janela sem escrita. Arquivos .tar já são ignorados pelo Git.
Proteja o acesso ao backup e mantenha cópia externa conforme política local;
um arquivo no mesmo disco não protege contra perda do servidor.
Uma restauração deve ser ensaiada em volumes isolados autorizados, preservando
UID/GID 10001 e verificando catálogo, arquivos e telas. Não restaurar sobre
produção sem plano e autorização específicos nem remover os volumes atuais.

## Administração autenticada — ETAPA 006

Etapa concluída e validada operacionalmente pelo operador no ambiente local
com túnel SSH. Evidências fornecidas pelo operador nesta solicitação e
registradas em 2026-10-15; o Codex não executou nem reexecutou comandos Docker,
pytest, bootstrap, requisições HTTP ou testes pelo navegador nesta atualização
documental. O bloqueio sudo da implementação inicial permanece como histórico
em [STATUS](STATUS.md#registro-da-etapa-006).

### Resultados operacionais e automatizados fornecidos pelo operador

- `sudo docker compose config --quiet`: aprovado;
- `sudo docker compose build`: aprovado; imagem digital-signage:etapa006;
- container digital-signage-app healthy; inicialização sem erros nos logs
  apresentados;
- binding efetivo 127.0.0.1:8080; acesso administrativo por túnel SSH,
  sem exposição direta do HTTP à rede institucional no ambiente validado;
- primeiro administrador criado com sucesso pelo operador;
- comando automatizado executado pelo operador:
  `sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider`;
  resultado: **267 passed, 1 warning, 172.98 segundos**, nenhuma falha.
  Warning de depreciação Starlette/AnyIO; todos os testes anteriores aprovados.

A configuração temporária confirmada utiliza SIGNAGE_BIND_IP=127.0.0.1,
SIGNAGE_PORT=8080, SESSION_COOKIE_SECURE=false e LOCAL_AUTH_TEST_MODE=true.
Destina-se exclusivamente a testes locais por túnel SSH e não libera uso
institucional amplo. Antes dessa disponibilização: HTTPS com certificado
válido, SESSION_COOKIE_SECURE=true, LOCAL_AUTH_TEST_MODE=false, revisão das
políticas de acesso e definição de autenticação específica dos futuros players
das TV Boxes. MFA, recuperação administrativa e auditoria de operações são
trabalhos futuros. Na validação da ETAPA 006 ainda não havia confirmação de
backup/restauração conjunta; o backup anterior à ETAPA 007 foi posteriormente
confirmado, conforme seção acima. Restauração formal permanece pendente.

### Procedimentos para futuras implantações e revalidações

Executar a sequência de docs/DEPLOYMENT.md no terminal do operador. Não fazer
login/bootstrap em rede HTTP sem TLS. Nunca alterar .env/binding, host ou
privilégios automaticamente para testar.

O primeiro administrador já foi criado na validação. Procedimento de bootstrap
para uma nova implantação, após testes, backup e escolha de transporte seguro:

```bash
sudo docker compose exec -it signage-app python -m app.scripts.bootstrap_admin
```

Exige terminal interativo, username ASCII normalizado (3–64 caracteres) e
senha oculta com confirmação (16–128 caracteres, três classes entre letras
minúsculas/maiúsculas/números/símbolos). Não aceita argumentos. Repetição,
usuário existente ou administrador já criado são recusados sem sobrescrita.
Não existe cadastro público, senha inicial padrão ou recuperação pelo navegador.
O Codex não deve executar esse bootstrap no banco de produção.

Login usa pré-sessão de 10min e CSRF oculto; senha incorreta tem mensagem
genérica. Após sucesso, nova sessão admin libera telas/mídias. Sair é POST
com CSRF e revoga somente a sessão atual. GETs protegidos não escrevem no
banco; somente mutações autorizadas bem-sucedidas renovam atividade, com
intervalo mínimo de 5min. Leituras contínuas não renovam inatividade: relogar
após 30min desde a última atividade persistida. Expiração absoluta é 8h,
sem extensão. Tentativas: 5/conta e 20/origem em janela fixa de 15min,
inclusive logins corretos; ao receber 429, aguardar expiração da janela.

Cliente da API deve autenticar-se pelo mesmo fluxo de login/pre-sessão em
transporte seguro, manter o cookie e consultar GET /admin/csrf autenticado.
O JSON no-store contém o token para X-CSRF-Token em POST/PATCH /api/screens.
Nunca transportar cookie ou token em query string, links ou logs. Proteger
cookie jars fora do Git; não incluir senha em comandos de operação.
HTML usa campo oculto em criação/edição/toggle, upload e logout. API/download
sem sessão: 401 JSON; papel insuficiente: 403 JSON; CSRF inválido: 403 sem
mutação. Em HTTP com Secure=true, administração/login são bloqueados com 503.
Não tratar essa recusa de transporte como regressão dos endpoints de saúde.

### Checklist manual confirmado pelo operador

Os 18 itens abaixo foram aprovados pelo operador e podem ser repetidos em
futuras revalidações. São evidências manuais, distintas da suíte pytest:

1. Página de login acessível sem autenticação: aprovado.
2. Login correto: aprovado.
3. Senha incorreta recusada: aprovado.
4. Painel de telas protegido: aprovado.
5. Painel de mídias protegido: aprovado.
6. API de telas sem sessão retorna 401: aprovado.
7. Download de mídia sem sessão retorna 401: aprovado.
8. Administrador autenticado consegue editar telas: aprovado.
9. Administrador autenticado consegue cadastrar mídia: aprovado.
10. Escrita na API sem token CSRF retorna 403: aprovado.
11. Logout encerra a sessão: aprovado.
12. Acesso após logout exige login novamente: aprovado.
13. Cookies conferidos no navegador: aprovado.
14. HTTP Range de MP4 com sessão válida: aprovado.
15. TV Piloto, TV do Pátio e mídias anteriores preservadas: aprovado.
16. Dados e sessão persistem após restart, respeitando as regras implementadas
    de expiração: aprovado conforme checklist do operador.
17. Recriação do container preserva usuários, telas e mídias: aprovado.
18. Interface utilizável em computador e janela estreita: aprovado.

### Resultados manuais complementares de autenticação e segurança

| Verificação do operador | Resultado real |
|---|---|
| GET /health | HTTP 200 |
| GET /admin/screens sem sessão | HTTP 303 para /admin/login |
| GET /api/screens sem sessão | HTTP 401 |
| GET /media/1/file sem sessão | HTTP 401 |
| Escrita autenticada sem X-CSRF-Token (item 10) | HTTP 403; proteção CSRF confirmada |
| Cookies no HTTP local (item 13) | HttpOnly habilitado; SameSite=Lax; Secure desabilitado conforme configuração temporária; transporte de rede por túnel SSH |
| MP4 autenticado com Range: bytes=0-99 (item 14) | HTTP 206 Partial Content; 100 bytes recebidos |

O item 16 registra a confirmação do checklist do operador, sem acrescentar
medições individuais de timeout. A confirmação manual de Range nesta etapa
é a de 206 com 100 bytes; Range 416/400 integra a cobertura automatizada
descrita em STATUS, sem nova atribuição de teste manual.

Evidências consolidadas em
[STATUS](STATUS.md#validação-operacional-da-etapa-006). O checklist anterior
incluía backup/recuperação como verificação operacional: não houve evidência
de execução de backup conjunto ou ensaio de restauração nesta validação.
Persistência após restart/recriação não comprova restauração. Backups de
SQLite contêm hashes de senha e CSRF; restringir acesso, proteger cópias e
ensaiar restauração conjunta em ambiente isolado autorizado. O procedimento
acima permanece disponível para execução futura; não foi executado pelo Codex.

## Playlists e associação às telas — ETAPA 007

Etapa implementada e validada operacionalmente pelo operador no ambiente de
testes com binding 127.0.0.1:8080 e acesso administrativo por túnel SSH.
Resultados fornecidos pelo operador neste fechamento, sem execução ou
reexecução de comandos Docker, pytest, consultas SQLite ou testes pelo navegador
pelo Codex nesta atualização documental. O bloqueio sudo da implementação
inicial permanece no histórico de [STATUS](STATUS.md#registro-da-etapa-007).

Resultados automatizados e de infraestrutura confirmados pelo operador:

- `sudo docker compose config --quiet`: aprovado;
- `sudo docker compose build`: aprovado; imagem `digital-signage:etapa007`;
- `sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider`:
  **439 passed, 1 warning em 515.73 segundos (8min35s)**, nenhuma falha;
  warning conhecido de depreciação Starlette/AnyIO;
- testes anteriores de autenticação, API, telas e biblioteca multimídia
  continuam aprovados;
- serviço único signage-app e container digital-signage-app executando etapa007;
- binding de teste, túnel SSH e volumes SQLite/mídia preservados;
- restart com retorno ao estado healthy e force-recreate executados;
  playlists, itens e associações persistiram após ambos os ciclos.

URLs administrativas, usando o mesmo acesso local por túnel SSH:

- `/admin/playlists`: catálogo com id/nome, estado, quantidade de itens e telas;
- `/admin/playlists/new`: criação ativa, podendo começar vazia;
- `/admin/playlists/{id}`: detalhe, itens ordenados, adicionar/remover/subir/descer
  e telas vinculadas;
- `/admin/playlists/{id}/edit`: nome e descrição;
- `/admin/screens/{screen_id}/playlist`: associar, substituir ou desvincular;
  a lista de telas mostra a playlist atual ou Sem playlist e um link de gestão.

Navegação Telas/Mídias/Playlists. Todas as páginas exigem administrador ativo.
Todos os POSTs usam o CSRF da sessão; GET não altera playlists ou vínculos.
Sucesso redireciona com 303; campos inválidos retornam HTML 422, violações
de negócio 409, ausentes 404 e falha de banco genérica 503 quando não for
classificada como conflito. Formulários preservam valores em erros esperados.

Itens referenciam o acervo existente, sem copiar arquivos. Até 100 por playlist,
incluindo repetições. Use o formulário de imagem para duração inteira 5–600
segundos; vazio usa 15, inclusive em GIF/WebP animados. O formulário de vídeo
não envia duração; o backend recusa qualquer duração enviada para vídeo,
que fica com Reprodução integral. Remover um item preserva MediaAsset e arquivo.
Subir/descer muda uma posição; os botões dos limites ficam desabilitados.

Só playlists ativas com itens podem ser associadas. Cada tela tem no máximo
uma playlist; várias telas podem compartilhar a mesma. Substituir/desvincular
afeta apenas o vínculo escolhido e não altera Screen.active. Desativar uma
tela não remove sua associação. Desvincule todas as telas antes de desativar
uma playlist; uma playlist associada não pode perder seu último item.
Playlists inativas continuam editáveis, inclusive seus itens e ordenação.

### Procedimentos para futuras implantações e revalidações

Build, suíte e validação operacional da ETAPA 007 estão aprovados pelo operador;
o backup anterior à implantação está registrado acima. Para futuras implantações
ou revalidações, após revisão do diff e backup apropriado dos dois volumes,
seguir a sequência de [DEPLOYMENT](DEPLOYMENT.md#implantação-de-playlists--etapa-007).
Não executar up se build ou pytest falharem. Não repetir bootstrap, não alterar
o .env/binding e não remover volumes. Preservar o acesso atual por túnel SSH;
nenhuma liberação institucional é autorizada por esta etapa.

O schema é criado incrementalmente no startup. O operador confirmou na engine
implantada `Foreign keys habilitadas: True` e identificou as tabelas playlists,
playlist_items e screen_playlist_assignments. PRAGMA foreign_keys=ON é
habilitado/verificado por conexão make_engine. Para futuras conferências,
sem alterar registros, permanece a consulta de referência:

```bash
sudo docker compose exec signage-app python -c 'from app.database import engine; c = engine.connect(); print(c.exec_driver_sql("PRAGMA foreign_keys").scalar_one()); c.close()'
```

Resultado esperado dessa consulta: `1`. O resultado real fornecido pelo operador
é a confirmação True acima, sem atribuir a ele um comando não informado.
O Codex não executou essa consulta nesta atualização documental.

### Checklist manual confirmado pelo operador — ETAPA 007

**20/20 aprovados**, conforme os itens efetivamente informados pelo operador
neste fechamento; são evidências manuais separadas dos 439 testes pytest:

1. Painel de playlists abre após login.
2. Usuário anônimo é redirecionado ao login.
3. Criação de playlist com nome e descrição.
4. Edição de nome e descrição.
5. Inclusão de imagem da biblioteca.
6. Configuração da duração da imagem.
7. Inclusão de vídeo MP4.
8. Vídeos configurados para reprodução integral.
9. Inclusão de mídias repetidas.
10. Alteração da ordem com Subir e Descer.
11. Remoção de item com reorganização da sequência.
12. Associação de playlist válida à TV Piloto.
13. Associação da mesma playlist à TV do Pátio.
14. Substituição de playlist associada.
15. Desassociação sem desativar a TV.
16. Bloqueio de associação de playlist vazia ou inativa.
17. Bloqueio de desativação de playlist associada.
18. Bloqueio de remoção do último item de playlist associada.
19. Proteção das operações administrativas por autenticação e CSRF.
20. Persistência de playlists, itens e associações após restart e recriação.

Evidências consolidadas em [STATUS](STATUS.md#validação-operacional-da-etapa-007).
Os itens podem ser repetidos em futuras revalidações. O backup anterior à
implantação foi criado pelo operador, mas o teste formal de restauração conjunta
do SQLite e mídias permanece pendente. A ETAPA 007 entrega apenas configuração
e associação; não há TVs reproduzindo playlists por um player do sistema.
Player web e identidade limitada de dispositivos estão implementados na 008,
com homologação funcional local confirmada conforme matriz no início deste
documento. Integração real BTV13/H6+, auditoria e recuperação
administrativa continuam futuras. HTTPS institucional é necessário antes de disponibilizar o painel na
rede. O fechamento documental histórico da 007 não iniciou a 008; a
implementação atual e o alcance das evidências constam no início do documento.
