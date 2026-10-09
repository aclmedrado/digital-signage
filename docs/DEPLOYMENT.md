# Implantação

Execute no diretório oficial /home/administrador/digital-signage.
Docker e Docker Compose devem estar disponíveis; o usuário operacional utiliza
sudo, com autenticação realizada no próprio terminal. A configuração real usa .env não versionado, conforme .env.example.

O binding padrão é 127.0.0.1:8080, acessível somente no host. As variáveis
SIGNAGE_BIND_IP e SIGNAGE_PORT estão documentadas em .env.example. Para usar
outros valores sem criar .env, passe-os após sudo em cada comando Compose que
valida ou cria containers. Exemplo para a implantação atual:

```bash
sudo SIGNAGE_BIND_IP=10.4.254.202 SIGNAGE_PORT=8080 docker compose config --quiet
sudo SIGNAGE_BIND_IP=10.4.254.202 SIGNAGE_PORT=8080 docker compose up -d --wait
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

A imagem atual é digital-signage:etapa004, com build e validação operacional
aprovados conforme resultados fornecidos pelo operador. O container
digital-signage-app foi confirmado healthy em 10.4.254.202:8080, com
inicialização normal e logs sem erros; 66 testes passaram, com três warnings
descritos em docs/STATUS.md. Esses resultados não foram reexecutados nesta
atualização documental. O único serviço signage-app executa como
UID/GID 10001, com porta interna 8000 e binding configurável, por padrão
127.0.0.1:8080. Ajuste as URLs de teste ao IP e à porta escolhidos. O healthcheck usa Python
para verificar HTTP 200 e o JSON de /health. Aguarde o estado healthy.

O banco fica no volume nomeado signage-data em /app/data. O Compose gerencia
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
sem falhas. O container está healthy em 10.4.254.202:8080 -> 8000/tcp, com
UID/GID 10001; /app/data pertence a signage:signage e signage.db foi criado
no volume signage-data. A API e os quatro ciclos de persistência foram
validados; o registro completo está em docs/STATUS.md.

Para futuras implantações ou revalidações, inspecione primeiro sudo docker
compose ps, containers, redes, volumes e binding atual. Preserve no .env o IP
e porta da implantação antes de recriar o container (atualmente
10.4.254.202:8080). Execute no terminal do operador:

```bash
sudo docker compose config
sudo docker compose build
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
sudo docker compose up -d
sudo docker compose ps
sudo docker compose logs --tail=100 signage-app
```

Aguarde healthy e valide também GET / e GET /health. Teste a API:

```bash
curl -i -X POST http://10.4.254.202:8080/api/screens -H 'Content-Type: application/json' -d '{"name":"TV Recepção","slug":"recepcao","location":"Recepção"}'
curl -i http://10.4.254.202:8080/api/screens
```

Use o id retornado pelo POST nas consultas GET /api/screens/{id} e PATCH
/api/screens/{id}. Verifique 201 na criação, 200 nas consultas/atualizações,
404 para id ausente, 409 para slug duplicado e 422 para slug inválido.
Exemplo de atualização: PATCH com {"active":false}, seguido de GET.
Consulte docs/OPERATIONS.md para repetir a verificação de persistência real,
já concluída com sucesso nesta etapa.
