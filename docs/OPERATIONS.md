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
