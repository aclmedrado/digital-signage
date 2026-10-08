# ADR 0004 - Interface administrativa server-rendered

Status: Aceito

Data: 2026-10-08

## Contexto

O Digital Signage precisa oferecer uma interface administrativa simples para que usuários possam gerenciar telas sem utilizar diretamente a API HTTP ou comandos `curl`.

O projeto possui como princípios:

- baixo consumo de recursos;
- implantação simples;
- poucas dependências;
- facilidade de manutenção;
- facilidade de replicação;
- evolução incremental.

Neste momento, a interface administrativa necessária é pequena e contém principalmente formulários e listagens.

Não há necessidade atual de uma Single Page Application ou de um frontend independente.

## Decisão

Implementar a interface administrativa inicial utilizando renderização HTML no servidor através de FastAPI e Jinja2.

A interface utilizará:

- FastAPI;
- Jinja2;
- HTML;
- CSS;
- formulários HTML tradicionais.

JavaScript não será requisito para as funcionalidades básicas desta fase.

A interface administrativa fará parte da mesma aplicação e do mesmo container do backend.

## Estrutura

A interface administrativa utilizará URLs sob:

`/admin`

Inicialmente será implementado somente o gerenciamento de telas.

Exemplo:

`/admin/screens`

Os templates ficarão no diretório:

`app/templates/`

Os arquivos estáticos ficarão em:

`app/static/`

## Fluxo

Operações que modificam dados deverão preferir o padrão:

POST → Redirect → GET

Esse padrão evita reenvio acidental de formulários quando o usuário atualiza a página.

## Reutilização da camada existente

A interface administrativa deverá utilizar os mesmos modelos, validações e regras de persistência já existentes na aplicação.

Não deve chamar a própria API HTTP internamente para realizar operações.

Também não deve criar uma segunda implementação independente das regras de negócio.

Caso pequena extração de código compartilhado seja necessária para evitar duplicação significativa, ela deverá permanecer simples e localizada.

Não introduzir arquiteturas ou camadas adicionais sem necessidade concreta.

## Frontend

A interface inicial deverá:

- funcionar sem framework JavaScript;
- possuir HTML semântico;
- possuir CSS simples;
- ser responsiva;
- ser utilizável em navegadores modernos;
- fornecer mensagens claras de erro e confirmação.

Não utilizar nesta fase:

- React;
- Vue;
- Angular;
- Next.js;
- Node.js;
- Bootstrap;
- Tailwind;
- HTMX;
- bundlers;
- pipeline de frontend.

Essas ferramentas somente deverão ser introduzidas futuramente se houver necessidade concreta.

## Autenticação

A autenticação da interface administrativa não faz parte desta decisão nem desta etapa.

Enquanto não houver autenticação, a interface deve ser considerada apropriada somente para ambiente interno controlado.

A aplicação não deverá ser exposta diretamente à Internet nessa condição.

Uma etapa futura deverá tratar autenticação, autorização e proteção administrativa antes de qualquer exposição externa.

## Consequências positivas

- arquitetura simples;
- apenas um serviço;
- baixo consumo de recursos;
- implantação fácil;
- nenhuma cadeia de build frontend;
- manutenção facilitada;
- integração direta com FastAPI e SQLAlchemy.

## Consequências negativas

- menor interatividade quando comparada a uma SPA;
- atualizações geralmente exigem nova requisição HTTP;
- funcionalidades muito dinâmicas poderão exigir JavaScript futuramente.

Essas limitações são aceitáveis para a fase atual do projeto.