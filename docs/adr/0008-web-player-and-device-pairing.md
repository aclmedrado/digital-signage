# ADR 0008 — Player web e pareamento seguro de dispositivos

- **Status:** Proposto — exige versionamento antes da implementação
- **Data:** 2026-10-15
- **Projeto:** Digital Signage — IFG Câmpus Inhumas
- **Escopo:** ETAPA 008
- **Dependências:** ADRs 0003 a 0007, em especial 0006 (autenticação) e 0007 (playlists)

## 1. Contexto

Até a ETAPA 007 existem cadastro de telas (`Screen`), biblioteca persistente de mídia (`MediaAsset`), playlists ordenadas (`Playlist`, `PlaylistItem`), associação por tela (`ScreenPlaylistAssignment`) e administração autenticada, autorizada e protegida por CSRF. A ETAPA 007 foi validada com 439 testes automatizados e 20 verificações operacionais; commit `32925f4`, branch `main` limpa e sincronizada.

Não existe ainda player de reprodução contínua nem identidade própria de TV Box. O acesso administrativo é feito em ambiente de teste local com `SIGNAGE_BIND_IP=127.0.0.1`, `SESSION_COOKIE_SECURE=false`, `LOCAL_AUTH_TEST_MODE=true` e túnel SSH. **Isso não autoriza publicar login, códigos de pareamento ou sessões em HTTP na LAN.** HTTPS institucional será requisito para acesso direto pelos dispositivos.

## 2. Decisão

Implementar, no mesmo serviço FastAPI e sem frameworks frontend adicionais, (a) um player HTML/CSS/JavaScript enxuto e responsivo; (b) manifesto por tela, versionado por conteúdo; (c) entrega de mídias por rota protegida, inclusive HTTP Range; e (d) pareamento de tela por código temporário, trocado por cookie de dispositivo persistente e revogável. Validar primeiro em navegador comum, via túnel SSH. A homologação física nas BTV13/H6+ não faz parte desta etapa.

A autenticação do player será **separada** da conta administrativa: o navegador do dispositivo nunca conhece usuário/senha administrativos, não precisa de token em query string e não recebe poderes sobre telas, playlists ou uploads.

## 3. Fluxos e rotas de referência

### 3.1. Administração (sessão administrativa existente)

- `GET /admin/screens/{screen_id}/player`: mostra estado do pareamento, instruções, link de prévia e ação de revogação; **não** revela sessões nem códigos já emitidos.
- `POST /admin/screens/{screen_id}/player/pairing`: gera um **novo** código aleatório de uso único, com validade de 10 minutos, e mostra-o somente na resposta protegida por `Cache-Control: no-store`; CSRF obrigatório. Gerar novo código substitui o código anterior **sem desconectar** o dispositivo atualmente pareado.
- `POST /admin/screens/{screen_id}/player/revoke`: revoga a sessão de dispositivo daquela tela e o código pendente; CSRF obrigatório e confirmação clara no formulário.
- Link de prévia para `/player/s/{slug}`, onde a sessão administrativa permite visualização, sem emitir cookie de dispositivo.

### 3.2. Ativação no dispositivo

- `GET /device/activate`: formulário público mínimo, protegido por desafio CSRF pré-sessão, sem expor dados internos.
- `POST /device/activate`: recebe código pelo **corpo POST**, aplica CSRF e limitação de tentativas, consome código válido atomicamente e emite cookie de dispositivo associado exclusivamente à tela aprovada. Redireciona para `/player/s/{slug}`.
- Sem código válido, a resposta é genérica e não revela nomes, IDs, slugs ou existência de dispositivos.
- O operador gera o código em seu painel autenticado e o digita **uma vez** no navegador do dispositivo, ou em segundo perfil de navegador para homologação. Não colocar códigos ou identificadores secretos em URLs, logs, Markdown, JavaScript persistente ou `localStorage`.

### 3.3. Reprodução

- `GET /player/s/{slug}`: entrega HTML do player somente ao administrador autenticado (prévia) **ou** a dispositivo com sessão válida vinculada precisamente àquela tela. Sem autenticação, orientar à ativação; dispositivo de outra tela não recebe o conteúdo.
- `GET /player/s/{slug}/manifest`: manifesto JSON apenas para a tela autorizada; sem dados de outras telas. Requer a mesma autorização da página.
- `GET /player/s/{slug}/media/{media_id}`: entrega apenas uma mídia que pertença, **naquele momento**, à playlist ativa associada à tela ativa autorizada. Reutiliza validação de caminho e entrega segura da ETAPA 005; deve preservar `Range: bytes=...` e HTTP 206/416. O caminho não contém credenciais.
- Rotas existentes de administração, API e `GET /media/{id}/file` **permanecem administrativas** e não passam a aceitar sessões de dispositivos.

A implementação pode acrescentar rotas auxiliares, desde que preserve esses contratos e documente a escolha. Identificadores `slug` são localizadores, **não segredos**. Separar `/device/activate` de `/player/s/{slug}` evita colisão de rota com slugs existentes.

## 4. Modelo de credenciais

Adicionar tabelas de maneira incremental, sem migração destrutiva:

- **ScreenPairingCode**: código aleatório gerado com CSPRNG de pelo menos 128 bits de entropia; armazenar somente seu hash SHA-256; FK de tela e emissor admin; emissão e expiração (10 min). Uma emissão pendente por tela. Reemissão invalida a anterior. Exclusão/consumo transacional.
- **ScreenDeviceSession**: no máximo **uma sessão ativa por tela** (preferencialmente `screen_id` como PK), hash SHA-256 do token opaco CSPRNG de pelo menos 256 bits, emissão, expiração absoluta em até 90 dias e revogação/substituição. Cookie persistente no navegador com expiração correspondente. Repareamento substitui/revoga a sessão antiga **somente na consumação bem-sucedida** do novo código; não na sua emissão.
- **Limitação de tentativas de ativação**: persistente por origem confiável (sem aceitar `X-Forwarded-For` de cliente arbitrário); referência de política: até 10 falhas por origem em 15 minutos, HTTP 429 após limite, mensagens genéricas. Reutilizar mecanismos existentes quando apropriado, sem contaminar bloqueios de login administrativo.

A validação de todos os tokens, validade, revogação, tela associada e estado da tela ocorre no **servidor**. Hashes não se tornam credenciais aceitas. Nunca armazenar o token em claro no banco, em arquivos de configuração ou em logs.

O cookie de dispositivo utiliza `HttpOnly`, `SameSite=Lax`, `Path=/`, ausência de `Domain` e `Secure=true` no HTTPS com prefixo `__Host-`. No **modo local previamente aprovado** utiliza nome distinto sem `__Host-`, `Secure=false` e acesso estrito por túnel SSH. **Não criar novo modo de teste, não alterar o `.env` nem relaxar as regras de transporte da ETAPA 006.** O cookie administrativo não é reutilizado como credencial de dispositivo.

O pareamento é operação sensível: páginas com códigos, manifestações e respostas autenticadas devem usar `Cache-Control: no-store` e cabeçalhos de segurança compatíveis; nenhum dado secreto deve aparecer em URLs ou páginas públicas. Usar transações e rollback na emissão, no consumo e na revogação.

## 5. Manifesto e semântica da programação

Resposta de referência (campos de apresentação podem ser ajustados com testes e documentação):

```json
{
  "screen": {"slug": "tv-piloto", "name": "TV Piloto"},
  "state": "playing",
  "revision": "hash-estavel-do-conteudo-e-do-vinculo",
  "poll_after_seconds": 20,
  "items": [
    {"id": 10, "kind": "image", "duration_seconds": 15, "url": "/player/s/tv-piloto/media/4"},
    {"id": 11, "kind": "video", "duration_seconds": null, "url": "/player/s/tv-piloto/media/8"}
  ]
}
```

- Respeitar `position` de `PlaylistItem`, inclusive repetições da mesma mídia.
- Imagem usa `duration_seconds`, vídeo termina por evento `ended`; nunca cortar vídeo pelo tempo configurado da imagem.
- Manifesto `state` distingue, sem vazar detalhes internos: tela desativada, sem playlist, playlist indisponível e sequência ativa. Estados sem reprodução retornam `items: []` e mensagem neutra.
- Revisão calculada de forma determinística a partir de identidade e estado da tela, vínculo, playlist e sequência (item, mídia, ordem, duração e metadados necessários). Evitar depender exclusivamente de timestamp não atualizado ou do relógio do cliente.
- Nenhuma URL de manifesto ou mídia inclui token, senha, caminho físico ou identificadores de sessão; a autorização está no cookie `HttpOnly`.
- HTTP 401/403 não deve ser transformado em reprodução pública ou substituído por conteúdo de outra TV.

## 6. Máquina de reprodução no navegador

- Player de tela inteira com fundo neutro escuro, sem navegação administrativa; imagens e vídeos com `object-fit: contain` inicialmente, preservando proporção. HTML, CSS e JavaScript próprios, sem biblioteca de terceiros.
- Vídeos MP4/H.264 em elemento `<video muted autoplay playsinline>`, sem controles; áudio automático fica fora de escopo devido a políticas de autoplay. Não presumir aceleração de hardware.
- Carregar manifesto ao entrar e consultar atualizações periodicamente (alvo 20 segundos, tolerância a jitter e sem requisições concorrentes). Aplicar mudanças **na transição de item** para não interromper desnecessariamente um vídeo em andamento. Se tela for desativada ou acesso revogado, interromper imediatamente e limpar a mídia apresentada.
- Ao concluir o último item, retornar ao primeiro; imagem deve avançar após sua duração e vídeo por `ended`.
- Pré-carregamento apenas quando seguro e moderado; não manter todos os vídeos em memória.
- Erros de imagem, `play()` rejeitado, formato não suportado, vídeo travado, servidor indisponível ou lista vazia devem resultar em avanço controlado ou tela neutra com nova tentativa e espera. Sem loops apertados, recursão descontrolada ou reintentos por segundo. Uma sequência completamente defeituosa deve estacionar em estado de espera.
- Em perda de rede, mostrar indicação discreta e tentar reconectar com intervalo limitado. **Sem offline cache, service worker, sincronização ou promessa de reprodução desconectada** nesta etapa.

## 7. Restrições operacionais

- Manter **um** container FastAPI, Python 3.12, SQLite, SQLAlchemy, Jinja2, mídia e volumes existentes, UID/GID 10001 e healthcheck.
- Tag da imagem: `digital-signage:etapa008`.
- Sem React/Vue, Redis, Celery, broker, CDN, proxy ou banco novo.
- **Não** alterar portas/binding, `.env`, firewall, Caddy/nginx, DNS, SSH nem configurações globais do host. Acesso local por SSH é o único ambiente de homologação autorizado neste momento.
- A instalação física das BTV13/H6+, Chromium kiosk, autostart, desempenho/decodificação H.264, HTTPS institucional e publicação à rede pertencem a etapas posteriores e dependem de infraestrutura segura.
- Preservar de forma não destrutiva telas, mídias, playlists, sessões administrativas e novos dados. Usar `create_all` para tabelas novas; nenhuma alteração/destruição de tabelas existentes sem decisão explícita.

## 8. Verificação e critérios de aceitação

- Suíte completa da etapa anterior (439 testes) permanece verde e novos testes cobrem emissão, expiração, uso único, concorrência, bloqueios, revogação, substituição, cookies, sessão por tela, isolamento de dados, CSRF e proteção de todas as rotas, manifesto estável e mutável, Range 206/416, regressões.
- Testes de browser reais verificam sequenciamento imagem/vídeo, tempo de imagens, looping, atualização no limite do item, pausa em falhas, sessão de dispositivo em perfil separado e revogação; verificações de testes unitários não substituem esses testes.
- Teste com usuário administrativo via túnel SSH e com navegador/perfil separado simulando o dispositivo; manter inalterada a configuração local de segurança.
- Backup do SQLite e das mídias antes de `docker compose up -d`, testes de persistência por restart e force-recreate. Teste formal de **restauração conjunta** continua pendente até execução explícita.
- O Codex não consegue `sudo` no sandbox: pode implementar e realizar verificações estáticas, mas **não** deve alegar `pytest`, build ou validação operacional sem execução efetiva. O operador conduz essas etapas e repassa resultados.

## 9. Riscos e limites assumidos

O código temporário precisa ser digitado no navegador da TV; sem HTTPS a comunicação com uma TV real na LAN permanece proibida. A sessão tem validade absoluta e exige novo pareamento ao expirar ou ser revogada. Um dispositivo comprometido pode utilizar sua sessão até revogação; não há DRM nem atestação de hardware. Testes em navegador desktop não comprovam reprodução fluida nas BTV13/H6+. Políticas de áudio, telemetria, trabalho offline, agendamento, gestão central de quiosque e múltiplas sessões para a mesma tela estão fora do escopo.

## 10. Próximos passos

ETAPA 009: integração real de TVs, modo quiosque e, **antes de acesso por rede**, encaminhamento institucional de HTTPS com certificados válidos e credenciais seguras. Planejamento adicional poderá separar formalmente a frente de infraestrutura TLS. ETAPA 010: agendamento/planejamento de campanhas, após homologação do player.
