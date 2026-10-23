# ADR 0009 — Transporte HTTPS e piloto de player quiosque na BTV13

- **Status:** Proposto — versionar antes da execução
- **Data:** 2026-10-22
- **Projeto:** Digital Signage — IFG Câmpus Inhumas
- **Escopo:** ETAPA 009, uma BTV13 com Debian Trixie como piloto
- **Dependências:** ADRs 0005–0008, especialmente 0006 (autenticação), 0007 (playlists) e 0008 (player/pareamento)
- **Referência inicial do repositório:** `main`, commit `3de5dbc` (`feat: add secure web player and device pairing`), sem alterações pendentes no fechamento da ETAPA 008

## 1. Contexto e evidências anteriores

A ETAPA 008 entregou player HTML/CSS/JS, manifesto versionado, mídias por tela, pareamento via código temporário e cookie opaco revogável. O operador confirmou: **555 testes Python aprovados**, **13 testes JS simulados aprovados**, `digital-signage:etapa008` **healthy**, `/health` HTTP 200, quatro tabelas novas, FKs SQLite habilitadas, primeiro pareamento e reprodução reais em navegador, atualização sem interromper vídeo, revogação/isolamento e persistência após `restart` e `force-recreate`. Commit e push realizados; `HEAD == origin/main == 3de5dbc15b744dda52ded2bdf1d0ffee92b4eace`.

O ambiente confirmado até aqui usa HTTP **somente no host loopback** (`127.0.0.1:8080`) com túnel SSH e `SESSION_COOKIE_SECURE=false`, `LOCAL_AUTH_TEST_MODE=true`. Este é um modo **de desenvolvimento**, não uma configuração adequada a TVs conectadas pela LAN. As BTV13 estão disponíveis para reaproveitamento, e há relato de Debian Trixie em pelo menos uma unidade, mas **arquitetura de CPU, sistema gráfico, GPU/VPU, aceleração H.264, rede, hostname, DNS, pacotes, memória e permissões reais ainda exigem levantamento**. Não extrapolar resultados do Chrome em computador para a TV.

O objetivo é provar o funcionamento de **uma** unidade piloto, antes de replicação para H6+ e demais BTV13.

## 2. Decisão central e divisão em portões

A ETAPA 009 será realizada de forma incremental, em duas fases **com autorização explícita entre elas**:

1. **009-A — Inventário e desenho de implantação, somente leitura:** revisar configuração existente no servidor; coletar evidências não sensíveis da BTV13 por comandos executados pelo operador ou SSH **explicitamente autorizado**; selecionar origem HTTPS e estratégia de sessão gráfica/quiosque. Registrar diagnóstico, lacunas, plano, riscos e rollback. **Não instalar, expor serviços ou alterar infraestrutura.**
2. **009-B — Implantação controlada do piloto:** somente após aprovação do operador e da infraestrutura institucional de rede/certificados, estabelecer HTTPS confiável, adaptar estritamente o transporte ao proxy, preparar quiosque com usuário comum na BTV13 e homologar a TV real. Empregar procedimentos documentados e reversíveis; instalações e alterações de sistema são **comandos do operador**, não ações autônomas do Codex.

Se qualquer pré-condição indispensável não for comprovada, registrar **bloqueado / pendente de decisão**, sem substituir HTTPS por HTTP inseguro ou desabilitar verificações de certificado.

## 3. Arquitetura-alvo

```text
BTV13 / Debian Trixie (Chromium, usuário não privilegiado)
  |  HTTPS com DNS/nome estável, validação de certificado e cookies Secure
  v
Proxy TLS institucional existente OU Caddy no host utilities (a aprovar)
  |  HTTP restrito ao loopback do MESMO host, origem do proxy confiável
  v
127.0.0.1:8080 → Docker Compose signage-app (FastAPI :8000)
  |                     |
  +--> signage-data SQLite /app/data
  +--> signage-media /app/media
```

**Invariantes:** preservar `signage-app`, `digital-signage-app`, volumes, UID/GID 10001 e SQLite. Não adicionar novo serviço dentro do Compose automaticamente. Proxy no **host**, se necessário e aprovado, fica fora do Compose existente. Se já existir proxy/TLS institucional compatível, preferir reutilizá-lo; não instalar um segundo por conveniência. Não publicar FastAPI diretamente em interface LAN.

A origem HTTPS da TV será um **FQDN estável que resolva corretamente na rede autorizada** e esteja coberto por SAN do certificado. O nome é uma **decisão operacional pendente**; não inventar domínio institucional, IP de TV ou nome DNS. Um certificado de CA interna é opção apenas com governança, distribuição segura da **CA raiz pública** e confiança demonstrada no Chromium; chave privada de CA nunca vai para TV nem para Git. Certificado público válido emitido para nome institucional também é opção, desde que seus requisitos de emissão e exposição sejam atendidos.

### 3.1. Segurança do transporte e autenticação

- Habilitar `SESSION_COOKIE_SECURE=true`, `LOCAL_AUTH_TEST_MODE=false` **somente** no corte controlado para HTTPS testado, com rollback preparado. Não editar o `.env` real pelo Codex; o operador controla sua alteração e backup.
- O proxy deve encaminhar `X-Forwarded-Proto` e dados de cliente de maneira sanitizada. **Examinar concretamente** `app/security.py`, `transport_allowed()`, configuração de Uvicorn e limitações de proxy da ETAPA 006: a aplicação só deve reconhecer HTTPS original e IP real quando transmitidos por um proxy **explicitamente confiável**. Não aceitar `X-Forwarded-*` arbitrário vindo de clientes, nem usar `--forwarded-allow-ips='*'` sem justificativa e isolamento verificáveis.
- Considerar especificamente o rate-limit de ativação (`request.client.host`): ao introduzir proxy, não transformar todas as TVs em uma origem única sem documentar o impacto, nem confiar em IP forjado. Provar comportamento correto por testes negativos.
- Cookies administrativos e de dispositivo devem usar prefixos `__Host-` e atributos `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/`, sem `Domain`, no ambiente HTTPS. Um cookie do modo local não deve autenticar como cookie seguro de HTTPS por acidente.
- Nenhum login, pareamento, token de dispositivo ou cookie deve atravessar a LAN em HTTP. Sem downgrade HTTP→HTTPS que aceite POST sensível em claro; portas e redirecionamentos sujeitos à política institucional. Não permitir acesso por IP/hostname inesperado, TLS com certificado inválido ou proxys não autorizados.
- Os controles de ETAPA 008 continuam válidos: apenas uma sessão por tela, revogação, mídia por playlist atual e HTTP Range, CSRF admin e ativação, sem privilégios administrativos para a TV. Não usar senha admin em TV, cookies em scripts, URL com credencial, `localStorage`, variáveis públicas ou argumentos de processos.
- Segurança em profundidade: delimitar quais segmentos/IPs podem alcançar a origem HTTPS; avaliar política de firewall institucional sem alterar UFW ou regras de rede antes de aprovação.

### 3.2. Origem, certificado e proxy

Escolher, com o operador e TI institucional, uma das opções abaixo:

**Preferida:** proxy e certificado institucional já existentes com DNS e cadeia de confiança instalada nos clientes autorizados.

**Alternativa controlada:** Caddy instalado/gerenciado no host `utilities` (fora do Compose) escutando somente em interface/porta autorizada, reverso para `127.0.0.1:8080`, certificado emitido por CA institucional ou CA interna administrada sob controle local. Com `tls internal`, a cadeia **não é automaticamente confiável nas BTV13**: exige instalação controlada da CA pública e verificação real da cadeia e do nome no Chromium. Não prometer certificado público automático para nome interno.

Produzir configuração proposta para **revisão**, não aplicá-la sem autorização. Preservar mecanismo de atualização/renovação de certificados, logs sem segredos, backup do estado do proxy e um comando de rollback testável. O proxy não deve introduzir cache de manifestos/mídias autenticadas nem remover políticas `no-store`, `CSP`, `nosniff`, `Referrer-Policy` e controles de origem.

## 4. Piloto BTV13 e sistema gráfico

A BTV13 escolhida deverá ser inventariada antes de instalar ou configurar qualquer software. Coletar, sem segredos: fabricante/identificação visível, CPU/SoC, `uname -m`, distro/kernel, memória e armazenamento, resolução HDMI, `loginctl`, `XDG_SESSION_TYPE`, gerenciador de exibição ou compositor, pacotes Chromium, GPU/DRM (`/dev/dri` se existir), capacidades de VPU/VA-API/V4L2 (se disponíveis), rede/DNS e acesso ao FQDN HTTPS. **Não presumir que o SoC dispõe de aceleração no Chromium só porque o pacote existe.**

Um projeto ARM64 ou ARMHF só usa os pacotes compatíveis com arquitetura/ABI realmente confirmadas. Não compilar Chromium, trocar kernel, instalar firmware ou habilitar repositórios terceiros sem decisão formal separada.

### 4.1. Modo quiosque

- Executar Chromium oficial do Debian **como usuário comum dedicado ou explicitamente aprovado**, em sessão gráfica existente, com perfil persistente exclusivo e permissões restritas (ex.: `~/.config/chromium-signage`, `0700`). O cookie HttpOnly do dispositivo deve ser preservado no perfil local e não aparecer em linha de comando, unidades systemd ou logs.
- URL de inicialização: `https://<FQDN_APROVADO>/player/s/<slug>` (**somente slug público**); o primeiro pareamento é realizado **interativamente** na página `/device/activate`, com código inserido pelo operador.
- Considerar `chromium --kiosk --no-first-run` **somente após identificar a sessão gráfica** e testar as flags aceitas pela versão instalada. Autoplay mudo já é suportado pelo player e deve ser validado sem relaxar segurança global.
- Nunca usar `--no-sandbox`, `--disable-web-security`, `--ignore-certificate-errors`, `--allow-running-insecure-content` ou instalação de CA não verificada. Não executar Chromium como root.
- Autoinício por autostart do desktop ou **unidade systemd de usuário vinculada à sessão gráfica**, conforme observações do piloto. Não presumir `DISPLAY=:0`/Wayland, nem criar unidade de sistema iniciando GUI antes da sessão. Autologin gráfico só mediante avaliação explícita de segurança e aprovação. A escolha deve ser documentada com seu rollback.
- Evitar a combinação de vários processos/serviços que abram duas instâncias do mesmo quiosque; tolerar reinício do navegador, retorno de aba, rede indisponível e falha de energia sem produzir novos tokens.
- Operação prevista: 1920×1080 até 30 fps H.264 yuv420p (limite do catálogo atual), imagens JPEG/PNG/WebP/GIF. **São limites da mídia aceita pelo servidor, não provas de decodificação real pela BTV13.** Verificar fluidêz, uso de CPU/RAM, temperatura/thermal throttling se mensurável, áudio mudo, HDMI e recuperação após reinício.

## 5. Diagnóstico não invasivo — evidências solicitadas ao operador

Realizar preferencialmente **no terminal da BTV13**, por usuário comum; não enviar senhas, tokens, `.env`, endereço MAC completo, certificados privados ou valores de cookies:

```bash
printf '\n=== IDENTIDADE ===\n'
cat /etc/os-release
uname -m
uname -r
id -un
printf '\n=== RECURSOS ===\n'
free -h
df -h / /home
printf '\n=== GRÁFICO ===\n'
printf 'XDG_SESSION_TYPE=%s\n' "${XDG_SESSION_TYPE:-desconhecido}"
loginctl list-sessions --no-legend 2>/dev/null || true
systemctl get-default 2>/dev/null || true
printf '\n=== CHROMIUM ===\n'
command -v chromium || true
chromium --version 2>/dev/null || true
dpkg-query -W -f='${binary:Package} ${Version}\n' chromium chromium-common 2>/dev/null || true
printf '\n=== VÍDEO ===\n'
ls -ld /dev/dri /dev/video* 2>/dev/null || true
command -v vainfo || true
command -v ffmpeg || true
printf '\n=== REDE (SEM CREDENCIAIS) ===\n'
ip -br link | awk '{print $1, $2}'
ip route show default
```

O `XDG_SESSION_TYPE` via **SSH** pode estar vazio mesmo que uma sessão gráfica exista no HDMI: correlacionar com `loginctl`, configuração do display manager e observação local. Não concluir “sem interface gráfica” por variável SSH vazia. Com FQDN e CA definidos e aprovados, executar posteriormente verificações de resolução, certificado e acesso no próprio dispositivo.

No servidor, antes de propor TLS: inventariar **somente leitura** serviço atual, listeners relevantes (sem revelar segredos), software/proxy já existente, `app/security.py`, `app/main.py`, Compose e documentação. Não ler `.env`; pedir ao operador que confirme apenas valores **não sensíveis** e estado de binding. Não executar `sudo`, instalar proxy, alterar firewall ou escutar novas portas autonomamente.

## 6. Portões de aprovação

**G0 — Documentação aceita:** ADR e prompt `009` versionados por commits documentais separados, `main` limpa e sincronizada. Nenhum código novo antes disso.

**G1 — Inventário aprovado:** CPU/arquitetura, distro, sessão gráfica, navegador, rede e riscos levantados; rota HTTPS definida com DNS, certificado, controle de acesso e responsáveis; validação do encaminhamento HTTPS ao FastAPI planejada; rollback definido. **Ausência de evidência = parar antes de instalação/deploy.**

**G2 — Transporte seguro comprovado:** origem HTTPS com certificado válido e confiável para o cliente, sem aviso de certificado ou bypass, `Secure=true` e modo local desabilitado no contexto HTTPS; HTTP da app permanece no loopback; autenticação, CSRF, rate-limit e isolamento sob proxy testados; logs sem segredos; sem acesso a credenciais em HTTP da LAN. Provas operacionais apresentadas pelo operador.

**G3 — Piloto kiosk:** BTV13 reproduz tela autorizada pelo FQDN seguro, sem conta admin, em sessão de usuário comum; imagens e MP4 fluem e avançam; atualização/revogação/renovação de código preservadas; navegador retorna após falha de rede, restart do processo e reboot aprovado; perfil persistente preserva sessão válida; sem flags inseguras; monitorar consumo real. Primeiro validação assistida ≥2 horas, depois ensaio de longa duração (alvo 24 horas) antes de replicar a outras TVs. Não contar duração sem medição.

**G4 — Fechamento:** testes de regressão na imagem se o app for alterado, checklist de 009 com resultados manuais discriminados, backup do SQLite/mídia/.env quando houver alteração de serviço ou dados, restauração/rollback praticável, evidências da BTV13, documentação realista, auditoria e commit/push **somente pelo operador**. A ausência de ensaio formal de restauração conjunta das etapas anteriores deve permanecer explícita.

## 7. Testes exigidos (mínimo)

1. Certificado com SAN do hostname, cadeia confiável no Chromium e sem modo inseguro de validação; navegador rejeita destino com cert inválido.
2. `https://<FQDN>/health` 200 por origem aprovada; FastAPI continua somente `127.0.0.1:8080` no host.
3. HTTP de origem LAN não permite transportar credenciais; HTTPS fora da origem autorizada não concede acesso por engano.
4. Admin e dispositivo geram cookies `__Host-` + Secure/HttpOnly/Lax; CSRF e controles de acesso anteriores continuam.
5. Manifesto/mídia/Range autorizados apenas para tela pareada; outro dispositivo recebe recusa; redirecionamentos de página não divulgam segredos.
6. Rate-limit de ativação diferencia origens reais confiáveis ou documenta claramente limitação controlada do piloto, sem aceitar spoofing de cabeçalhos.
7. Player reproduz imagem temporizada, vídeo MP4 H.264 completo mudo e loop na TV física; eventual falta de decodificação por hardware é registrada com observações.
8. Mudança de playlist em andamento, estado neutro, revogação e novo pareamento verificados na TV.
9. Janela kiosk e perfil persistente, inicialização/reinicialização gráfica, retorno após rede e reinício/reboot autorizado; nenhuma credencial em arquivo de inicialização.
10. Testes de regressão e `healthy` no servidor após alterações aprovadas; `git diff --check`; validação do rollback.

## 8. Fora de escopo

- Implantar simultaneamente nas ~15 TV Boxes ou nas H6+.
- Alteração de kernel, device tree, firmware, bootloader, permissões DRM, root do navegador, flashing e aceleração por hacks.
- Novo painel de gerenciamento de frota, telemetria central, agendamento, reprodução offline, multicast ou transcodificação.
- Exposição pública à Internet, liberação institucional ampla, certificados sem governança, senhas/tokens no URL, criptografia ignorada.
- Migração de SQLite ou criação de novos containers/bancos sem ADR adicional.

## 9. Rollback e registro

- Antes de qualquer mudança, registrar configuração vigente e backup apropriado dos arquivos **fora do Git** que sejam responsabilidade do operador, sem transportar segredos para relatórios.
- Rollback do proxy/TLS deve restabelecer **o estado anterior seguro**, mantendo FastAPI no loopback e nunca expondo 8080 à LAN.
- Rollback da BTV13 deve ser desabilitar o mecanismo de autoinício e restaurar a sessão gráfica anterior; o operador pode revogar a sessão da tela no painel se for necessário descomissionar o piloto.
- Mudança de cookie `Secure`/modo de teste pode exigir novo login/repareamento pelo endereço HTTPS: documentar janela e comportamento, sem falsificar persistência entre origens distintas.
- Relatórios devem separar verificação estática, ensaios do operador e observação presencial na TV. Nada será declarado homologado sem evidência real.

## 10. Fontes primárias e notas de verificação

- Debian: pacote Chromium em Trixie (arquiteturas listadas; não garante aceleração de hardware): https://packages.debian.org/trixie/chromium
- Debian Wiki: Chromium, vídeo/Wayland (orientação genérica dependente de drivers): https://wiki.debian.org/Chromium
- Debian Wiki: gerenciadores de exibição (a sessão gráfica precisa ser identificada): https://wiki.debian.org/DisplayManager
- Caddy: HTTPS automático/local e CA interna: https://caddyserver.com/docs/automatic-https
- Caddy: `tls internal` e cadeia/CA: https://caddyserver.com/docs/caddyfile/directives/tls
- Caddy: `reverse_proxy`, cabeçalhos `X-Forwarded-*` e confiança: https://caddyserver.com/docs/caddyfile/directives/reverse_proxy
- systemd: política de reinício de serviços; depende da sessão do usuário: https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html

As fontes externas descrevem capacidades possíveis de Debian/Caddy; **não** substituem o levantamento da BTV13 nem uma decisão de TI institucional.
