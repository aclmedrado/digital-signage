# ETAPA 009 — Prompt para Codex: diagnóstico do HTTPS e piloto BTV13 (009-A)

> **Execução autorizada neste prompt: somente a FASE 009-A (inspeção não invasiva e plano de implantação).**
>
> **Não executar a 009-B automaticamente.** O objetivo é eliminar suposições sobre a BTV13 e a infraestrutura de certificados antes de instalar software, editar serviços ou expor qualquer porta.

## 0. Leitura, localização e restrições obrigatórias

Você é o agente de implementação do repositório **Digital Signage** do IFG Câmpus Inhumas. Trabalhe somente no repositório oficial:

```text
/home/administrador/digital-signage
```

Estado de referência ao final da ETAPA 008: branch `main`, commit `3de5dbc15b744dda52ded2bdf1d0ffee92b4eace`, upstream sincronizado e working tree limpa. O operador deverá ter versionado previamente e **separadamente**:

```text
docs/adr/0009-https-and-btv13-kiosk-pilot.md
docs/prompts/etapa009.md
```

Antes de qualquer ação:

1. Execute **somente leitura**: `pwd`, `git branch --show-current`, `git status --short`, `git log --oneline --decorate -6`, `git diff --check`.
2. Confirme que a branch é `main`, que os dois documentos de 009 estão versionados e que não existem alterações preexistentes. Se houver diferença, **pare e reporte**; não use `reset`, `stash`, `checkout`, `clean`, `git add`, `commit` ou `push` para forçar a condição.
3. Leia integralmente `AGENTS.md`, `README.md`, `docs/STATUS.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, `docs/OPERATIONS.md`, `docs/SECURITY.md`, todos os ADRs aplicáveis e `docs/prompts/etapa009.md`; trate o ADR 0009 como decisão proposta, a ser aprovada antes de mudar infraestrutura.
4. Inspecione os arquivos atuais ligados ao transporte/autorização: `app/security.py` (inclusive `transport_allowed()` e `AuthMiddleware`), `app/config.py`, `app/main.py`, `app/services/auth.py`, `app/services/device_auth.py`, `app/routes/device.py`, `app/routes/player.py`, `compose.yaml`, `Dockerfile`, `.env.example` e testes relevantes. **Não ler o `.env` real.**
5. Compare as premissas do ADR com o código. Registre divergências reais sem inventar configuração externa.

### Restrições absolutas da 009-A

- Não executar `sudo`, `apt install`, `systemctl enable/start/stop/restart`, `docker compose up/build/run`, `docker exec`, alteração de firewall, `ufw`, `iptables`, `nft`, DNS, certificados, proxy, SSH, kernel, display manager, autologin, arquivos `/etc`, usuários/grupos ou boot.
- Não modificar `.env`, banco de produção, volumes, mídia, certificados ou trust store. Não pedir/exibir senhas, seeds, cookies, códigos de pareamento, tokens, chaves privadas ou arquivo `.env` real.
- Não alterar código, testes, Dockerfile, Compose nem documentos normativos nesta primeira execução. Não criar serviços/containers, nem mesmo provisórios.
- Não estabelecer SSH com a BTV13 sem autorização explícita do operador e endereço credenciado por ele. Se o ambiente não permitir tal acesso, **fornecer comandos de diagnóstico para o operador executar** e aguardar seus resultados. Nunca procurar dispositivos por varredura, `nmap` ou tentativa de senha.
- Não executar `git add`, `git commit`, `git push` ou reinicialização de equipamento. Não iniciar implantação quiosque, HTTPS, ETAPA 010 ou replicação de frota.
- Não usar HTTP `10.4.254.202:8080` para credenciais de TV, nem `--ignore-certificate-errors`, `--no-sandbox`, `--disable-web-security`, `--allow-running-insecure-content`, `--forwarded-allow-ips='*'` indiscriminado ou qualquer bypass para “fazer funcionar”.

## 1. Meta da ETAPA 009

Preparar, em conformidade com o ADR 0009, a homologação futura de **uma** BTV13 com Debian Trixie executando o player já implementado na ETAPA 008 através de Chromium em modo quiosque. O transporte da TV ao servidor deverá ser HTTPS de ponta a proxy confiável, com certificado validado, e o backend permanecerá exclusivamente no loopback do servidor.

A ETAPA 008 é o baseline, já implementada e versionada: 555 testes Python aprovados, 13 testes JS simulados, `digital-signage:etapa008` healthy, `127.0.0.1:8080`, pareamento e reprodução reais via túnel SSH, isolamento, revogação e persistência. **Não reclassificar esse baseline como homologação de TV física.**

Nesta primeira execução (009-A), a entrega é um **diagnóstico verificável e um plano 009-B**. Não é entrega de quiosque instalado.

## 2. Auditoria somente leitura do lado servidor

Revise e responda com evidência de arquivo, linha e contrato:

1. O backend FastAPI continuará em loopback ao receber TLS de proxy no host? Confirme onde `SIGNAGE_BIND_IP` e publicação de portas são definidos; não exiba `.env`.
2. `transport_allowed()` exige HTTPS de `request.url.scheme`, confia em `X-Forwarded-Proto` ou usa algum mecanismo explícito? O que acontece com `SESSION_COOKIE_SECURE=true` e `LOCAL_AUTH_TEST_MODE=false` ao receber requisição HTTP interna vinda do proxy? **Não suponha** que Caddy por si só satisfaça o middleware. Documente a adaptação/teste realmente necessário.
3. Qual política efetiva de Uvicorn para cabeçalhos `X-Forwarded-*`? Há lista de proxies confiáveis? De onde ela vem? Quais origens de rede devem ser permitidas? Como impedir spoofing? Não confiar em cabeçalhos do cliente sem cadeia de confiança.
4. Como `request.client.host` alimenta rate-limit de ativação? Um proxy poderia converter todos os clientes em `127.0.0.1`, causando compartilhamento involuntário de limite? Proponha ensaio de origens múltiplas e cabeçalhos forjados.
5. Quais mudanças de configuração/código/testes são **estritamente necessárias** para HTTPS? Quais arquivos permaneceriam intocados? Como preservar autorização administrativa, CSRF, cookies, manifesto/mídia e Range?
6. Há software de proxy instalado, disponível ou documentado? Se não houver evidência, marcar desconhecido — não instalar Caddy automaticamente.
7. Existe eventual serviço em 443/80 ou política de TLS/DNS institucional? Se somente dados do operador puderem confirmar, marcar dependência externa. **Não inventar domínio nem autoridade certificadora.**
8. Descrever impactos de mudar a origem de `http://localhost:18080` para `https://<FQDN_APROVADO>`: novo contexto de cookies, relogin administrativo e reativação eventual das TVs, escopo do certificado, host-only cookies e preservação das sessões armazenadas.

Evite usar comandos que exijam sudo ou que leiam credenciais. Qualquer saída de status/rede deve ser revisada para não incluir informação sensível desnecessária.

## 3. Diagnóstico da BTV13 a ser solicitado ao operador

**Não invente hardware nem resultado.** O operador poderá executar no terminal da BTV13, com usuário comum, o bloco do ADR 0009. As informações mínimas são:

- Versão real Debian Trixie e kernel, arquitetura `uname -m`, CPU/SoC se verificável.
- Memória, armazenamento e condição de instalação (evitar lotar partição raiz).
- Sessão X11/Wayland/TTY; compositor/display manager, `loginctl`, resolução HDMI e modo gráfico já disponível.
- Chromium instalado/versão/arquitetura dos pacotes; possibilidade de inicializá-lo em sessão gráfica **sem root**.
- Presença de DRM/V4L2/VA-API e/ou outros recursos verificáveis; distinguir **dispositivo presente** de **aceleração efetivamente usada no H.264**.
- Conectividade à rede e **origem HTTPS aprovada** quando houver DNS; ausência de CA confiável/erro de certificado deve bloquear pareamento.
- Capacidade de acesso remoto existente (SSH), somente se o operador já tiver autorizado o método, sem expor credenciais.

O `XDG_SESSION_TYPE` sob SSH pode estar vazio; isso não comprova ausência de X11/Wayland no HDMI. Registre esta limitação.

Forneça ao operador os comandos **não invasivos** faltantes e peça a saída sem segredos. Não instale pacotes para produzir o diagnóstico.

## 4. Proposta técnica para 009-B — ainda sem executar

Entregue uma proposta **específica condicionada às evidências**, contendo:

### 4.1. HTTPS

- Opções: aproveitar TLS institucional já existente, ou Caddy no host `utilities` depois de aprovação.
- Requisito de DNS/FQDN e SAN; certificado de CA institucional/pública válida ou CA interna distribuída de forma controlada. No caso de CA interna, **somente certificado da raiz pública** chega ao cliente, nunca chave privada. Validação no Chromium sem exceções.
- Sequência de implantação reversível: backup da configuração anterior, teste de sintaxe, checagem do listener/ACL, execução controlada pelo operador, `https://<FQDN>/health`, conferência de headers, cookies Secure e validação de confiança na BTV13.
- Revisão de proxy IP/Proto: distinguir peer confiável do valor enviado pelo navegador; negar spoofing e não enfraquecer modo seguro existente. Avaliar origem real para rate-limit.
- Plano de rollback: retirar rota HTTPS/alteração do proxy sem publicar HTTP externo nem destruir dados; preservar retorno seguro ao teste local por túnel SSH, se necessário.
- Se faltarem aprovação institucional, FQDN, certificado, ACL ou política de proxy: **bloqueio G1**, sem operar 009-B.

### 4.2. Chromium quiosque na BTV13

- Selecionar estratégia coerente com o gerenciador de exibição **observado** (autostart desktop ou `systemd --user` associado à sessão gráfica). Não assumir `DISPLAY=:0` nem Wayland automático.
- Utilizar conta não privilegiada e perfil persistente exclusivo com diretório privado 0700. Não criar múltiplos serviços que iniciem duas instâncias. Não executar como root nem desabilitar sandbox/certificados.
- URL de player só com FQDN seguro e slug não secreto; primeira ativação manual pelo código `/device/activate`.
- Descrever habilitação, teste, logs sem segredos, parada, desabilitação e rollback do autoinício; medidas para evitar screen blanking **somente** se compatíveis com a sessão gráfica e aprovadas.
- Planilha simples ou roteiro de observação: reprodução JPEG/PNG/WebP/GIF + MP4 H.264, vídeo mudo, uso real de CPU/RAM, quedas de frame observáveis, resolução HDMI, temperatura/thermal quando disponível, polling e limites de rede. Não afirmar aceleração de vídeo antes de teste.
- Ensaios autorizados: alteração de playlist, revogação, novo pareamento, desconexão/reconexão, reinício do Chromium e reinício do dispositivo. Reboot/power-cycle somente com aprovação e acesso físico disponível.

### 4.3. Critérios de passagem

Apresente checklist objetivo cobrindo G0, G1, G2, G3, G4 definidos no ADR. Não declare G1 cumprido sem os dados da BTV13 e escolha de infraestrutura TLS. Propor teste acompanhado inicial ≥2h e longa duração alvo 24h (medição real, não estimativa).

## 5. Formato exigido do relatório 009-A

Responda em português com estas seções, sem omitir lacunas:

1. **Pré-condições Git:** diretório, branch, HEAD, ADR/prompt versionados, tree limpa.
2. **Evidências do servidor:** arquivos e linhas relevantes; transporte atual, política de proxy/headers, autorização, Compose e modo local, sem ler `.env`.
3. **Inventário da BTV13:** `confirmado`, `informado pelo operador` ou `não verificado` por atributo; jamais inferir pacote/driver/CPU a partir de Debian Trixie genericamente.
4. **Decisões necessárias do operador/TI:** FQDN, certificado/CA, restrição de rede, proxy escolhido, acesso físico/remoto, sessão gráfica e conta de quiosque.
5. **Riscos e correções propostas:** compatibilidade TLS/ASGI, rate-limit por origem, gerenciamento seguro do certificado, Chromium/driver/codec, privacidade do perfil.
6. **Plano 009-B em ordem:** mudanças propostas de código/configuração, testes unitários/integrados, comandos **a executar pelo operador** para instalação e homologação, rollback por componente.
7. **Critérios G0–G4:** para cada um, `atendido / pendente / bloqueado`, com fundamento.
8. **Verificações realmente executadas:** separar leitura/análise de testes efetivos; não reportar pytest, `healthy`, HTTPS, Chromium nem reprodução física sem execução real.
9. **Git final:** `git status --short`, `git diff --check`, arquivos alterados (esperado: nenhum), nenhum commit/push.
10. **Próxima ação concreta:** lista curta de evidências solicitadas ao operador. Se G1 não passou, **encerrar esta execução com o relatório de diagnóstico**.

## 6. Proibições de escopo

Não iniciar implantação em H6+, demais BTV13, agendamento, monitoramento de frota, cache/offline, transcodificação, novos bancos/containers ou integração com outras aplicações. Não alterar o contrato de códigos/sessões da ETAPA 008 para contornar requisitos de HTTPS.

A aceitação de 009-A é um diagnóstico honesto, completo e verificável, **não** a implantação da TV. O operador decidirá a continuação para 009-B a partir do seu relatório e do inventário físico.

## 7. Referências técnicas para conferência

- ADR: `docs/adr/0009-https-and-btv13-kiosk-pilot.md`.
- Debian Chromium Trixie: https://packages.debian.org/trixie/chromium
- Debian Chromium / vídeo / Wayland: https://wiki.debian.org/Chromium
- Caddy Automatic HTTPS: https://caddyserver.com/docs/automatic-https
- Caddy reverse_proxy: https://caddyserver.com/docs/caddyfile/directives/reverse_proxy
- Caddy tls internal: https://caddyserver.com/docs/caddyfile/directives/tls

Fontes de projeto prevalecem sobre inferências sobre o estado real do servidor. A adoção de instruções genéricas de terceiros exige análise de compatibilidade com o ambiente, segurança e autorização institucional.
