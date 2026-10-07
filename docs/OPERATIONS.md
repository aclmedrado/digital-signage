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
