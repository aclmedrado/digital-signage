# ADR 0001 - Uso de Docker

Status: Aceito

Data: 2026-09-28

## Contexto

O servidor utilizado pelo projeto hospeda outras aplicações.

Instalar diretamente dependências da aplicação no sistema operacional poderia
causar conflitos e dificultar manutenção e reprodução do ambiente.

## Decisão

Executar o Digital Signage utilizando containers Docker gerenciados através de
Docker Compose.

## Motivos

- isolamento de dependências;
- facilidade de implantação;
- ambiente reproduzível;
- facilidade de atualização;
- menor interferência em outras aplicações.

## Consequências

Dados persistentes deverão ser armazenados fora da camada efêmera dos
containers.

O projeto deverá possuir Dockerfile e compose.yaml versionados.
