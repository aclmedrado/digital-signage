# ADR 0007 — Playlists e associação às telas

**Status:** Aceito  
**Data:** 2026-10-15

## 1. Contexto

O Digital Signage concluiu as etapas de infraestrutura, API de telas, painel administrativo, biblioteca de mídias e segurança administrativa (ETAPAS 001–006). O sistema dispõe de `Screen`, `MediaAsset`, SQLite persistente, FastAPI, Jinja2 e autenticação administrativa com CSRF.

É necessário organizar os materiais já cadastrados em sequências de exibição e associá-las às telas. O conteúdo prioritário é vídeo MP4/H.264, mantendo imagens JPEG, PNG, WebP e GIF. A reprodução efetiva nos dispositivos ainda não faz parte desta decisão.

## 2. Decisão

Implementar o **gerenciamento de playlists e seus vínculos com telas** no mesmo serviço FastAPI, com páginas HTML server-rendered, SQLite e operações administrativas autenticadas e protegidas contra CSRF.

- Uma playlist contém uma **lista ordenada** de referências a mídias existentes.
- A mesma mídia pode aparecer em diversas playlists e também mais de uma vez na mesma playlist.
- Uma playlist pode ser associada a **várias telas**.
- Cada tela pode ter **no máximo uma playlist associada por vez**.
- A associação é opcional; uma tela sem playlist permanece válida.
- Não copiar, converter nem duplicar os arquivos físicos ao adicioná-los às playlists.
- Não disponibilizar nesta etapa um endpoint anônimo de reprodução ou manifesto para TV Boxes.

## 3. Entidades e relações

### Playlist

Tabela sugerida: `playlists`.

Campos mínimos:

- `id`: chave primária inteira;
- `name`: texto obrigatório de 1 a 200 caracteres, após remoção dos espaços externos;
- `description`: texto opcional de até 1000 caracteres;
- `active`: booleano, padrão `true`;
- `created_at` e `updated_at`: timestamps UTC conforme o padrão atual.

Não exigir nome exclusivo; a identidade é o `id`. A interface distinguirá playlists com nomes iguais por identificador quando necessário.

### PlaylistItem

Tabela sugerida: `playlist_items`.

Campos mínimos:

- `id`: chave primária;
- `playlist_id`: chave estrangeira para `playlists.id`, obrigatória;
- `media_id`: chave estrangeira para `media_assets.id`, obrigatória;
- `position`: inteiro positivo, sequencial a partir de 1 dentro da playlist;
- `duration_seconds`: inteiro entre 5 e 600 **somente para imagem**; para vídeo deve ser `NULL`;
- `created_at`: timestamp UTC.

A ordem deve ser determinada exclusivamente por `position`, com desempate determinístico apenas defensivo.

Exigir unicidade de `(playlist_id, position)`. As operações de reordenação deverão manter essa restrição, sem posições duplicadas, inclusive durante o `flush` de SQLAlchemy.

A coerência entre `duration_seconds` e `MediaAsset.kind`, que depende de outra tabela, deve ser validada na camada de serviço, dentro da transação. Aplicar também restrições SQL locais cabíveis.

### ScreenPlaylistAssignment

Tabela sugerida: `screen_playlist_assignments`.

Campos mínimos:

- `id`: chave primária (ou `screen_id` como chave primária, se a implementação existente favorecer);
- `screen_id`: FK obrigatória para `screens.id`, **única**;
- `playlist_id`: FK obrigatória para `playlists.id`;
- `assigned_at` e `updated_at`: timestamps UTC quando pertinentes.

A unicidade de `screen_id` garante uma playlist por tela, mas não limita o número de telas que utilizam uma playlist.

Preservar o modelo `Screen` e a API de telas existente; não introduzir alteração destrutiva na tabela `screens`.

## 4. Regras de negócio

1. Playlists podem ser criadas vazias para edição, mas **não podem ser associadas a telas enquanto vazias**.
2. Somente playlists `active=true` e com pelo menos um item podem ser associadas a telas.
3. Uma playlist já associada a qualquer tela **não pode ser desativada**, a menos que seus vínculos sejam removidos antes. A tentativa deve resultar em erro de negócio claro, sem alterar dados.
4. Enquanto uma playlist estiver associada a uma ou mais telas, seu **último item não poderá ser removido**, evitando uma associação a playlist vazia.
5. Itens podem ser adicionados, removidos e reordenados. A exclusão de um **item** não remove seu `MediaAsset` nem o arquivo físico.
6. Trocar a playlist de uma tela substitui o vínculo anterior em uma única transação; desvincular remove apenas a associação.
7. A desativação de uma `Screen` existente não apaga automaticamente a associação; seu significado futuro de exibição será tratado na etapa do player.
8. A playlist pode ser editada e reordenada quando ativa ou inativa, mas não pode ser designada a telas enquanto inativa.
9. Cada playlist admite inicialmente no máximo **100 itens**, como limite simples de operação; ultrapassá-lo gera erro claro, sem inserção parcial.
10. Imagens estáticas e animadas (JPG/PNG/WebP/GIF) utilizam duração configurável, padrão **15 segundos**, mínimo 5, máximo 600. A reprodução futura de animações durante esse intervalo será especificada na etapa do player.
11. MP4 usa a **duração integral do arquivo** já validado no catálogo. Não adicionar recorte ou campo de duração editável para vídeos nesta etapa.
12. Não adicionar exclusão de playlist nem exclusão física de mídia nesta etapa; permitir **desativação** de playlist observadas as regras acima.

## 5. Ordenação e consistência

- Posições são `1..N`, sem lacunas após operações bem-sucedidas.
- Inserir item no final; remover compacta posições; subir/descer troca somente com o item adjacente.
- A implementação deve respeitar a constraint `UNIQUE (playlist_id, position)` em SQLite. Evitar trocas ingênuas de dois `UPDATE`s que falhem por colisão temporária; usar estratégia transacional com posição auxiliar livre ou outra solução simples e testada.
- Usar transações atômicas para criação, edição, inserção, remoção, reordenação, ativação e associação; rollback em falha.
- Verificar se `PRAGMA foreign_keys=ON` é efetivo em cada conexão SQLite e ajustar somente o necessário com testes. Não assumir que `FOREIGN KEY` é aplicado automaticamente por SQLite.
- Proteger operações de concorrência relevante contra inconsistências, usando restrições do banco e tratamento de conflitos, sem introduzir sistemas de fila ou locks externos.
- Preservar `created_at`, atualizar `updated_at` em mudanças relevantes e manter timestamps UTC.

## 6. Interface administrativa

Continuar com FastAPI, Jinja2, CSS local e formulários HTML tradicionais.

Páginas mínimas:

- Catálogo de playlists, com nome, status, quantidade de itens e telas associadas.
- Criação e edição de playlist.
- Detalhe da playlist: itens, ordem, tipo de mídia, duração de imagens, ações adicionar/remover/subir/descer, além de status.
- Associação/desassociação de playlist na página administrativa de uma tela, com acesso fácil a partir da lista de telas.
- Links de navegação `Telas`, `Mídias` e `Playlists` no layout compartilhado.

As alterações devem usar POST e **POST → 303 → GET** quando concluídas. Erros normais devem renderizar HTML com mensagens compreensíveis, preservando dados do formulário, sem stack trace.

Não exigir JavaScript para ordenar. Utilizar botões **Subir** e **Descer**, ocultos ou desabilitados quando não aplicáveis. Manter acessibilidade e responsividade.

## 7. Segurança

- Exigir a autenticação e autorização administrativa já existentes em **todas as rotas** desta etapa.
- Exigir a proteção CSRF existente em **todos os POSTs**.
- Não criar credenciais compartilhadas com players ou novos perfis de usuário.
- Não expor playlists ou associações por endpoints anônimos.
- Não desabilitar cookies, CSRF, CSP ou validação de sessão para fazer novos formulários funcionarem.
- Preservar o modo de testes local por `127.0.0.1:8080` e túnel SSH; não alterar `.env` ou infraestrutura global.
- Continuar sem liberação institucional até HTTPS configurado corretamente.

## 8. Persistência e implantação

Adicionar tabelas de maneira incremental pelo mecanismo existente, sem remover dados e sem migração destrutiva. Preservar `signage-data`, `signage-media`, UID/GID 10001, serviço único, healthcheck e imagem Docker `digital-signage:etapa007` conforme convenção do repositório.

Nenhuma nova dependência ou container é esperada. Qualquer necessidade inesperada deverá ser justificada antes da mudança.

## 9. Não objetivos

Ficam fora da ETAPA 007:

- Player, Chromium kiosk, sincronização com TV Box ou API de dispositivos;
- distribuição de manifesto, tokens de dispositivos e cache offline;
- agendamento por data/hora, prioridade, expiração automática e grupos de telas;
- transcodificação, thumbnails, exclusão física e edição de arquivos de mídia;
- drag-and-drop, SPA, frameworks JavaScript e frontend separado;
- HTTPS/proxy novo, alteração do sistema operacional ou serviços globais;
- novos papéis, login público e administração de usuários.

## 10. Consequências

**Positivas:** reaproveitamento seguro do acervo, composição flexível de campanhas, uma playlist compartilhada entre várias TVs, modelo relacional simples, evolução sem novo serviço e suporte claro a vídeo integral e imagens por duração.

**Limitações:** ainda não há reprodução nas TVs; as associações são apenas a configuração central no banco. Atualizações em playlists associadas passam a representar mudanças futuras no que será exibido; pré-visualização fiel e política de sincronização serão decididas na etapa do player. Sem HTTPS, a operação administrativa continua restrita ao ambiente de testes por túnel SSH.

## 11. Validação

Exigir testes isolados de banco e autorização, integridade referencial, restrições, reordenação, associações, regressão das 267 verificações anteriores e validação operacional pelo operador, inclusive preservação após restart e recriação do container.
