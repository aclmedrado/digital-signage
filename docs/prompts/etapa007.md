# ETAPA 007 — Playlists e associação às telas

## 1. Objetivo e contexto

Implementar o gerenciamento administrativo de **playlists multimídia** e sua **associação às telas** do Digital Signage.

Projeto: `aclmedrado/digital-signage`  
Diretório oficial: `/home/administrador/digital-signage`  
Branch: `main`  
Servidor: `utilities` (`10.4.254.202`)  
Ambiente: Ubuntu, Docker Compose, FastAPI, SQLAlchemy, SQLite, Jinja2.

As ETAPAS 001–006 foram concluídas, testadas e versionadas. A ETAPA 006 implementou autenticação administrativa e CSRF; o commit de sua implementação foi `a9e8b64`. Os commits de documentação desta ETAPA 007, que serão posteriores, devem estar presentes antes de iniciar a implementação.

O catálogo de mídias já contém vídeos MP4/H.264 e imagens JPG/PNG/WebP/GIF. Não refazer esse subsistema.

## 2. Pré-condições obrigatórias

**Antes de alterar qualquer arquivo:**

1. Execute `pwd`; confirme `/home/administrador/digital-signage`.
2. Leia integralmente `AGENTS.md` e `README.md`.
3. Leia `docs/STATUS.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/OPERATIONS.md` e `docs/DEPLOYMENT.md`.
4. Leia todos os ADRs pertinentes, **especialmente `docs/adr/0007-playlists-and-screen-assignments.md`**.
5. Leia integralmente este prompt.
6. Execute `git status`, `git log -5 --oneline` e confirme `main`, working tree limpa e documentos 007 versionados.
7. Inspecione modelos `Screen` e `MediaAsset`, base SQLAlchemy, configuração SQLite, inicialização de tabelas, serviços, rotas administrativas, templates, middleware de autenticação, CSRF e fixtures de testes.
8. Verifique se todas as funcionalidades e limites solicitados podem ser implementados respeitando a arquitetura real.

**Pare e reporte** se houver divergência relevante, documentos 007 não versionados ou working tree suja. Não crie exceções silenciosas.

## 3. Regras inegociáveis

- Reutilizar **FastAPI + SQLAlchemy + SQLite + Jinja2** e o serviço Docker único.
- Preservar integralmente `Screen`, `MediaAsset`, uploads, API existente, autenticação, sessões, CSRF, logout e download HTTP Range.
- Não modificar os volumes `signage-data` e `signage-media`; não remover ou zerar registros reais.
- Não exigir JavaScript, Node.js, SPA, Redis, PostgreSQL ou Alembic.
- Não implementar player, integração com TV Boxes, tokens de dispositivo, agendamentos ou exclusão física.
- Não alterar `.env`, bind, portas, SSH, firewall, UFW, sudoers, Docker daemon ou serviços alheios ao projeto.
- Não instalar pacotes no host, não contornar sudo e não usar `docker compose down -v`.
- **Não executar `git add`, `git commit` ou `git push`.**
- Ao registrar testes, diferenciar os executados dos apenas definidos; não atribuir resultados históricos à etapa atual.

## 4. Modelo de dados

Implemente as entidades do ADR 0007. Nomes sugeridos:

### `Playlist` (`playlists`)

- `id`: PK inteira.
- `name`: obrigatório, 1–200 caracteres após `strip()`.
- `description`: opcional, máximo 1000 caracteres.
- `active`: bool, padrão true.
- `created_at`, `updated_at`: UTC.

Não impor unicidade ao nome; identidade é `id`.

### `PlaylistItem` (`playlist_items`)

- `id`: PK inteira.
- `playlist_id`: FK obrigatória para playlist.
- `media_id`: FK obrigatória para mídia.
- `position`: inteiro positivo, único por playlist; posições sempre contíguas `1..N`.
- `duration_seconds`: imagem entre 5 e 600 (padrão 15); para vídeo deve ser NULL.
- `created_at`: UTC.

Uma mídia pode ocorrer em várias playlists e múltiplas vezes na mesma playlist. Usar chave primária própria em vez de PK composta por `playlist_id` e `media_id`.

### `ScreenPlaylistAssignment` (`screen_playlist_assignments`)

- `screen_id`: FK obrigatória e **única** para `screens`.
- `playlist_id`: FK obrigatória para `playlists`.
- `assigned_at` e `updated_at`, quando cabível.
- `id` próprio ou `screen_id` como PK: escolha simples e documentada.

Uma tela pode ficar sem playlist. Uma playlist pode estar ligada a várias telas.

### Banco e constraints

- Defina `UNIQUE(playlist_id, position)` e demais `CHECK`, `NOT NULL` e FKs adequadas.
- Verifique o estado real do `PRAGMA foreign_keys` do SQLite. Se necessário, habilite-o para **cada conexão** da engine usada pelo projeto, com testes; não dependa do padrão SQLite.
- Garanta importação dos novos modelos antes do `create_all()` utilizado no lifespan da aplicação.
- Adicione somente as novas tabelas, preservando as tabelas e registros existentes. **Sem migração destrutiva.**
- Faça rollback apropriado em qualquer erro e evite estados parciais.

## 5. Regras de negócio

1. Criar playlist inicialmente ativa, com `name` e `description` opcional.
2. Renomear e editar descrição sem perder itens ou associações.
3. Desativar/reativar por POST. **Não permitir desativar uma playlist associada a uma ou mais telas**: retornar erro de negócio claro e manter o estado.
4. Permitir playlist vazia no catálogo e edição, mas **não associá-la a uma tela**.
5. Não associar playlist inativa. Manter as associações anteriores intocadas em caso de tentativa inválida.
6. Adicionar `MediaAsset` existente como item; mídia inexistente deve gerar erro claro.
7. Inserir item sempre na última posição.
8. Para imagem (`kind=image`), usar `duration_seconds` de 5 a 600, com padrão 15 quando o campo for deixado vazio.
9. Para vídeo (`kind=video`), exigir `duration_seconds=NULL` e recusar com erro de validação qualquer duração explicitamente enviada; não aceitar corte: a futura reprodução será integral.
10. Limite inicial por playlist: **100 itens**, incluindo duplicatas. Exceder o limite deve falhar sem inserção.
11. Remover um item sem remover sua mídia física ou metadados de catálogo.
12. **Proibir a remoção do último item enquanto a playlist estiver associada a qualquer tela.**
13. Ao remover item permitido, compactar as posições para `1..N`.
14. Subir/descer item em uma posição por operação POST. Primeiro não pode subir; último não pode descer. Operações não aplicáveis não devem corromper dados.
15. Para cada `Screen`, permitir atribuir playlist válida, substituir a atual ou desvincular. Alterar a associação não deve modificar `Screen.active`.
16. Aceitar várias telas associadas à mesma playlist.
17. Atualizar timestamps dos registros alterados conforme o padrão de UTC existente.
18. Em caso de concorrência, usar constraints e transações, retornando mensagem compreensível quando houver conflito; não implementar sistemas externos de locks.

**ATENÇÃO À ORDENAÇÃO:** SQLite verifica a unicidade de `(playlist_id, position)` durante atualizações; não faça swap ingênuo de duas posições usando dois UPDATEs que colidam. Adote posição temporária livre ou outra estratégia transacional simples e teste reordenação/remoção de listas com várias entradas.

## 6. Serviços

Inspecione `app/services/screens.py`, `app/services/media.py`, `app/services/auth.py` e as convenções atuais. Crie um serviço pequeno e explícito para regras de playlists/associações, sem chamar a própria API via HTTP.

Os métodos de serviço deverão garantir transações, validar existência de mídias/telas, aplicar regras de estado, preservar FKs e tratar colisões.

Não introduza repository framework, CQRS, microserviço nem nova camada abstrata genérica.

## 7. Páginas e rotas administrativas

Utilizar layout/template base e o sistema de autenticação/CSRF **existente**, inclusive tokens em todos os formulários POST.

Rotas sugeridas (ajustar ao padrão do projeto sem alterar semântica):

| Método | Rota | Função |
|---|---|---|
| GET | `/admin/playlists` | Listar playlists e vínculos |
| GET | `/admin/playlists/new` | Formulário de criação |
| POST | `/admin/playlists` | Criar playlist |
| GET | `/admin/playlists/{playlist_id}` | Detalhe com itens ordenados |
| GET | `/admin/playlists/{playlist_id}/edit` | Formulário de edição |
| POST | `/admin/playlists/{playlist_id}/edit` | Alterar nome/descrição |
| POST | `/admin/playlists/{playlist_id}/toggle` | Ativar/desativar |
| POST | `/admin/playlists/{playlist_id}/items` | Adicionar item |
| POST | `/admin/playlists/{playlist_id}/items/{item_id}/remove` | Remover somente item |
| POST | `/admin/playlists/{playlist_id}/items/{item_id}/move-up` | Subir item |
| POST | `/admin/playlists/{playlist_id}/items/{item_id}/move-down` | Descer item |
| GET | `/admin/screens/{screen_id}/playlist` | Formulário de associação da tela |
| POST | `/admin/screens/{screen_id}/playlist` | Atribuir/substituir playlist |
| POST | `/admin/screens/{screen_id}/playlist/unassign` | Desvincular playlist |

Regras de HTTP:

- GET nunca modifica dados.
- Operações administrativas bem-sucedidas: POST → **303** → GET.
- Campos inválidos: HTML com mensagem clara, dados preservados, preferencialmente 422.
- Violação de regras de negócio (playlist inativa, vazia, último item, limite, playlist vinculada): HTML claro e status adequado, preferencialmente 409.
- Registros inexistentes: 404 sem traceback; reutilizar padrão visual atual de páginas não encontradas.
- Métodos indevidos: resposta adequada, sem mutação.
- Não retornar respostas JSON de validação padrão em erros normais de formulários administrativos.

A navegação deve incluir `Telas`, `Mídias` e `Playlists`. Na listagem de telas, mostrar o nome da playlist associada ou `Sem playlist`, com link de gerenciamento. Não alterar o contrato JSON da API existente `/api/screens`.

## 8. Interface de gerenciamento da playlist

No catálogo mostrar: `id`, nome, estado ativa/inativa, total de itens, total de telas associadas e ações de editar/abrir/ativar ou desativar.

No detalhe:

- Nome, descrição, status.
- Lista ordenada com posição, título da mídia, tipo e nome original.
- Imagens: duração configurada em segundos.
- Vídeos: indicação `Reprodução integral` (opcionalmente mostrar duração da mídia).
- Formulário de adição escolhendo uma mídia já existente e duração apenas para imagens; **o backend sempre decide a regra final, independentemente do HTML**.
- Ações `Subir`, `Descer`, `Remover` em formulários POST separados, com CSRF.
- Mostrar as telas vinculadas e links para associação/desassociação.

Se houver muitas mídias, uma lista simples e acessível é suficiente. Sem drag-and-drop nem JavaScript obrigatório. Reutilizar CSS local e preservar acessibilidade/responsividade.

No formulário de tela apresentar playlist atual e opções válidas. Não permitir que um valor manipulado no HTML contorne as regras do serviço.

## 9. Autorização e isolamento

As novas rotas são exclusivamente administrativas e devem respeitar autenticação, papel admin, CSRF e política de sessão da ETAPA 006.

- Navegação anônima GET: seguir o contrato existente de redirecionamento ao login.
- POST anônimo: contrato HTTP existente para não autenticados.
- POST autenticado sem CSRF: recusar com 403.
- Usuário autenticado sem papel suficiente: recusar conforme política existente.
- Não criar APIs anônimas de playlist nem abrir downloads.
- Não expor tokens, cookies de sessão ou segredos em logs.
- Manter `127.0.0.1:8080` e túnel SSH durante a fase de testes atual; não mexer no `.env`.

## 10. Testes automatizados

Criar `tests/test_playlists.py` e demais arquivos de teste apenas quando necessários, aproveitando fixtures isoladas. SQLite e mídias temporárias não devem tocar volumes reais.

Cobrir **pelo menos**:

1. Criação de playlist válida e listagem vazia.
2. Nome vazio, nome acima do limite, descrição acima do limite.
3. Edição de playlist, timestamps UTC e preservação de itens.
4. Ativação e desativação sem associações.
5. Recusa da desativação quando há tela vinculada.
6. Item com imagem, duração padrão 15 e limites 5/600.
7. Rejeição de duração 4, 601, não numérica e outros tipos inválidos.
8. Item MP4 com duração NULL e reprodução integral; não permitir duração arbitrária para vídeo.
9. Referência a mídia inexistente.
10. Mesma mídia adicionada em playlists diferentes e repetida numa playlist.
11. Limite de 100 itens, sem registro parcial ao exceder.
12. Ordem determinística, posições contíguas após adição/remoção.
13. Subir/descer itens no começo, meio e fim.
14. Restrição `UNIQUE(playlist_id, position)` e prova de swap sem colisão temporária.
15. Remoção de um item sem apagar registro MediaAsset nem arquivo físico.
16. Proibição da remoção do último item se houver associação.
17. Associação de playlist válida a uma tela e substituição atômica.
18. Várias telas usando a mesma playlist.
19. Proibição de associação de playlist vazia ou inativa.
20. Desassociação sem afetar a playlist ou os itens.
21. Tela/playlist/item inexistente, incluindo item de outra playlist.
22. Falhas de banco e rollback, sem associações ou posições parciais.
23. FKs verificadas na conexão SQLite e comportamento em referências inexistentes.
24. Rotas GET públicas não alteram dados.
25. GET anônimo protegido, POST anônimo recusado, CSRF ausente ou inválido recusado.
26. Autorização de administrador e papel insuficiente.
27. HTML escapa conteúdo malicioso inserido em nomes e descrições.
28. Formulários preservam valores e mostram mensagens claras para erros.
29. Redirecionamentos 303 e uso correto de POST para mutações.
30. A API atual de screens, biblioteca de mídias, download com Range e autenticação continuam aprovados.
31. Persistência e funcionamento das novas tabelas após inicialização repetida da app.
32. Ausência de efeitos colaterais em dados reais e regressão de toda a suíte existente.

Não usar `skip`/`xfail` para ocultar falhas. A contagem real de casos deve vir do pytest, não da contagem estática.

## 11. Docker e implantação

Adotar `digital-signage:etapa007` apenas após confirmar a convenção no Compose atual.

Não adicionar volumes ou dependências sem necessidade comprovada. Preservar serviço único, processo não-root, imagem base, healthcheck e dados existentes.

Se o Codex não conseguir usar sudo, não contornar; registrar as instruções ao operador.

Comandos operacionais para o operador, depois de revisar o relatório e realizar backup apropriado:

```bash
cd /home/administrador/digital-signage
sudo docker compose config --quiet
sudo docker compose build
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
sudo docker compose up -d
sudo docker compose ps
sudo docker compose logs --tail=100 signage-app
```

**Não executar `up` se `build` ou pytest falharem.** Não executar `down -v`.

## 12. Validação operacional pelo operador

A documentação deve deixar esta fase pendente até os testes reais ocorrerem.

Verificar, em ambiente local via SSH tunnel:

1. Tela de login e rotas administrativas continuam protegidas.
2. Criar playlist `Playlist Piloto 007`, descrição opcional.
3. Adicionar imagem existente e definir 15 segundos.
4. Adicionar vídeo MP4 existente e conferir indicação de reprodução integral.
5. Adicionar outra imagem e usar ações `Subir` e `Descer`.
6. Conferir ordenação e permanência do catálogo de mídia intacto.
7. Associar playlist à `TV Piloto`.
8. Associar **a mesma playlist** à `TV do Pátio`.
9. Confirmar dois vínculos para a mesma playlist, mas uma só playlist para cada tela.
10. Criar segunda playlist não vazia e substituir associação de uma tela.
11. Desassociar uma tela e confirmar que não altera a outra.
12. Tentar associar playlist vazia e inativa: recusa clara.
13. Tentar desativar playlist associada: recusa clara.
14. Tentar remover último item de playlist associada: recusa clara.
15. Verificar mensagens de erro e preservação de valores.
16. Confirmar rejeição CSRF em POST sem token e bloqueio anônimo.
17. Confirmar API de telas e visualização/download de mídias anteriores sem regressão.
18. Reiniciar serviço, conferir que playlists, itens e vínculos persistem.
19. Recriar container sem apagar volumes; repetir conferências.
20. Confirmar que `TV Piloto`, `TV do Pátio` e mídias existentes permanecem intactas.

**Não alegar reprodução em TV Box**, pois ainda não há player nesta etapa.

## 13. Documentação

Atualizar somente quando necessário: `README.md`, `docs/STATUS.md`, `docs/ARCHITECTURE.md`, `docs/OPERATIONS.md`, `docs/DEPLOYMENT.md`, `docs/SECURITY.md` e `docs/ROADMAP.md`.

Documentar:

- esquema e regras das novas tabelas;
- interface, navegação e URLs administrativas;
- semântica de vídeos integrais e tempo de imagens;
- regra de uma playlist por tela e playlist compartilhada;
- constraints e políticas de alteração segura;
- comandos de teste e implantação;
- situação real dos testes automatizados e operacionais;
- limites de segurança e ausência de player/dispositivo nesta etapa.

Não declarar concluída/validada operacionalmente a ETAPA 007 antes das evidências do operador.

## 14. Relatório final obrigatório

Ao concluir, apresentar:

1. Estado inicial do repositório, branch e limpeza da working tree.
2. Arquivos novos e arquivos modificados, separadamente.
3. Esquema das três entidades, FKs, UNIQUE/CHECK e conexão SQLite.
4. Serviços e validações, inclusive transações e ordenação segura em SQLite.
5. Rotas novas e alterações na navegação HTML.
6. Reutilização de sessões, autorização e CSRF existentes.
7. Testes: quantidade definida, quantidade **efetivamente executada**, resultados, warnings e bloqueios.
8. Docker: tag, volumes, permissões e comandos de implantação para o operador.
9. Regressões verificadas e ressalvas; distinguir inspeções estáticas de testes reais.
10. Documentação modificada e pendências genuínas.
11. `git diff --check`, `git diff --stat`, `git status --short`.
12. Confirmação de que não houve `git add`, `git commit`, `git push`, deploy, bootstrap ou alteração global do servidor.
13. Próxima etapa apenas sugerida, não implementada.

**Não adicionar novos commits, nem alterar arquivos após auditoria sem reportar.**
