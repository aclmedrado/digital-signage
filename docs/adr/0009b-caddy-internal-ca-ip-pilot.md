# ADR 0009-B — HTTPS com Caddy, CA interna e acesso pelo IP no piloto BTV13

- **Status:** Proposto — decisão de arquitetura selecionada pelo operador em 23/10/2026; implantação condicionada aos portões abaixo.
- **Complementa:** `docs/adr/0009-https-and-btv13-kiosk-pilot.md`. Não substitui seus requisitos de segurança.
- **Escopo:** infraestrutura piloto para ETAPA 009-B1; autoinício/quiosque físico só na 009-B2, após validação HTTPS.
- **Aplicação base:** ETAPA 008, commit `3de5dbc` (referência histórica; confirmar HEAD atual).

## 1. Contexto e decisão

Não há disponibilidade de hostname DNS institucional nem certificado TLS institucional para `utilities`. O piloto utilizará **Caddy executado no próprio host `utilities`** como proxy reverso HTTPS, com **CA interna do Caddy**, endereço de acesso `https://10.4.254.202` e certificado de servidor que inclua **SAN do tipo IP Address = 10.4.254.202**. O endereço por IP evita mudanças em DNS, `/etc/hosts`, mDNS e infraestrutura institucional. A CA não é pública: sua **raiz pública precisa ser conferida e instalada explicitamente** em cada cliente autorizado, incluindo a BTV13 e o navegador da estação administrativa. Nunca instalar ou transmitir a chave privada da CA.

O proxy será a única borda de rede do piloto. O backend continuará publicado **somente** em `127.0.0.1:8080` no host, recebendo HTTP local. **Não** abrir `10.4.254.202:8080` ou transmitir cookies/códigos em HTTP pela LAN. O piloto não representa liberação institucional ampla.

A opção B foi selecionada pelo operador, mas a habilitação de 443 na infraestrutura do IFG ainda precisa de aprovação operacional/política de rede. Se essa autorização não existir, interromper implantação e usar ambiente isolado explicitamente autorizado.

## 2. Evidências já conhecidas

- Host `utilities`: Ubuntu 26.04.1, IP `10.4.254.202`, aplicativo FastAPI em Docker, `127.0.0.1:8080`, ETAPA 008 homologada localmente com 555 testes Python e 13 testes JS simulados.
- BTV13: Debian 13 Trixie/ARM64, Amlogic SC2/AH212, Cortex-A55 ×4, 1,9 GiB RAM, XFCE/X11 via LightDM, usuário `arthur` e sessão gráfica `:0`.
- Na BTV13, `ip route get 10.4.254.202` escolheu `eth0`, origem `10.4.2.190`; `wlan0` tinha `10.4.252.1` e `eth0` dois IPs. **Não presumir IP de origem permanente**; verificar leases/rotas antes de ACLs. Não alterar interfaces nesta fase.
- Chromium oficial Debian instalado; testes de vídeo local H.264 720p e 1080p satisfatórios em reprodução visual. Não demonstrada aceleração por hardware por nome exato de decoder; 24 h ainda não ensaiadas.
- Caddy não estava instalado na 009-A e as portas 80/443 não constavam como ouvintes no host naquele diagnóstico; confirmar novamente antes de intervenção.

## 3. Topologia pretendida

```text
BTV13 (Chromium, conta arthur)  ── TLS validado, porta 443 ──┐
Estação do operador autorizada ── TLS validado, porta 443 ──┤
                                                             ▼
                                              Caddy no utilities
                                              bind 10.4.254.202:443
                                              CA interna persistente
                                              allowlist/ACL de origem
                                                             │
                                              HTTP apenas dentro do host
                                                             ▼
                                               127.0.0.1:8080
                                                             ▼
                                               Docker / FastAPI
                                               SQLite e mídias atuais
```

O servidor do Caddy deve responder somente ao destino/Host aprovados. Restringir **também** a origem à BTV13 piloto e à estação administrativa aprovada, preferencialmente com controles de firewall/rede e adicionalmente no proxy; não confiar exclusivamente em ACL IP para autenticação. Avaliar IPv6 para não abrir uma rota paralela inadvertida. Não quebrar outros serviços do host; verificar configuração existente antes de qualquer alteração.

## 4. Certificação e confiança

1. Para o endereço `https://10.4.254.202`, o Caddy pode emitir certificados por `tls internal` sem depender de DNS público. Na verificação operacional, exigir SAN IP correspondente, período de validade, cadeia assinada pela CA interna e renovação normal.
2. Preservar **duravelmente** os dados de PKI do Caddy, com acesso restrito ao usuário do serviço. A chave privada da raiz e o restante da PKI **não** entram no repositório, logs, relatórios, nem nas TVs. Definir backup, restauração, custódia e revogação/rotatividade da CA; perda da CA pode exigir distribuição de nova raiz a todos os clientes.
3. Obter a **raiz pública**, por exemplo no serviço systemd convencional em `/var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt`, mas verificar o caminho real antes de usar. Transferir por canal autenticado, comparar fingerprint SHA-256 no servidor e na TV e só então adicionar ao trust store aprovado do Debian (`update-ca-certificates`). Chromium pode requerer validação adicional do trust store do navegador; testar acesso real, sem `-k`, `--ignore-certificate-errors`, flags para suprimir intersticial ou exceções manuais.
4. Validar de um cliente **não confiável** que o certificado é rejeitado; e do cliente aprovado que `curl` e Chromium validam a cadeia. `GET /health` sozinho não comprova autenticação, cookies nem proteção das rotas.
5. Não habilitar HTTP/80 ou redirecionamento automático do Caddy sem decisão operacional específica. Para um hostname por IP, cuidado com verificações de SNI (clientes podem não enviar SNI para IP); confirmar na prática em vez de ativar `strict_sni_host` indiscriminadamente.

## 5. Aplicação e cabeçalhos de proxy — ponto crítico

A configuração operacional pretendida, **somente após G1/G2**, é:

```text
SIGNAGE_BIND_IP=127.0.0.1
SIGNAGE_PORT=8080
SESSION_COOKIE_SECURE=true
LOCAL_AUTH_TEST_MODE=false
FORWARDED_ALLOW_IPS=<IP_EXATO_DO_PEER_DE_PROXY_COMPROVADO>
```

Não escrever `.env` no Git, não revelar valores operacionais confidenciais e não alterar essas variáveis enquanto o HTTPS validado não estiver pronto. O FastAPI verifica `request.url.scheme` nas rotas protegidas; o Caddy entrega HTTP ao backend e o Uvicorn precisa receber `X-Forwarded-Proto: https` de um **peer comprovadamente confiável**. A variável `FORWARDED_ALLOW_IPS` não pode ser `*`, CIDR, IP da TV nem de toda a LAN; o `AuthSettings` atual aceita apenas IP(s) explícito(s). Nunca fixar um IP de gateway Docker por suposição: observar o endereço de origem **efetivamente visto pelo processo Uvicorn** durante uma requisição de teste. Se esse peer representar uma fronteira compartilhada e insegura, reavaliar arquitetura/conectividade antes de confiar nele.

O Caddy deve sobrescrever, e não confiar em valores vindos da TV, os cabeçalhos relevantes `X-Forwarded-Proto`, `X-Forwarded-For` e `X-Forwarded-Host`, e remover `Forwarded` não utilizado. Para acesso direto cliente → Caddy, o IP real é o peer TCP recebido pelo Caddy; caso exista proxy adicional, redesenhar a cadeia e a política de confiança. `Host` externo deve ser o IP aprovado, não arbitrário. Testar repetição e valores malformados dos cabeçalhos.

Os limites por origem do login e de ativação dependem de `request.client.host`. Validar com clientes/origens realmente distintas e verificar resistência a spoofing de XFF; não esgotar limites contra contas reais inadvertidamente.

## 6. Esboço ilustrativo do Caddyfile (NÃO pronto para implantação)

Exemplo para orientar a geração do arquivo versionável `deploy/caddy/Caddyfile.pilot.example` durante a 009-B1. **Validar a sintaxe com a versão efetivamente escolhida, ajustar ACLs e não copiar às cegas para `/etc/caddy/Caddyfile`**:

```caddyfile
{
    auto_https disable_redirects
}

https://10.4.254.202 {
    bind 10.4.254.202
    tls internal

    # Exemplo para piloto com Ethernet; adicionar origem administrativa
    # somente depois de verificá-la e obter aprovação da rede.
    @piloto remote_ip 10.4.2.190
    handle @piloto {
        reverse_proxy 127.0.0.1:8080 {
            header_up X-Forwarded-Proto https
            header_up X-Forwarded-For {remote_host}
            header_up X-Forwarded-Host 10.4.254.202
            header_up -Forwarded
            header_up -X-Real-IP
        }
    }
    handle {
        respond "Acesso não autorizado" 403
    }
}
```

A rota administrativa precisará de IP permitido próprio e confirmado. `remote_ip` considera o IP TCP observado pelo Caddy, que pode não ser o informado anteriormente após mudanças de rede ou NAT. O teste de porta 443 deve confirmar que não foram abertas interfaces inesperadas. Não usar a configuração ilustrativa como licença de exposição institucional.

## 7. Entregáveis e divisão da 009-B

### 009-B1 — Preparação versionável, sem instalação (Codex)

- Criar arquivo **exemplo**, não operacional, de Caddyfile e documentação de configuração, testes de segurança/integração relevantes e checklist de rollback.
- Inspecionar as restrições atuais de `AuthSettings`, Uvicorn, middleware e rotas. Preservar código da ETAPA 008, alterando-o somente se um teste reproduzível demonstrar falha real e se a mudança mínima for autorizada.
- Nenhum `sudo`, instalação Caddy, serviço systemd, alteração de `.env`, ACL/firewall, trust store, certificados, deploy, commit ou push pelo Codex.
- Testes estáticos e suite local só se disponíveis sem privilégio; relatar zero testes Python se não puder executar.

### 009-B2 — Implantação por operador, somente com aprovação de G1

- Confirmar autorização da rede e acesso à porta 443, clientes permitidos, inspeção de listeners, política de certificados, janela de manutenção, rollback, backup conjunto e preservação do SQLite/mídias.
- Instalar Caddy a partir da fonte de pacotes aprovada, validar configuração e limitar à borda de rede; não publicar `/app` diretamente.
- Confirmar PKI/cadeia e instalar apenas raiz pública verificada na BTV13/estação autorizada.
- Confirmar peer ASGI observado, testar cabeçalhos e limites, aplicar configuração segura e recriar container; `restart` sozinho não recarrega `.env`.
- Comprovar login, CSRF, emissão e ativação, cookies `__Host-...`, manifesto, isolamento, mídia Range 206/416, revogação, atualização e rollback.
- Só depois: Chromium quiosque sob `arthur`, perfil privado 0700, sessão XFCE existente e **um único** mecanismo de autostart, sem root/`--no-sandbox` ou flags para ignorar TLS. Ensaiar ≥2 h e depois 24 h.

## 8. Portões de aceitação

- **G0:** documentação e baseline Git limpas (já confirmado na 009-A).
- **G1:** decisão CA/IP aprovada, **mais** autorização de exposição controlada da porta 443, IPs efetivos do piloto/admin, backup+rollback e topologia de confiança definida.
- **G2:** TLS válido no IP, CA verificada nos clientes, cliente não confiável recusado, Caddy ACL comprovada, peer Uvicorn comprovado, Secure cookies, CSRF, Range, manifesto e autorização por tela testados.
- **G3:** vídeo real 1080p, imagem e playlist no Chromium via HTTPS, autoinício e recuperação, ensaios operacionalmente registrados (testes locais H.264 anteriores são evidências preliminares, não G3 completo).
- **G4:** documentação refletindo apenas evidência real, aprovação de rollback/restauração conforme escopo, auditoria e versionamento final.

## 9. Pendências explícitas

Sem DNS/certificado institucional; aprovação de acesso na LAN ainda pendente. Endereço da estação administrativa e permissões do firewall ainda não identificados. Peer Uvicorn através da ponte Docker ainda não comprovado. Falta comprovar nome do decodificador H.264, teste prolongado, CA confiável e configuração quiosque. O teste formal de restauração conjunta permanece pendente. A revogação de sessão não remove bytes já recebidos. **Não usar HTTP com credenciais na LAN nem enfraquecer TLS para cumprir cronograma.**

## 10. Referências oficiais consultadas

- https://caddyserver.com/docs/automatic-https
- https://caddyserver.com/docs/caddyfile/directives/tls
- https://caddyserver.com/docs/caddyfile/directives/reverse_proxy
- https://caddyserver.com/docs/running
- https://uvicorn.dev/deployment/
- https://uvicorn.dev/settings/
