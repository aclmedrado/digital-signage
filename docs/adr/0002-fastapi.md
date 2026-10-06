# ADR 0002 - Uso de FastAPI

Status: Aceito

## Contexto

O backend inicial precisa responder a requisições HTTP com uma implementação
pequena, testável e isolada em Docker, sem antecipar funcionalidades do MVP.

## Decisão

Utilizar FastAPI com Uvicorn. Nesta etapa, disponibilizar somente GET / e
GET /health, ambos com respostas JSON. Desabilitar as rotas automáticas de
documentação e OpenAPI para manter apenas os dois endpoints previstos.

## Motivos

- implementação simples de endpoints HTTP em Python;
- integração com testes usando pytest e TestClient;
- possibilidade de evolução gradual da API;
- execução em container sem dependências Python no host.

## Consequências

FastAPI e Uvicorn passam a ser dependências do backend. As versões diretas são
fixadas em requirements.txt; dependências transitivas e a imagem base não estão
travadas por hash/digest. Os testes são incluídos na imagem nesta etapa mínima
para permitir validação do mesmo artefato sem volumes do host. Banco de dados,
autenticação, upload e player permanecem fora desta etapa.
