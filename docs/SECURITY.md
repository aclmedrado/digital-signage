# Segurança

## Biblioteca de mídias — ETAPA 005

O painel, a API e o upload ainda não possuem autenticação, autorização ou
proteção administrativa CSRF. Esses controles são requisitos obrigatórios
na ETAPA 006, antes da liberação institucional. Utilizar apenas com operadores
confiáveis em ambiente restrito; não expor diretamente à Internet.
O operador decidiu manter temporariamente o binding 10.4.254.202:8080 durante
os testes da ETAPA 005, como risco temporariamente aceito diante da ausência
desses controles. O binding não constitui proteção de acesso nem autorização
para liberação institucional. A atualização documental não altera .env,
portas ou configuração global e não inicia a ETAPA 006.

Controles de upload: título limitado, extensões permitidas, tamanho real em
blocos de 1 MiB, MIME derivado da validação, Pillow com limite por quadro,
quantidade de quadros e pixels acumulados, ffprobe sem shell com timeout e
saída limitada. MP4 exige H.264 yuv420p/Full HD/30 FPS e AAC opcional;
outros codecs/trilhas são recusados. Protocolos externos e referências
externas de MOV são desabilitados. Não há execução de uploads nem conversão.

SVG bruto é recusado, inclusive com mensagem explícita para .svg. SVG
renomeado como imagem ou MP4 também deve falhar na validação de conteúdo.
Sua ingestão/exibição exige nova decisão de sanitização ou rasterização segura;
nenhuma biblioteca adicional de SVG foi incorporada.

Nomes originais são somente metadados escapados pelo Jinja2. Arquivos usam
UUID no volume /app/media, temporários 0600, publicação sem sobrescrita,
rollback/limpeza em falha tratável e entrega por id do banco. A entrega
confirma confinamento do caminho e usa MIME validado, nosniff e CSP restritiva.
A aplicação permanece UID/GID 10001; volumes, healthcheck e binding anterior
são preservados. Não há proteção de acesso aos arquivos sem autenticação.

Limites individuais não são quota global nem controle de concorrência. O
framework recebe multipart em spool temporário antes da validação por arquivo;
uploads concorrentes, exaustão de disco e entradas malformadas ainda exigem
restrição operacional. Análise por ffprobe não garante decodificação completa
de um vídeo nem compatibilidade com uma TV Box. Queda abrupta entre arquivo
e commit pode deixar resíduos para conferência manual. Não excluir arquivos
automaticamente nesta etapa. Monitorar espaço, logs e backups consistentes.

Config/build, suíte em Docker (149 passed, 1 warning), regressão HTTP,
os 14 itens do checklist pelo navegador, Range 206/416 e persistência após
restart/force-recreate foram aprovados pelo operador, conforme docs/STATUS.md.
Esses resultados foram fornecidos pelo operador, sem reexecução nesta
atualização; não demonstram proteção administrativa ou adequação para acesso
institucional amplo. A compatibilidade com TV Boxes continua pendente.
