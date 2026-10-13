# ETAPA 005 — Biblioteca de mídias: vídeos e imagens

## 1. Contexto

Projeto: Digital Signage  
Repositório: `aclmedrado/digital-signage`  
Diretório oficial: `/home/administrador/digital-signage`  
Branch principal: `main`

Ambiente de implantação atual:

- hostname: `utilities`;
- servidor: `10.4.254.202`;
- Ubuntu 26.04.1 LTS;
- Docker Engine e Docker Compose;
- aplicação FastAPI;
- SQLite com volume persistente;
- interface administrativa Jinja2.

As ETAPAS 001 a 004 foram concluídas e validadas operacionalmente.

A ETAPA 004 foi registrada no commit `1d0e394`.

O principal usuário do sistema produz campanhas prioritariamente em formato MP4.

Nesta etapa construiremos a biblioteca de mídias que futuramente alimentará as playlists das TVs.

## 2. Instruções iniciais obrigatórias

Antes de modificar arquivos:

1. Execute `pwd` e confirme o diretório oficial.
2. Leia integralmente `AGENTS.md`.
3. Leia `README.md`.
4. Leia `docs/STATUS.md`.
5. Leia `docs/ARCHITECTURE.md`.
6. Leia os ADRs existentes.
7. Leia especialmente `docs/adr/0005-media-storage.md`.
8. Execute `git status`.
9. Confirme que a working tree está limpa.
10. Inspecione os arquivos do projeto e a configuração Docker.
11. Identifique os mecanismos existentes de banco, templates, rotas, serviços e testes.

Não presuma que arquivos ou funcionalidades existem.

Se houver divergência relevante entre a documentação e o código, pare e reporte antes de alterar arquivos.

## 3. Objetivo

Implementar uma biblioteca unificada de mídias.

O administrador deverá conseguir, pelo navegador:

1. Abrir o catálogo.
2. Enviar vídeos MP4.
3. Enviar imagens.
4. Informar um título.
5. Visualizar mídias cadastradas.
6. Consultar os metadados.
7. Pré-visualizar imagens e vídeos.
8. Receber mensagens claras quando o arquivo for inválido.

O servidor deverá preservar os arquivos e os metadados após recriação do container.

## 4. Fora do escopo

NÃO implementar:

- autenticação ou usuários;
- autorização;
- playlists;
- programação de exibição;
- associação mídia-tela;
- reprodução automática na TV Box;
- Chromium kiosk;
- heartbeat;
- grupos de TVs;
- exclusão de mídia;
- transcodificação;
- geração automática de versões 720p/1080p;
- armazenamento em nuvem;
- Redis;
- PostgreSQL;
- Alembic;
- novo container;
- frontend JavaScript independente;
- Docker privilegiado.

A autenticação, autorização e proteção CSRF deverão ser tratadas obrigatoriamente antes da liberação institucional. Não alegar que a interface atual é segura para acesso amplo.

## 5. Formatos

### Vídeo — prioridade principal

Aceitar `.mp4` com:

- contêiner MP4;
- vídeo H.264;
- pixel format 8-bit compatível, preferencialmente `yuv420p`;
- resolução máxima inicial 1920 × 1080;
- taxa de quadros máxima inicial 30 FPS;
- áudio AAC opcional.

Não aceitar silenciosamente H.265, AV1 ou outros codecs na implementação inicial.

Quando houver incompatibilidade, retornar mensagem clara ao usuário, informando a razão.

Não transcodificar automaticamente.

### Imagens

Aceitar:

- `.jpg`;
- `.jpeg`;
- `.png`;
- `.webp`;
- `.gif`.

Preservar a possibilidade de imagens animadas em WebP ou GIF, sem converter todas as animações automaticamente para imagem estática.

### SVG

SVG permanece como requisito previsto, mas **não será aceito como upload bruto nesta etapa**.

Documentar essa decisão e apresentar uma mensagem apropriada se o usuário tentar enviar SVG.

Não acrescentar bibliotecas de sanitização ou renderização de SVG sem uma nova decisão de segurança.

Não expor conteúdo SVG não confiável diretamente no navegador.

## 6. Limites

Limites iniciais configuráveis:

- `MAX_VIDEO_UPLOAD_MB=250`
- `MAX_IMAGE_UPLOAD_MB=10`
- `MAX_IMAGE_PIXELS=20000000`

Interpretar os limites de tamanho de arquivo como MiB (1024 × 1024 bytes) e documentar isso.

Aplicar validação pelo tamanho efetivamente recebido, não apenas por cabeçalhos HTTP.

Recusar arquivos vazios e arquivos cujo tamanho exceder o limite.

Não carregar o vídeo completo na memória.

Realizar leitura incremental em blocos, por exemplo de 1 MiB.

Estabelecer limites razoáveis adicionais para análise de imagens animadas e recursos computacionais, documentando-os e cobrindo-os com testes.

Não confiar no `Content-Length` nem no `Content-Type` do cliente.

## 7. Modelo de dados

Adicionar uma nova entidade SQLAlchemy chamada `MediaAsset`.

Tabela sugerida: `media_assets`.

Campos mínimos:

- `id`: inteiro, chave primária;
- `title`: string obrigatória;
- `kind`: `video` ou `image`;
- `original_filename`: nome original, utilizado somente para exibição;
- `stored_filename`: identificador físico único;
- `mime_type`: tipo validado;
- `size_bytes`: tamanho;
- `width`: largura;
- `height`: altura;
- `duration_seconds`: duração para vídeos, nulo para imagens;
- `video_codec`: codec para vídeos, nulo para imagens;
- `audio_codec`: codec de áudio para vídeos, nulo quando ausente;
- `created_at`: timestamp UTC.

É permitido adicionar metadados úteis, como SHA-256, desde que não aumentem desnecessariamente a complexidade.

Não modificar os campos existentes da tabela `screens`.

Criar a nova tabela usando a estratégia atual da aplicação, respeitando o ADR de SQLite.

Não introduzir Alembic nesta etapa.

## 8. Persistência física

Manter o volume existente:

`signage-data:/app/data`

Adicionar volume nomeado:

`signage-media:/app/media`

Não alterar nem remover o volume SQLite existente.

A aplicação continuará executando como usuário não-root, UID/GID 10001.

Preparar `/app/media` com permissões adequadas no Dockerfile, sem `chmod 777` e sem executar permanentemente como root.

Os arquivos enviados deverão receber nomes internos gerados pelo sistema, por exemplo com UUID.

Nunca utilizar diretamente o nome original para definir caminhos de armazenamento.

Não permitir escrita fora de `/app/media`.

Não montar diretórios amplos do host.

## 9. Upload e validação

Utilizar `UploadFile` do FastAPI.

O upload deve:

1. receber título e arquivo;
2. validar o título;
3. verificar extensão permitida;
4. aplicar limite de tamanho durante a leitura;
5. escrever em arquivo temporário controlado;
6. validar conteúdo e metadados;
7. gerar nome interno único;
8. mover o arquivo validado para o armazenamento definitivo;
9. registrar os metadados no SQLite;
10. responder com redirecionamento para o catálogo.

Deve existir limpeza dos arquivos temporários em sucesso e falha.

Se o registro no banco falhar, remover o arquivo definitivo recém-criado para evitar inconsistência.

Usar nomes imprevisíveis e impedir path traversal, inclusive com nomes contendo `../`, barras e outros caracteres especiais.

Não construir comandos shell utilizando nomes originais.

Erros esperados de validação devem produzir mensagens HTML compreensíveis, sem traceback para o usuário.

## 10. Inspeção de vídeo com ffprobe

Adicionar à imagem Docker somente o necessário para disponibilizar `ffprobe` e suas dependências.

Preferir os pacotes mantidos pela distribuição base da imagem.

Não instalar FFmpeg nem dependências da aplicação no host Ubuntu.

Executar `ffprobe` por `subprocess` com lista de argumentos, `shell=False` e timeout finito.

A entrada será sempre um arquivo local temporário controlado pela aplicação.

Utilizar a saída JSON do `ffprobe` para extrair:

- formato;
- codec de vídeo;
- codec de áudio, se existente;
- largura;
- altura;
- duração;
- taxa de quadros.

Tratar corretamente:

- vídeo sem áudio;
- ausência de trilha de vídeo;
- duração inválida;
- erro do processo;
- timeout;
- JSON inválido;
- codecs incompatíveis;
- arquivo truncado ou não reconhecido.

Não iniciar transcodificação nesta etapa.

Limitar também a quantidade de saída capturada do processo quando apropriado.

## 11. Validação de imagens

Adicionar Pillow com versão fixada.

Confirmar o formato real da imagem, suas dimensões e seu limite de pixels.

Rejeitar imagens corrompidas, arquivos falsamente nomeados como imagem ou conteúdo incompatível com a extensão.

Tratar adequadamente imagens animadas GIF/WebP.

Evitar descompressão excessiva ou processamento ilimitado de quadros.

Não depender exclusivamente do MIME enviado pelo navegador.

## 12. Entrega dos arquivos

Criar endpoint semelhante a:

`GET /media/{media_id}/file`

O identificador deverá ser resolvido a partir do banco de dados.

Não aceitar caminho arbitrário na URL.

Retornar 404 para mídia inexistente.

Usar tipo MIME validado e cabeçalhos seguros.

Utilizar `FileResponse` do Starlette/FastAPI, mantendo suporte a HTTP Range para MP4.

Testar uma requisição contendo:

`Range: bytes=0-99`

Para arquivo suficientemente grande, verificar:

- HTTP 206;
- `Content-Range` coerente;
- corpo com 100 bytes;
- `Accept-Ranges: bytes`.

Também testar intervalo inválido, observando o comportamento documentado de FileResponse.

Não criar serviço externo de streaming.

## 13. Interface administrativa

Utilizar o padrão Jinja2 já adotado.

Criar:

- `GET /admin/media`: catálogo;
- `GET /admin/media/new`: formulário;
- `POST /admin/media`: upload.

As rotas administrativas devem permanecer separadas das rotas de entrega física dos arquivos.

### Catálogo

Exibir:

- título;
- tipo;
- nome original;
- tamanho;
- dimensões;
- duração, quando aplicável;
- data de envio;
- ação de pré-visualização.

Ordenar por identificador ou data de criação, de maneira determinística.

### Formulário

Campos:

- título;
- arquivo.

O campo de arquivo deverá indicar os formatos e limites suportados.

Deve existir tratamento HTML para falhas de validação.

Em sucesso, seguir:

POST → Redirect 303 → GET.

### Pré-visualização

Para imagens, usar elemento HTML `<img>` com URL da mídia.

Para vídeos, usar elemento HTML `<video>` com controles e pré-carregamento apenas de metadados.

A pré-visualização de vídeo não deverá reproduzir automaticamente com som.

Preferir `muted` e `preload="metadata"`.

Evitar carregar todos os vídeos integralmente ao exibir o catálogo.

Reaproveitar:

- `base.html`;
- CSS existente;
- estrutura do painel;
- serviços e sessões existentes.

Não utilizar CDN, React, Vue ou Node.js.

Manter a interface responsiva.

## 14. Segurança operacional

A aplicação ainda não possui autenticação nem proteção administrativa CSRF.

Por isso:

- não considerar o upload adequado para acesso institucional amplo;
- não expor a aplicação à Internet;
- não ampliar a publicação de portas;
- manter o acesso de teste restrito a operadores confiáveis;
- registrar explicitamente esse risco no STATUS e na documentação de operação.

O operador decidirá antes do deploy se o binding atual pode permanecer ou se deverá ser alterado para loopback com acesso via túnel SSH.

Não modificar silenciosamente o `.env` local.

Não modificar automaticamente firewall, UFW, SSH, sudoers, grupos ou configurações globais do Docker.

Não tentar contornar restrições de sudo.

## 15. Preservação do projeto existente

Todos os endpoints das etapas anteriores devem continuar funcionais.

Preservar:

- API de telas;
- painel administrativo de telas;
- SQLite;
- volume `signage-data`;
- registros existentes;
- healthcheck;
- usuário não-root.

Não reestruturar código existente sem necessidade diretamente relacionada à ETAPA 005.

Não implementar migrations destrutivas.

## 16. Testes automatizados

Criar testes com banco SQLite temporário e diretório de mídias temporário.

Os testes não poderão ler, modificar nem remover arquivos ou registros reais de produção.

Cobertura mínima:

1. Catálogo vazio.
2. Formulário de upload.
3. Upload válido de JPEG.
4. Upload válido de PNG.
5. Upload válido de WebP.
6. Upload válido de GIF.
7. Upload válido de MP4 H.264.
8. Upload de MP4 sem áudio.
9. Identificação de metadados e duração.
10. Arquivo com extensão inválida.
11. Arquivo com extensão permitida e conteúdo falso.
12. Arquivo vazio.
13. Imagem corrompida.
14. MP4 inválido.
15. Codec incompatível.
16. Arquivo acima do limite, com limite reduzido na configuração de teste.
17. Imagem acima do limite de pixels.
18. Tratamento de timeout do ffprobe.
19. Nome de arquivo malicioso ou tentativa de path traversal.
20. Armazenamento com nome UUID.
21. Persistência e recuperação dos metadados.
22. Entrega de arquivo com HTTP 200.
23. Entrega MP4 com HTTP 206 para Range válido.
24. Tratamento de Range inválido.
25. Mídia inexistente retornando 404.
26. Limpeza de temporários em caso de falha.
27. Rollback e ausência de arquivo órfão quando o banco falhar.
28. Tentar upload SVG deve resultar em rejeição explícita e segura.
29. Confirmação de que os caminhos de teste são isolados dos volumes de produção.
30. Regressão dos testes anteriores.

Para gerar vídeos sintéticos de teste, preferir FFmpeg disponível dentro do container e arquivos temporários pequenos.

Não adicionar arquivos MP4 de teste grandes ao Git.

O resultado final deverá reportar a quantidade efetiva de testes executados.

## 17. Testes Docker

A imagem deverá ser atualizada para:

`digital-signage:etapa005`

Preservar um único serviço:

`signage-app`

Executar ou orientar execução de:

```bash
sudo docker compose config --quiet
sudo docker compose build
sudo docker compose run --rm signage-app pytest -q -p no:cacheprovider
sudo docker compose up -d
sudo docker compose ps
sudo docker compose logs --tail=100 signage-app
```

Se o ambiente do Codex impedir acesso ao Docker por sudo, não contornar.

Registrar os comandos para execução pelo operador.

Não declarar testes não executados como aprovados.

## 18. Validação manual

Depois da implantação, o operador deverá:

1. Acessar `/admin/media`.
2. Confirmar a existência do catálogo.
3. Enviar uma imagem válida.
4. Enviar um MP4 H.264 real.
5. Confirmar que ambos aparecem no catálogo.
6. Conferir título, formato e metadados.
7. Pré-visualizar a imagem.
8. Reproduzir o vídeo pelo navegador do computador.
9. Verificar uma requisição HTTP Range.
10. Tentar enviar um arquivo inválido.
11. Reiniciar o container.
12. Confirmar que os registros e arquivos permanecem disponíveis.
13. Recriar o container sem remover volumes.
14. Confirmar novamente a persistência.
15. Confirmar que a TV Piloto continua cadastrada.
16. Verificar espaço em disco e volume persistente.

Não usar `docker compose down -v`.

Não executar comandos globais de limpeza Docker.

## 19. Documentação

Atualizar somente o necessário:

- `README.md`;
- `docs/STATUS.md`;
- `docs/ARCHITECTURE.md`;
- `docs/DEPLOYMENT.md`;
- `docs/OPERATIONS.md`;
- `docs/SECURITY.md`, se necessário;
- `.env.example`.

Documentar:

- novos formatos;
- limites;
- perfil MP4 suportado;
- armazenamento das mídias;
- volume Docker;
- comandos de operação;
- testes;
- restrições de segurança;
- situação atual do SVG;
- pendências relativas à TV Box;
- procedimentos básicos de backup dos volumes.

Não declarar validação operacional antes de receber os resultados reais do operador.

## 20. Git

Não executar:

```bash
git add
git commit
git push
```

Não criar branch nova.

Não modificar o histórico Git.

A auditoria e o versionamento serão executados pelo operador.

## 21. Relatório final obrigatório

Ao terminar, apresente:

### Estado inicial
Descreva o repositório e as condições encontradas.

### Arquivos criados
Liste todos.

### Arquivos modificados
Liste todos.

### Modelo MediaAsset
Explique campos, restrições e tabela.

### Armazenamento
Explique volumes, caminhos, permissões e limpeza de arquivos.

### Vídeos
Explique a validação MP4, codecs, limites e funcionamento do ffprobe.

### Imagens
Explique os formatos, os limites e o tratamento de GIF/WebP e SVG.

### Interface
Liste as novas rotas e os recursos implementados.

### Segurança
Informe controles implementados e riscos que permanecem.

### Testes
Apresente quantidade executada, sucessos, falhas e warnings.

### Docker
Informe imagem, serviço, volumes e alterações realizadas.

### Git
Apresente:

```bash
git status --short
git diff --stat
git diff --check
```

### Pendências
Diferencie pendências de implementação, de testes e de validação operacional.

### Próxima etapa
Sugira somente, sem implementar.

Não modifique arquivos depois da auditoria final sem reportar explicitamente a alteração.
