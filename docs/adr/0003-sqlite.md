# ADR 0003 - Uso de SQLite

Status: Aceito

Data: 2026-10-06

## Contexto

O Digital Signage precisa persistir informações como:

- telas cadastradas;
- configurações das telas;
- conteúdos;
- playlists;
- agendamentos;
- estado administrativo da aplicação.

O projeto foi definido como um sistema leve, simples de implantar e facilmente replicável.

Na fase atual existe apenas uma instância da aplicação FastAPI executando em um único servidor através de Docker Compose.

Não há necessidade, neste momento, de:

- múltiplas instâncias concorrentes da aplicação;
- cluster de banco de dados;
- replicação;
- alta disponibilidade de banco;
- grande volume de escritas simultâneas;
- servidor de banco de dados separado.

## Decisão

Utilizar SQLite como banco de dados inicial do Digital Signage.

O acesso ao banco será realizado pela aplicação através de SQLAlchemy.

O arquivo SQLite deverá ser armazenado em área persistente fora da camada efêmera do container.

O local lógico dentro do container será:

`/app/data/signage.db`

A implantação deverá garantir que o banco sobreviva a:

- reinicialização do container;
- reconstrução da imagem;
- atualização da aplicação.

A localização do banco deverá ser configurável por variável de ambiente.

Exemplo:

`DATABASE_URL=sqlite:////app/data/signage.db`

## Motivos

SQLite foi escolhido porque:

- não necessita de servidor de banco separado;
- possui baixo consumo de recursos;
- simplifica a implantação;
- simplifica backup e restauração;
- é adequado ao volume inicialmente esperado;
- atende bem aplicações com baixo nível de concorrência de escrita;
- facilita a replicação do projeto por terceiros;
- reduz a quantidade de containers e componentes operacionais.

Essa decisão está alinhada ao objetivo do projeto de permanecer simples enquanto não houver necessidade real de maior complexidade.

## Persistência

O arquivo do banco não deverá ser armazenado apenas no filesystem efêmero do container.

A implantação deverá utilizar armazenamento persistente definido no Docker Compose.

O banco de produção não deverá ser versionado pelo Git.

Arquivos SQLite deverão permanecer protegidos pelas regras do `.gitignore`.

## Acesso ao banco

A aplicação utilizará SQLAlchemy como camada de acesso ao banco.

Modelos de banco, sessões e operações deverão permanecer separados das rotas HTTP sempre que isso puder ser feito sem criar abstrações desnecessárias.

O SQLite deverá ser configurado corretamente para uso com FastAPI e SQLAlchemy.

## Migrações

Nesta fase inicial, o projeto poderá criar o esquema mínimo necessário durante a inicialização da aplicação.

Não será introduzido Alembic nesta etapa.

Quando o banco começar a possuir dados relevantes e alterações de esquema precisarem ser aplicadas de forma controlada, deverá ser criada uma nova decisão arquitetural para adoção de migrations.

## Limitações conhecidas

SQLite não é a escolha definitiva obrigatória para toda a vida do projeto.

Uma migração para PostgreSQL ou outro banco poderá ser considerada caso surjam requisitos como:

- múltiplas instâncias da aplicação;
- grande concorrência de escrita;
- necessidade de maior escalabilidade;
- replicação;
- alta disponibilidade;
- consultas ou cargas incompatíveis com SQLite.

Essa mudança deverá ser motivada por necessidade concreta e registrada em novo ADR.

## Consequências

### Positivas

- infraestrutura mais simples;
- menor consumo de memória e CPU;
- menos componentes para administrar;
- backups simples;
- implantação mais fácil;
- ambiente adequado ao MVP.

### Negativas

- menor capacidade para escritas concorrentes;
- ausência de recursos encontrados em servidores de banco completos;
- possível necessidade de migração futura.

Essas limitações são consideradas aceitáveis para a fase atual do Digital Signage.