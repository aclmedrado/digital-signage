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
