# ADR 0005 — Biblioteca unificada de mídias

**Status:** Aceito  
**Data:** 2026-10-13

## Contexto

O Digital Signage já possui FastAPI, Docker Compose, SQLite persistente, API de telas e painel administrativo renderizado no servidor.

O principal usuário informou que produz campanhas publicitárias predominantemente em MP4. Portanto, o sistema precisa priorizar vídeos sem abandonar o suporte a imagens.

O armazenamento deve ser simples, seguro, persistente e reproduzível em outras instalações.

## Decisão

Adotar uma biblioteca unificada de mídias, representada por uma entidade `MediaAsset`.

O catálogo permitirá armazenar metadados de vídeos e imagens em SQLite, enquanto os arquivos físicos serão mantidos em volume Docker persistente separado.

### Formatos

**Implementados inicialmente:**

- MP4 com vídeo H.264 (AVC), áudio AAC ou sem áudio.
- JPEG/JPG.
- PNG.
- WebP.
- GIF.

**Formato previsto com tratamento adicional:**

- SVG.

SVG permanece como requisito do produto, mas sua ingestão e exibição ficam condicionadas à implementação e validação de sanitização ou conversão segura para formato rasterizado.

Não será permitido servir SVG arbitrário fornecido pelo usuário diretamente no navegador.

## Compatibilidade de vídeo

O perfil inicial recomendado para campanhas é:

- contêiner MP4;
- codec H.264/AVC;
- vídeo 8-bit, preferencialmente yuv420p;
- resolução máxima inicial Full HD (1920 × 1080);
- taxa máxima inicial de 30 FPS;
- áudio AAC opcional.

O sistema não executará transcodificação automática no MVP.

Arquivos incompatíveis deverão ser recusados com mensagem explicativa. O usuário poderá convertê-los antes de enviar novamente.

A compatibilidade real com as TV Boxes deverá ser validada em uma etapa específica de reprodução.

## Armazenamento

Utilizar dois volumes persistentes distintos:

- `signage-data`: banco SQLite existente;
- `signage-media`: arquivos de mídia.

Dentro do container:

- banco: `/app/data/signage.db`;
- mídias: `/app/media`.

Os arquivos físicos deverão receber nomes gerados pelo sistema, preferencialmente identificadores UUID.

O nome original será armazenado apenas como metadado para exibição.

Nunca utilizar um nome enviado pelo usuário diretamente como caminho de armazenamento.

## Banco de dados

Adicionar uma tabela específica para `MediaAsset`.

Os metadados mínimos são:

- identificador;
- título;
- tipo (video ou image);
- nome original;
- identificador/nome físico;
- tipo MIME validado;
- tamanho em bytes;
- largura;
- altura;
- duração do vídeo, quando aplicável;
- codec de vídeo, quando aplicável;
- codec de áudio, quando aplicável;
- data de criação.

A tabela `screens` e seus registros existentes deverão permanecer preservados.

## Upload

Utilizar `UploadFile` do FastAPI.

O arquivo deverá ser recebido de forma incremental, sem carregar vídeos completos na memória.

Limites iniciais configuráveis:

- vídeo: 250 MiB;
- imagem: 10 MiB;
- imagem descomprimida: até 20 megapixels.

O sistema deverá validar extensão, estrutura/conteúdo real e tipo de mídia.

Para imagens, utilizar Pillow.

Para vídeos, utilizar `ffprobe`.

O processamento do `ffprobe` deverá possuir limite de tempo e ser executado sem shell, sobre arquivo temporário controlado pela aplicação.

## Integridade

O upload deverá:

1. receber o arquivo em local temporário controlado;
2. aplicar o limite de tamanho;
3. validar formato e metadados;
4. gerar identificador próprio;
5. armazenar o arquivo no volume persistente;
6. registrar metadados no SQLite;
7. remover arquivos temporários.

Em caso de erro no banco ou validação, não deixar arquivos órfãos ou registros inconsistentes.

Não sobrescrever arquivos já armazenados.

## Entrega das mídias

Os arquivos serão disponibilizados por endpoint associado ao identificador do registro, nunca por um caminho arbitrário fornecido pelo cliente.

Para MP4, a entrega deverá suportar requisições HTTP Range, permitindo respostas `206 Partial Content`.

Utilizar recursos existentes do Starlette/FastAPI sempre que possível.

Não implementar servidor de streaming separado nesta etapa.

## Segurança

Não confiar apenas em:

- extensão do arquivo;
- nome original;
- Content-Type enviado pelo navegador.

Aplicar também:

- limites de tamanho;
- validação do conteúdo;
- nomes internos não previsíveis;
- proteção contra path traversal;
- tratamento de arquivos inválidos;
- tratamento de imagens excessivamente grandes;
- execução como usuário não-root;
- arquivos fora do diretório de código;
- respostas HTTP com tipos MIME corretos;
- prevenção de execução de arquivos enviados.

O painel e a API ainda não possuem autenticação/autorização nem proteção administrativa completa contra CSRF.

Portanto, o upload não poderá ser liberado para uso institucional amplo nesta etapa. Os testes operacionais deverão ocorrer em ambiente restrito e controlado.

Autenticação, autorização e proteção contra CSRF constituem requisito obrigatório antes dessa liberação.

## Backup

Os arquivos de mídia e o banco deverão ser incluídos em uma estratégia de backup consistente.

O volume `signage-media` não poderá ser removido durante atualizações.

Nunca utilizar `docker compose down -v` como parte de procedimentos operacionais normais.

## Fora desta decisão

Não implementar nesta fase:

- playlists;
- vinculação de mídias às telas;
- player para TV Boxes;
- transcodificação automática;
- geração obrigatória de thumbnails;
- exclusão física de mídias;
- integração com serviços externos;
- armazenamento em nuvem.

## Consequências positivas

- prioridade aos vídeos utilizados pelo público-alvo;
- catálogo único para imagens e vídeos;
- simplicidade operacional;
- persistência independente dos containers;
- manutenção facilitada;
- possibilidade de reutilização por outras instituições.

## Consequências negativas

- consumo adicional de armazenamento;
- dependência de ferramentas de inspeção de vídeo;
- necessidade de monitoramento do espaço em disco;
- incompatibilidade com alguns codecs;
- necessidade de tratamento específico de SVG;
- necessidade futura de controle de acesso e políticas de retenção.

Essas limitações são aceitas para o desenvolvimento incremental do MVP.

## Referências técnicas

- FastAPI — Request Files: https://fastapi.tiangolo.com/tutorial/request-files/
- FFmpeg — ffprobe: https://ffmpeg.org/ffprobe.html
- Starlette — Responses: https://www.starlette.io/responses/
- OWASP — File Upload Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html