# Implantação

Execute no diretório oficial /home/administrador/digital-signage.
Docker e Docker Compose devem estar disponíveis; o usuário operacional utiliza
sudo, com autenticação realizada no próprio terminal. Não criar .env nesta etapa.

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

A imagem é digital-signage:etapa002. O único serviço signage-app executa como
UID/GID 10001, com porta interna 8000 e binding configurável, por padrão
127.0.0.1:8080. Ajuste as URLs de teste ao IP e à porta escolhidos. O healthcheck usa Python
para verificar HTTP 200 e o JSON de /health. Aguarde o estado healthy.

Não existem volumes ou dados persistentes nesta etapa. O Compose gerencia
somente a rede própria do projeto; não alterar configurações globais do Docker.

A ETAPA 002 foi validada operacionalmente com a imagem digital-signage:etapa002,
container digital-signage-app healthy e binding 10.4.254.202:8080 -> 8000/tcp.
Os dois testes passaram e GET / e GET /health retornaram HTTP 200 nesse endereço.
O registro completo dos resultados está em docs/STATUS.md.
