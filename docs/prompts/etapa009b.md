# Prompt do Codex — ETAPA 009-B1: preparar HTTPS piloto com Caddy/CA interna (SEM DEPLOY)

## Objetivo e autorização

O operador escolheu a alternativa **Caddy com CA interna**, sem DNS/certificado institucional, para o piloto BTV13. O endereço pretendido é **`https://10.4.254.202`**, com certificado contendo SAN IP e confiança explícita nos clientes. Esta execução é **somente preparação do repositório e testes não privilegiados**. Não autoriza instalação no host, exposição da porta 443, configuração operacional real ou início do quiosque.

Leia integralmente, antes de editar: AGENTS.md, README.md, docs/STATUS.md, docs/ARCHITECTURE.md, docs/DEPLOYMENT.md, docs/OPERATIONS.md, docs/SECURITY.md, todos os ADRs relevantes, `docs/adr/0009-https-and-btv13-kiosk-pilot.md`, **`docs/adr/0009b-caddy-internal-ca-ip-pilot.md`** e este `docs/prompts/etapa009b.md`. Inspecione app/config.py, app/security.py, app/main.py, Dockerfile, compose.yaml, requirements.txt, autenticação, player, testes e scripts. Não alterar ADRs/prompts.

## Pré-condições Git

1. Confirmar diretório `/home/administrador/digital-signage`, branch `main`, HEAD, working tree **totalmente limpa** e ADR+prompt 009-B1 versionados separadamente e já presentes em `HEAD`.
2. Se houver diferença inesperada, interromper antes de editar e relatar. Não executar git add/commit/push, reset/rebase ou operações mutantes.
3. Confirmar ETAPA 008 no baseline e preservar funcionalidades, arquivos e armazenamento existentes.

## Escopo permitido

1. Preparar `deploy/caddy/Caddyfile.pilot.example`, como **MODELO** não operacional. Deve contemplar `https://10.4.254.202`, `bind 10.4.254.202`, `tls internal`, upstream `127.0.0.1:8080`, sem abrir 80/redirecionamento por padrão, Host esperado e ACL explícita fail-closed. Não autorizar IPs fora do piloto; o IP `10.4.2.190` só é um candidato observado na rota, não garantia de lease estável. Origem administrativa ainda desconhecida e deve ficar identificada como configuração pendente; não ampliar para 10.4.0.0/16. Verificar sintaxe atual na documentação oficial; se `caddy` não existir, declarar que validação CLI não foi executada.
2. Sanitizar cabeçalhos X-Forwarded-For, X-Forwarded-Proto, X-Forwarded-Host e Forwarded; considerar corretamente uma cadeia direta cliente→Caddy, sem confiar em campos arbitrários recebidos de clientes. Não inventar o endereço do peer visto pelo Uvicorn. Documentar procedimento seguro de identificação e a fronteira de confiança com a bridge Docker.
3. Documentar `SESSION_COOKIE_SECURE=true`, `LOCAL_AUTH_TEST_MODE=false`, `FORWARDED_ALLOW_IPS` com somente peer(s) comprovados, `SIGNAGE_BIND_IP=127.0.0.1`, `SIGNAGE_PORT=8080`; não modificar o `.env` real nem incluir segredos em exemplos versionados. Verificar que `restart` não aplica mudanças no ambiente, exigindo recriação controlada.
4. Documentar criação/backup da PKI do Caddy, transferência autenticada apenas da raiz pública, fingerprint SHA256, teste de SAN IP e cadeia, instalação restrita de confiança na BTV13 e confirmação no Chromium. **Nunca** copiar/distribuir `root.key`, intermediate.key, certificados privados nem fixar `--ignore-certificate-errors`, `curl -k` ou `--no-sandbox`.
5. Adicionar cobertura isolada e reproduzível de transporte, autenticação/cookies, autorização de player, CSRF, Range 206/416, confiança de encaminhamento e host esperado **na medida do necessário**. Não transformar `TestClient` puro em prova de funcionamento real do proxy. Se a lacuna exigir teste de integração que só pode ser feito após instalação operacional, criar checklist/manual e marcar como pendente. Não enfraquecer testes existentes nem criar endpoints de debug expostos.
6. Atualizar de forma parcimoniosa docs/STATUS.md, docs/ARCHITECTURE.md, docs/DEPLOYMENT.md, docs/OPERATIONS.md, docs/SECURITY.md e README.md conforme necessário, sempre distinguindo preparação documental da implantação real, preservando o histórico das ETAPAS 008/009-A.
7. Preparar roteiro de intervenção do operador para etapa posterior 009-B2, incluindo autorização da rede/porta 443, origem administrativa, inspeção de portas existentes, validação prévia, backup consistente de SQLite+mídias+.env+PKI do Caddy (quando existir), reversão, teste de clients distintos, teste do trust store da TV e disponibilidade do autoinício XFCE para *depois* do G2.

## Limites inegociáveis

- Não executar sudo, apt, systemctl mutante, firewall/ACL de host, docker build/run/up, Caddy como serviço, HTTPS real, login, pareamento ou alterações de rede.
- Não editar `.env`, `/etc/caddy`, `/etc/hosts`, trust store, `/var/lib/caddy`, Docker Compose operacional, volumes, SQLite ou mídias reais. Não capturar tokens/códigos/cookies/CA privada em logs.
- Não criar hostname fictício, alterar porta 8080 para a LAN, habilitar confiança geral em X-Forwarded-* ou instalar root CA automaticamente na BTV13.
- Não iniciar modo quiosque, autologin, X11 remoto, flags GPU especiais nem ETAPA 010.
- Não inferir aprovação institucional de rede porque o operador escolheu a opção B.
- **Não realizar commit/push.**

## Checagem de segurança obrigatória

Explicitar a cadeia de confiança: cliente → Caddy (TLS) → backend loopback/Docker → Uvicorn `request.url.scheme`, `request.client.host`. Identificar como testar que cabeçalhos X-Forwarded-* enviados pelo cliente não promovem HTTP nem alteram limites; como detectar peer compartilhado inseguro; como assegurar que rotas administrativas, APIs, manifesto e mídia não são liberadas pelo simples fato de o TLS funcionar.

Distinguir: teste do certificado em curl confiável; verificação manual de Chromium; testes Python simulado; integrações reais em Caddy+Uvicorn; autorização/rede no host. Sem prova de runtime, registrar pendência.

## Verificações não privilegiadas

Executar `git diff --check`, revisar diff e novos arquivos; verificar AST/sintaxe Python para os arquivos tocados e tests/formatos disponíveis sem instalar pacotes no host. Se o projeto não disponibilizar pytest/FastAPI no host sem Docker, relatar **0 pytest executados**, e deixar os comandos de homologação para o operador. Não afirmar que testes da 008 foram reexecutados nesta fase.

## Saída obrigatória

Apresentar relatório estruturado:

1. Git inicial/final, HEAD, arquivos alterados/criados, sem commit.
2. Decisões IP/CA e justificativa da configuração exemplo.
3. Quais clientes e interfaces estão previstos e quais ainda precisam de aprovação.
4. Como foram tratados Host, X-Forwarded-* e as fronteiras de confiança; peer Uvicorn **não presumido**.
5. Testes criados e **separadamente** testes realmente executados, warnings, falhas e bloqueios.
6. Comandos manuais *propostos* de validação e homologação, apenas após autorização/backup.
7. Plano de rollback e preservação da PKI/SQLite/mídias.
8. Portões G0–G4 com evidências ou pendências.
9. `git diff --check`, `git diff --stat`, `git status --short`; confirmação de ausência de alterações no ambiente e de commit/push.

**Critério final:** entrega da preparação versionável da 009-B1, não da implantação 009-B2; não declarar HTTPS funcionando, G2 concluído nem BTV13 pareada por HTTPS.
