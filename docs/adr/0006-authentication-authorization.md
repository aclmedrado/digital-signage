# ADR 0006 — Autenticação, sessões e autorização administrativa

**Status:** Aceito  
**Data:** 2026-10-14  
**Projeto:** Digital Signage

## 1. Contexto

As ETAPAS 001–005 entregaram FastAPI, SQLite persistente, administração de telas, biblioteca de vídeos/imagens e entrega de arquivos. Atualmente, a interface `/admin`, a API de telas e a entrega das mídias não possuem autenticação. A ETAPA 006 deve proteger o sistema antes de sua liberação institucional, mantendo a arquitetura simples: uma aplicação FastAPI, um container e SQLite.

O servidor utiliza atualmente o binding `10.4.254.202:8080`, por HTTP. A rede interna não substitui TLS, autorização nem proteção contra CSRF. Este endereço **não deve ser utilizado para transmitir credenciais ou cookies de sessão em HTTP**.

## 2. Decisão principal

Implementar autenticação por usuário e senha com **sessões opacas mantidas no servidor**, persistidas no SQLite. Usar cookies de sessão no navegador, proteção CSRF nos formulários e verificações explícitas de autenticação/autorização nas rotas protegidas. Não implementar JWT, OAuth2, LDAP/AD, SSO, Redis, segundo serviço ou frontend JavaScript nesta etapa.

## 3. Usuários e papéis

- Criar entidade `User` com identificador, username único normalizado, hash de senha, papel (`admin` inicialmente; estrutura compatível com `viewer` para testes e evolução), estado ativo e timestamps UTC.
- Não armazenar nem registrar senhas em texto claro; não registrar hashes em logs.
- Criar inicialmente apenas um administrador por **comando administrativo interativo dentro do container**, executado pelo operador, com senha solicitada via entrada oculta (`getpass`) e confirmação. Não aceitar senha como argumento de linha de comando nem fornecer credencial padrão ou cadastro público.
- O bootstrap deve ser idempotente/seguro: jamais sobrescrever usuário existente, exigir intervenção explícita para qualquer operação de recuperação e reportar instruções seguras ao operador.
- Somente usuários ativos com papel `admin` poderão usar o painel, a API de telas e o endpoint de mídias existente. Reservar a expansão dos papéis para uma etapa futura. A presença de um cookie não é autorização por si só.

## 4. Armazenamento de senhas

- Usar Argon2id, com biblioteca mantida e parâmetros não inferiores às recomendações atuais da OWASP (referência mínima: `m=19456 KiB`, `t=2`, `p=1`), adequados à memória do servidor.
- Pode-se usar `pwdlib[argon2]` ou `argon2-cffi`, com versões fixadas e documentadas.
- Usar método seguro de verificação de senha, inclusive para usuário inexistente, evitando diferenças triviais de comportamento que facilitem enumeração.
- Exigir senha inicial forte; definir e documentar critério compatível com o uso institucional. Não exibir a senha em relatórios, comandos ou testes operacionais.

## 5. Sessões

- Criar entidade de sessão persistida no SQLite, com vínculo ao usuário, hash de token opaco, expiração absoluta, último acesso, data de criação e estado de revogação/remoção.
- Gerar identificador aleatório por CSPRNG com ao menos 256 bits de entropia; **persistir apenas seu hash**, não o token bruto. O token é entregue somente no cookie do navegador.
- Aplicar timeout absoluto inicial de 8 horas e de inatividade inicial de 30 minutos, ambos validados pelo servidor, não apenas pelo navegador. Os prazos deverão ser configuráveis.
- Logout via **POST protegido por CSRF**, revogando a sessão no servidor e expirando o cookie. Invalidação deve funcionar mesmo se o cookie tiver sido copiado.
- Criar sessão nova após login, nunca promovendo/reaproveitando uma pré-sessão como sessão autenticada. Rejeitar identificadores desconhecidos; não aceitar sessão em URL ou query string.
- Cookies: `HttpOnly`, `SameSite=Lax` (ou mais restritivo), `Path=/`, sem `Domain`; `Secure=true` por padrão. Em contexto HTTPS, preferir nome com prefixo `__Host-`. Não incluir identificador, senha ou CSRF em URL/logs.

## 6. CSRF

- Proteger todos os métodos que alteram estado autenticados por cookie: formulários de telas, alternância de estado, upload de mídia, logout e operações de escrita da API (`POST`, `PATCH` e outras futuras).
- Usar token CSRF aleatório, vinculado a sessão autenticada, validado no servidor por comparação resistente a diferenças de tempo. Em HTML, enviá-lo em campo oculto; na API, exigir cabeçalho explícito `X-CSRF-Token` para requisições com cookie.
- Também proteger o formulário de login contra login CSRF mediante **pré-sessão/challenge temporário**, com cookie e token vinculados e prazo curto. Após autenticação, invalidar a pré-sessão e emitir sessão autenticada completamente nova.
- `SameSite` não substitui a validação CSRF. Requisições sem token, inválidas ou expiradas devem retornar 403 e não alterar dados.
- Não aceitar mudança de estado via GET. Não publicar tokens CSRF em URLs, logs ou documentos de operação.

## 7. Política de acesso às rotas

- Públicas somente as verificações de saúde (`GET /`, `GET /health`), recursos estáticos estritamente necessários à tela de login e `GET/POST /admin/login` com proteção adequada.
- `GET /admin` e todas as rotas `/admin/screens` e `/admin/media`: exigir usuário ativo com papel `admin`. GET não autenticado pode redirecionar à tela de login; alterações não autenticadas devem falhar sem modificar estado.
- Todas as rotas `/api/screens` (inclusive GET) devem exigir administrador e responder **401 JSON** sem autenticação ou **403 JSON** sem permissão. Operações de escrita também exigem CSRF. Esta é uma **mudança intencional de contrato** em relação às etapas anteriores.
- `GET /media/{media_id}/file` deve exigir administrador nesta etapa; preservar `FileResponse` e HTTP Range 206/416 para quem estiver autorizado. Não deixar catálogo privado exposto apenas por URL conhecida.
- Documentação interativa da API (`/docs`, `/redoc`, `/openapi.json`), caso habilitada, deve ficar protegida ou desabilitada para acesso anônimo; não bloquear `/health`.
- O futuro player das TV Boxes terá um mecanismo de acesso **separado e limitado à mídia publicada**, a definir quando implementarmos playlists/player. Não reutilizar o cookie administrativo nas TV Boxes.

## 8. Defesa adicional

- Aplicar proteção simples e testada contra tentativas repetidas de login, com limites por conta e/ou origem e janela temporal; não confiar cegamente no cabeçalho `X-Forwarded-For`.
- Evitar enumeração de usuários: mensagem genérica para credenciais incorretas. Não registrar senha, cookies, tokens CSRF ou conteúdos sensíveis.
- Preservar `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, escaping dos templates e restrições dos uploads; garantir compatibilidade do player HTML de pré-visualização e do `FileResponse`.
- Não introduzir CORS permissivo, endpoints de registro público, senhas padrão, recuperação por e-mail ou troca automática de privilégios.

## 9. Transporte seguro e implantação

- Em operação institucional, exigir HTTPS com certificado válido e `Secure=true` nos cookies. A configuração definitiva de TLS/proxy e domínio institucional requer decisão e operação próprias; **não instalar Caddy, alterar rede, firewall ou DNS automaticamente nesta etapa**.
- Para **testes controlados antes do HTTPS**, permitir excepcionalmente cookie `Secure=false` **somente** com configuração de desenvolvimento explícita, binding efetivo `127.0.0.1:8080` e acesso pelo túnel SSH (`ssh -N -L 18080:127.0.0.1:8080 ...`). Registrar essa exceção como temporária e nunca como configuração de produção.
- O operador altera `.env` manualmente após auditoria; o Codex não deve alterar segredos, `.env` operacional, binding do host nem arquivos fora do projeto.
- O comportamento padrão deve falhar de forma segura: em HTTP exposto à LAN sem TLS, **não habilitar sessões inseguras nem instruir usuários a fazer login**. Incluir verificações documentadas para `docker compose config` e para os atributos dos cookies.

## 10. Banco, backup e operação

- Acrescentar tabelas necessárias com a estratégia incremental existente (`create_all`), sem destruir/modificar dados das telas ou mídias.
- Preservar os volumes `signage-data` e `signage-media`, o usuário não-root e o healthcheck.
- Antes do deploy, executar backup consistente do SQLite e manter backup das mídias; validar futuramente a restauração conjunta de banco e arquivos.
- Não utilizar `docker compose down -v`, `docker system prune` ou comandos globais de limpeza.

## 11. Testes exigidos

- Login válido/inválido/inativo, bootstrap seguro, hash Argon2id, rate limiting.
- Sessão criada, expirada, inativa, revogada, inexistente e logout; flags e isolamento de cookies.
- CSRF válido/ausente/inválido em login, logout, telas, uploads e API; ausência de alteração de dados em requisições rejeitadas.
- Acesso anônimo e papel insuficiente a todas as rotas protegidas, inclusive entrega de arquivos e HTTP Range; saúde pública preservada.
- Regressão funcional das ETAPAS 002–005 **com autenticação e CSRF apropriados nos testes**, sem reduzir a cobertura; banco e diretório de mídias temporários.
- Nenhum teste poderá modificar os volumes de produção.

## 12. Fora do escopo

Múltiplos usuários administráveis via painel, mudança/esquecimento de senha pelo navegador, integração com IFG ID/LDAP/SSO, MFA, API key para players, publicação de playlists, player/kiosk, HTTPS/Caddy em produção e políticas avançadas de auditoria/recuperação. Podem ser propostos separadamente sem implementação nesta etapa.

## 13. Referências

- OWASP Password Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- OWASP Session Management Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- OWASP CSRF Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- FastAPI Password Hashing: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- Starlette Responses/Cookies: https://www.starlette.io/responses/
