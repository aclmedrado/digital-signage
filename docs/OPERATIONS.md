# Operações

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

Acesse no navegador:

- `http://10.4.254.202:8080/admin`;
- `http://10.4.254.202:8080/admin/screens`.

Ajuste IP e porta conforme a implantação. O painel permite listar, cadastrar,
editar, ativar e desativar telas; não há exclusão. Cadastro e edição solicitam
nome, slug e localização. Novas telas ficam ativas; ativação e desativação
são ações separadas na listagem. Sucesso redireciona por HTTP 303 para a
listagem com uma mensagem; erros mantêm os valores no formulário HTML.

O painel e a API ainda não possuem autenticação ou autorização. Utilizar
somente no ambiente interno controlado; não expor a aplicação diretamente à Internet.

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

Para repetir a verificação, crie uma tela pela API e anote o id retornado.
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
exclusão, playlists, associação às telas ou player TV Box.

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

Autenticação, autorização e proteção CSRF ainda estão ausentes e são
obrigatórias na ETAPA 006, antes da liberação institucional. Testar somente
com operadores confiáveis em ambiente restrito; não expor à Internet.
O operador decidiu manter temporariamente 10.4.254.202:8080 durante os testes,
como risco temporariamente aceito. Esse binding não constitui proteção de
acesso nem autorização para liberação institucional.
Não alterar firewall, SSH, sudoers, grupos, Docker global ou permissões
para contornar bloqueios de sudo. O .env real e as portas foram preservados.

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

Para Range, substitua 1 pelo id real de um MP4 com mais de 100 bytes e ajuste
IP/porta conforme o binding aprovado pelo operador:

```bash
curl --noproxy '*' -D - -o /dev/null -H 'Range: bytes=0-99' http://127.0.0.1:8080/media/1/file
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
conjunto de SQLite e mídias da ETAPA 005 nem confirma restauração. O backup
dos dois volumes e o ensaio de restauração continuam sem confirmação de execução.

Procedimento para futuros backups consistentes, não executado nesta atualização.
No diretório oficial, inspecione o espaço disponível e reserve uma janela
sem uploads. A imagem
etapa005 deve estar construída antes de usar compose run abaixo; build não
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
