# Log de decisões do projeto

Este arquivo é o registro cronológico de toda decisão não trivial tomada durante o desenvolvimento do Trabalho Final de PSI5120. Ele existe para que o artigo IEEE possa ser escrito depois com base em fatos registrados, não em memória. Cada entrada indica também qual seção do artigo aquela decisão deve alimentar.

Formato de cada entrada: contexto → decisão → alternativas consideradas → impacto no artigo.

---

## [2026-09-26 13:56] Escolha da trilha do trabalho final

- **Contexto:** o professor sugeriu 3 trilhas no documento `Trabalho Final/Orientacoes Trabalho Final.png`: (2.1) solução IoT fim a fim, (2.2) extensão de um trabalho intermediário da disciplina, (2.3) revisão sistemática de literatura. O prazo de entrega é 27/09/2026 23h55, ou seja, ~34h a partir do início do planejamento, e o trabalho é executado individualmente (apesar do grupo formal ter até 3 integrantes).
- **Decisão:** trilha 2.2 — extensão de um trabalho intermediário.
- **Alternativas consideradas:**
  - IoT fim a fim (2.1): descartada por falta de hardware físico (ESP32/ESP8266/RaspberryPi + sensor/atuador) e inviabilidade de adquirir/configurar dentro do prazo.
  - Revisão sistemática (2.3): descartada porque o usuário preferiu um trabalho prático que reaproveita código já escrito no curso, em vez de um artigo puramente bibliográfico.
- **Impacto no artigo:** seção *Introduction* (justificativa da escolha do escopo) e *Related Work* (a revisão de literatura descartada como trilha principal ainda pode compor uma seção de related work mais enxuta).

## [2026-09-26 13:58] Escolha do laboratório-base a estender

- **Contexto:** entre os laboratórios das Aulas 03–07, era preciso escolher qual estender. Aula 06 (Amazon EKS) é a base tecnicamente mais rica, mas cria/destrói cluster gerenciado em 15–20 min por operação e tem custo horário maior. Aula 07 (Lambda + SQS + DLQ + CloudFormation) é 100% serverless, de custo quase nulo dentro do Free Tier, e já usa Infra como Código.
- **Decisão:** estender o laboratório da Aula 07 (`Aula 07/04_software/`).
- **Alternativas consideradas:** Aula 06 (EKS) — descartada por risco de cronograma; Aula 04/05 (Docker/Kubernetes cru) — descartada por exigir migração completa para um serviço gerenciado da AWS, consumindo tempo que não havia.
- **Impacto no artigo:** seção *Introduction* e *Background* (por que partir de uma arquitetura serverless) e *Discussion* (comparação qualitativa serverless vs. orquestração de contêineres, citando os preços já levantados na Aula 06 — ver `Aula 06/Prática/evidencias/E8_precos-*.png`).

## [2026-09-26 14:02] Escopo da extensão: pipeline com engenharia de confiabilidade e observabilidade

- **Contexto:** o laboratório original da Aula 07 é puramente didático: função Lambda que só valida um campo `valor` numérico e simula falha via flag `forcar_falha`; não há porta de entrada HTTP, não há persistência, não há observabilidade estruturada além de `print()` e não há nenhuma avaliação quantitativa.
- **Decisão:** estender com (1) API Gateway HTTP API como porta de entrada, desacoplando ingestão de processamento; (2) tabela DynamoDB para persistir o resultado de cada evento; (3) escrita condicional no DynamoDB para garantir idempotência diante de reentregas do SQS (at-least-once delivery); (4) alarme CloudWatch na DLQ disparando notificação SNS por e-mail; (5) métrica customizada no CloudWatch; (6) script de carga (`scripts/load_test.py`) para gerar dados quantitativos de latência, throughput e taxa de redrive; (7) estimativa de custo comparando com uma alternativa always-on.
- **Alternativas consideradas:** manter o event source mapping com `BatchSize=1` herdado da Aula 07 (em vez de processar em lote), porque o handler da Aula 07 já valida explicitamente essa premissa — manter reduz o risco de regressão e mantém o comportamento didático original reconhecível.
- **Impacto no artigo:** seção *System Design* (a tabela "aspecto não coberto → extensão proposta" do plano vira a estrutura desta seção) e *Implementation*.

## [2026-09-26 14:05] Limitação conhecida da idempotência implementada

- **Contexto:** a forma mais rigorosa de idempotência seria reservar o `event_id` no DynamoDB *antes* de executar qualquer lógica de negócio (padrão "reserve-then-process"). Dado o escopo didático da função (a lógica de negócio é apenas uma validação, sem efeitos colaterais externos), foi decidido fazer a escrita condicional *depois* do processamento.
- **Decisão:** `consumer_function.py` processa o evento e, ao final, tenta um `put_item` com `ConditionExpression=attribute_not_exists(event_id)`. Se a condição falhar (evento duplicado), a função loga o caso como duplicata idempotente e retorna sucesso (a mensagem SQS é removida da fila sem reprocessamento futuro), mas a lógica de validação já rodou de novo nesse caso.
- **Alternativas consideradas:** padrão reserve-then-process com item de "lock" antes do processamento — descartado por complexidade adicional desnecessária dado que a função não tem efeitos colaterais externos (não chama serviços de terceiros, não cobra cartão, etc.).
- **Impacto no artigo:** seção *Discussion*/*Limitations* — este é um ponto importante para o artigo discutir criticamente (idempotência de efeito vs. idempotência de execução).

## [2026-09-26 14:07] Formato de deploy da Lambda: código inline no CloudFormation

- **Contexto:** a Aula 07 já usa o padrão de inline `ZipFile` dentro do template CloudFormation, mantendo uma cópia separada do código em `.py` "editável" só para leitura/edição — sem pipeline de empacotamento em S3.
- **Decisão:** manter o mesmo padrão nas duas novas funções (`producer_function.py`, `consumer_function.py`): o código-fonte em `src/` é a versão legível e testável localmente; o template `infra/template.yaml` embute o mesmo código inline via `ZipFile`. Os dois precisam ser mantidos sincronizados manualmente a cada alteração.
- **Alternativas consideradas:** `aws cloudformation package` com bucket S3 automático (via SAM) — descartado por adicionar uma ferramenta (SAM CLI) e um bucket S3 extra à lista de pré-requisitos de alguém sem experiência em AWS, aumentando a chance de erro no roteiro de execução.
- **Impacto no artigo:** seção *Implementation* (mencionar a limitação de sincronização manual como trade-off de simplicidade operacional).

## [2026-09-26 14:20] Scaffolding inicial do repositório

- **Contexto:** com o plano aprovado, era preciso decidir onde criar o repositório local e como estruturar o primeiro commit antes de criar o remoto no GitHub.
- **Decisão:** repositório criado em `Trabalho Final/psi5120-trabalho-final/` dentro da pasta da disciplina (fora do controle do OneDrive fazer merge estranho com o Git, mas sem mover a pasta da disciplina). `git init` + primeiro commit local feitos com todo o scaffolding (infra, código-fonte, scripts, docs, esqueleto do artigo). A criação do repositório remoto no GitHub e o primeiro `git push` foram propositalmente deixados para confirmação explícita do usuário antes de executar, por afetarem um sistema externo/compartilhado.
- **Alternativas consideradas:** nenhuma — passo mecânico.
- **Impacto no artigo:** nenhum (registro operacional, não de arquitetura).

## [2026-09-26 14:25] Referências bibliográficas verificadas nos PDFs da disciplina

- **Contexto:** era necessário citar corretamente, no artigo, os três artigos já trabalhados nas Aulas 01–03 (Buyya et al. 2009, Sotomayor et al. 2009, e o texto sobre OpenNebula da Aula 03). Em vez de citar de memória, o texto das primeiras páginas dos PDFs em `Aula 01/Artigo 01.pdf`, `Aula 02/Virtual_Infrastructure_Management_in_Private_and_Hybrid_Clouds.pdf` e `Aula 03/Artigo/OpenNebula_A_Cloud_Management_Tool.pdf` foi extraído para confirmar autoria, veículo e ano.
- **Decisão:** usar as referências completas encontradas: (1) Buyya, Yeo, Venugopal, Broberg, Brandic, "Cloud Computing and Emerging IT Platforms...", Future Generation Computer Systems, 25(6), 599-616, 2009 (confirmado no próprio enunciado da Aula 01); (2) Sotomayor, Montero, Llorente, Foster, "Virtual Infrastructure Management in Private and Hybrid Clouds", IEEE Internet Computing, vol. 13, n. 5, 2009 (confirmado no cabeçalho do PDF); (3) o texto da Aula 03 é na verdade uma entrevista "Trend Wars" (coluna da IEEE Internet Computing, Mar/Abr 2011) com Ignacio M. Llorente e Rubén S. Montero, conduzida por Dejan Milojičić — citada como tal, não como artigo de pesquisa tradicional.
- **Alternativas consideradas:** citar de memória sem verificar — descartado por risco de erro factual em uma referência bibliográfica de um artigo IEEE.
- **Impacto no artigo:** seção *Related Work* e lista de referências (`\bibitem`) de `paper/main.tex`.

## [2026-09-26 15:10] Repositório remoto no GitHub

- **Contexto:** o trabalho final exige entrega em repositório GitHub. O usuário criou manualmente o repositório vazio em `https://github.com/pedro-remus/psi5120-trabalho-final` e forneceu a URL.
- **Decisão:** remote `origin` configurado apontando para essa URL; branch local renomeada de `master` para `main` (padrão atual do GitHub); push inicial feito com sucesso (`git push -u origin main`).
- **Alternativas consideradas:** nenhuma — passo mecânico.
- **Impacto no artigo:** nenhum diretamente, mas a URL do repositório deve ser citada no artigo/relatório final como entregável de código, conforme pedido nas instruções do trabalho.

## [2026-09-26 15:55] Pasta de evidências de execução

- **Contexto:** o usuário pediu um local no repositório para guardar as evidências da execução (prints, saídas de comando, logs) para alimentar o relatório/artigo depois. As Aulas 04–06 da disciplina já usam uma pasta `evidencias/` com arquivos `E<n>.txt` numerados e uma subpasta `screenshots/` — convenção já estabelecida pelo próprio material do curso.
- **Decisão:** criada `evidencias/` na raiz do repositório, com subpastas `screenshots/`, `cli-output/` e `logs/`, mais um `evidencias/README.md` com uma tabela de checklist (E1–E9) mapeando cada evidência mínima à seção correspondente de `docs/ROTEIRO_EXECUCAO.md`. O roteiro foi editado para apontar, ao final de cada etapa relevante, onde salvar a evidência daquela etapa.
- **Alternativas consideradas:** guardar evidências dentro de `results/` junto dos CSVs/gráficos — descartado para manter a separação entre "dados quantitativos do experimento" (`results/`) e "prova de execução manual" (`evidencias/`), que têm propósitos e formatos diferentes.
- **Impacto no artigo:** nenhuma seção nova, mas é a fonte primária para preencher os `[PREENCHER]` da seção *Experimental Evaluation* e para eventuais capturas de tela que se queira incluir como figuras adicionais.

## [2026-09-26 16:05] Checklist interativo do roteiro (página web)

- **Contexto:** o usuário pediu uma versão do roteiro de execução utilizável como referência rápida durante a implantação na AWS, além do markdown já existente em `docs/ROTEIRO_EXECUCAO.md`.
- **Decisão:** publicado um checklist interativo em página web espelhando o conteúdo do roteiro, com os 25 itens de verificação, comandos com botão de copiar, tabela de troubleshooting e barra de progresso. O progresso marcado é persistido por usuário, com fallback em `localStorage` do navegador se a sincronização não estiver disponível. O `docs/ROTEIRO_EXECUCAO.md` continua sendo a fonte de verdade versionada no repositório; a página é um complemento de uso, não substitui a documentação.
- **Alternativas consideradas:** nenhuma — atende diretamente ao pedido.
- **Impacto no artigo:** nenhum diretamente; é uma ferramenta operacional, não um artefato de pesquisa a ser citado.

## [2026-09-27 08h35] Detalhamento da instalação do AWS CLI e nome do profile

- **Contexto:** ao iniciar a execução (dia da entrega), constatou-se que o AWS CLI não estava instalado na máquina do usuário, e o roteiro original assumia que a instalação "já tinha sido feita no Tutorial 2 da Aula 07" sem detalhar o passo Windows. O usuário também informou já ter um usuário IAM próprio chamado `pedro-psi5120` (em vez de criar um novo `psi5120-trabalho-final` como o roteiro sugeria) e perguntou se o AWS CLI deveria ser configurado com o usuário root ou com o IAM user.
- **Decisão:** (1) `docs/ROTEIRO_EXECUCAO.md` (seção 2) e o Artifact do roteiro foram expandidos com passo a passo específico para Windows (instalador MSI oficial ou `winget`), reforçando explicitamente que o AWS CLI deve ser configurado **sempre com o usuário IAM, nunca com a conta root** (root não deveria nem ter access keys geradas). (2) Todos os exemplos de comando que usavam `--profile psi5120` genérico foram trocados para `--profile pedro-psi5120`, refletindo o usuário IAM real do operador, para os comandos serem copiáveis sem precisar de substituição mental.
- **Alternativas consideradas:** manter um usuário/profile genérico nos exemplos — descartado porque o usuário já tinha um IAM user real configurado, e usar o nome real reduz erro de cópia/cola.
- **Impacto no artigo:** nenhum diretamente (detalhe operacional), mas reforça, na seção *Implementation* ou numa nota de rodapé, a prática de least-privilege/least-exposure já mencionada (nunca usar credenciais root em automação).

## [2026-09-27 08h50] Artifact do roteiro atualizado com o mesmo detalhamento

- **Contexto:** o Passo 2 do Artifact publicado (checklist interativo) estava resumido demais (só `aws configure`/`aws sts get-caller-identity`, sem passo de instalação), e um bug foi encontrado: o campo `label` de cada bloco de comando existia nos dados mas nunca era renderizado na página.
- **Decisão:** o Passo 2 do Artifact foi reescrito para espelhar `docs/ROTEIRO_EXECUCAO.md` (verificação, instalação no Windows via MSI/winget, aviso explícito IAM vs. root, configuração do profile, confirmação de identidade); o bug de renderização do `label` dos comandos foi corrigido (agora aparece como legenda acima de cada bloco de código); todas as referências ao profile genérico `psi5120` nos exemplos foram trocadas para `pedro-psi5120`.
- **Alternativas consideradas:** nenhuma — correção e atualização direta.
- **Impacto no artigo:** nenhum.

## [2026-09-27 09h10] Execução assumida por assistente de IA + teto de custo de US$10

- **Contexto:** após instalar e configurar o AWS CLI (usuário IAM `pedro-psi5120`, identidade confirmada — `evidencias/cli-output/E1_identidade_aws.txt`), o usuário pediu para o assistente de IA assumir a execução do deploy/testes/load test/limpeza diretamente via terminal (a mesma máquina onde o CLI está configurado), em vez de rodar cada comando manualmente. O usuário está usando conta AWS gratuita/créditos trial e impôs um teto explícito de **US$10 em custos totais**.
- **Decisão:** o assistente de IA assume a execução dos comandos AWS CLI diretamente. Estimativa de custo do stack (nenhum recurso com custo fixo por hora — sem EC2/NAT Gateway/Load Balancer/RDS; tudo pay-per-request dentro do Free Tier) é bem menos de US$1 para o volume de teste planejado. Para respeitar o teto: (1) o `cleanup.sh` será executado assim que as evidências forem coletadas, em vez de deixar a stack no ar por conveniência; (2) o volume do teste de carga (`load_test.py --total`) será mantido em uma escala modesta (dezenas a poucas centenas de requisições), não milhares; (3) qualquer ação de deploy/limpeza continua sendo confirmada com o usuário antes de executar, mesmo com a execução delegada.
- **Alternativas consideradas:** deixar a stack no ar até o fim do dia por flexibilidade — descartado em favor de minimizar custo, dado o teto explícito e o uso de créditos trial.
- **Impacto no artigo:** nenhum diretamente; pode alimentar a seção de custo (*Experimental Evaluation*) com o custo real observado, se o usuário quiser conferir a fatura depois.

## [2026-09-27 09h27] Bug real encontrado e corrigido: métrica customizada não aparecia no dashboard

- **Contexto:** ao gerar a evidência E8 (renderização dos widgets do CloudWatch Dashboard via `aws cloudwatch get-metric-widget-image`), o widget da métrica customizada `EventosProcessados` veio vazio, apesar de `list-metrics` confirmar que a métrica estava sendo publicada. Investigação (`list-metrics`) revelou que `_emitir_metrica` em `consumer_function.py` publicava cada ponto com duas dimensões (`TipoEvento` + `Resultado`), enquanto o widget do dashboard (`infra/template.yaml`) consultava só por `Resultado`. No CloudWatch, o conjunto de dimensões faz parte da identidade da métrica, então a consulta parcial nunca casava com os dados publicados.
- **Decisão:** `_emitir_metrica` foi simplificada para publicar apenas com a dimensão `Resultado` (removido `TipoEvento`, que nenhum widget usava). Corrigido em `src/consumer_function.py` e na cópia embutida em `infra/template.yaml`; redeploy da stack feito para atualizar a função `consumer`; correção confirmada via `aws cloudwatch get-metric-statistics` antes de regerar a imagem de evidência.
- **Alternativas consideradas:** ajustar o widget do dashboard para consultar por `Resultado` + `TipoEvento` juntos (ou via expressão `SEARCH`) — descartado por ser mais complexo (exigiria uma série por combinação de `TipoEvento`, que varia livremente por payload) sem trazer valor adicional, já que o dashboard só precisa do agregado por `Resultado`.
- **Impacto no artigo:** bom exemplo real para a seção *Discussion*/*Limitations* — ilustra um erro comum e sutil de observabilidade (dimensões de métrica como parte da identidade, não como filtro livre) encontrado e corrigido durante o desenvolvimento, com evidência do antes/depois em `evidencias/screenshots/E8_dashboard.md`.

## [2026-09-27 18h32] Limpeza da stack adiada para depois do artigo

- **Contexto:** com os Passos 1–6 completos e todas as evidências (E1–E8) coletadas, o usuário pediu para explorar o Console AWS pessoalmente (ver o Dashboard, os recursos criados) antes de rodar `cleanup.sh`, e preferiu deixar a limpeza para depois de redigir o artigo (para poder voltar a conferir algo no Console/CLI se precisar durante a escrita).
- **Decisão:** stack `psi5120-tf-serverless` permanece no ar; `cleanup.sh` só será executado após a redação do artigo estar concluída. Isso é seguro dentro do teto de US$10 combinado, já que nenhum recurso do stack tem custo fixo por hora (tudo pay-per-request/serverless).
- **Alternativas consideradas:** limpar imediatamente e recriar se necessário — descartado por ser mais lento (redeploy leva 1-3 min) do que simplesmente manter no ar por mais algumas horas.
- **Impacto no artigo:** nenhum diretamente.

## [2026-09-27 19h50] Artigo preenchido com dados reais

- **Contexto:** com toda a execução na AWS concluída e evidências (E1–E8) coletadas, era hora de preencher os `[PREENCHER]` deixados no esqueleto de `paper/main.tex`.
- **Decisão:** todos os placeholders foram substituídos por números reais tirados de `results/figures/resumo_estatistico.txt`, dos logs do CloudWatch e das evidências em `evidencias/`. Adições feitas além do preenchimento simples: (1) nome completo do autor corrigido para "Pedro Remus de Avila" (identificado no PDF do e-mail do alarme) e e-mail de contato trocado para `pedro.prda@usp.br`; (2) nova figura embutida no artigo (`evidencias/screenshots/E8_dashboard_filas.png`, o widget de profundidade da DLQ) em vez de só citar o dado em texto; (3) nova subseção de Discussion ("Observability pitfalls: metric dimensions as identity") relatando o bug de dimensão de métrica encontrado e corrigido durante a coleta de evidências — boa contribuição de conteúdo real para a seção de discussão; (4) seção *Threats to validity* preenchida com o achado dos 2 erros 503 investigados (Lambda sem erros/throttles registrados, atribuído à camada do API Gateway).
- **Alternativas consideradas:** omitir os achados "negativos" (os 2 erros 503, o bug do dashboard) para simplificar a narrativa — descartado porque relatar honestamente o que foi observado (inclusive imperfeições) é mais rigoroso cientificamente e gera conteúdo genuíno para as seções de Discussion/Limitations, além de demonstrar profundidade de investigação.
- **Alternativas consideradas (autor):** manter o e-mail pessoal `pedro.prda@gmail.com` no artigo — trocado para o e-mail institucional USP por ser mais apropriado a um artigo acadêmico afiliado à Universidade de São Paulo.
- **Impacto no artigo:** artigo completo, pronto para compilação/revisão final. Validado estruturalmente (chaves balanceadas, ambientes `\begin`/`\end` batendo, todas as `\ref`/`\cite`/`\includegraphics` resolvidas e apontando para arquivos existentes) — falta apenas compilar no Overleaf para confirmar a contagem de páginas (mínimo 6, máximo 18).

## [2026-09-27 20h05] Artigo expandido para atingir o mínimo de 6 páginas

- **Contexto:** a primeira compilação no Overleaf ficou com "pouco menos de 6 páginas" (mínimo exigido pelo enunciado). Era preciso adicionar conteúdo real, não enchimento.
- **Decisão:** adicionadas duas subseções em Background explicando conceitos usados na Implementação mas nunca introduzidos (API Gateway HTTP API e escrita condicional do DynamoDB); uma tabela quantitativa de custos (Table~II, com as taxas públicas da AWS e o volume real de requisições consumido); e uma nova seção "Reproducibility and Artifact Availability" (Seção VIII) descrevendo o repositório público, o log de decisões e o roteiro de execução como artefatos de auditoria do processo, não só do resultado. A numeração das seções no roadmap da Introdução foi corrigida (Conclusão passou a ser Seção IX).
- **Alternativas consideradas:** aumentar o tamanho da fonte/margens ou parafrasear trechos existentes de forma mais prolixa — descartado por ser enchimento sem conteúdo, indo contra a prática de honestidade científica já seguida no resto do artigo.
- **Impacto no artigo:** Seções III, VI, VIII diretamente; deve ser recompilado no Overleaf para confirmar que passou de 6 páginas.

## [2026-09-27 20h15] Coautores e NUSP adicionados ao artigo

- **Contexto:** o grupo formalmente cadastrado na disciplina tem 3 integrantes (ver decisão registrada em 2026-09-26 sobre execução individual). O usuário pediu para adicionar os outros dois integrantes e os números USP de todos ao artigo.
- **Decisão:** bloco de autoria do `paper/main.tex` atualizado para 3 autores via `\and` (formato padrão IEEEtran multi-autor): Pedro Remus de Ávila (NUSP 13682486, com acento corrigido), Murilo Gabriel Moraes de Azevedo (NUSP 13782776), Bruno Valle Martins (NUSP 13681036). E-mail institucional mantido só para o autor correspondente (Pedro), já que não temos os e-mails dos outros dois. Referências a "the author's" no texto (seção de custo) trocadas para "the authors'" para consistência. `README.md` também atualizado para listar os 3 autores em vez da nota sobre execução individual (que não deve aparecer em nenhum entregável).
- **Alternativas consideradas:** nenhuma — atende diretamente ao pedido.
- **Impacto no artigo:** bloco de autoria (topo) e seção de custo (pequeno ajuste de concordância).

## [2026-09-27 20h20] Correção do layout do cabeçalho de autoria

- **Contexto:** o formato multi-autor padrão do IEEEtran (3 blocos separados por `\and`) quebrou de forma estranha na compilação: 2 autores na primeira linha, o terceiro sozinho numa linha alinhado à esquerda em vez de centralizado — resultado de cada bloco conter várias linhas (afiliação + curso + NUSP), ficando largo demais para caber 3 por linha, mas não simétrico o suficiente para o layout de "2+1" do IEEEtran centralizar bem o terceiro.
- **Decisão:** trocado para um único bloco de autoria (um `\IEEEauthorblockN` só, listando os 3 nomes com o NUSP entre parênteses ao lado de cada um, e um `\IEEEauthorblockA` compartilhado com a afiliação comum). Um bloco único é sempre centralizado pelo IEEEtran e quebra de linha automaticamente se for muito longo, evitando o problema de alinhamento assimétrico com 3 autores.
- **Alternativas consideradas:** forçar centralização manual do terceiro bloco com comandos de espaçamento — descartado por ser mais frágil (depende da largura exata da coluna) que simplesmente usar um bloco compartilhado, já que os 3 autores têm a mesma afiliação.
- **Impacto no artigo:** cabeçalho de autoria (topo da primeira página).

## [2026-09-27 20h40] Revisão do PDF compilado: 2 bugs reais encontrados e corrigidos

- **Contexto:** o usuário compilou no Overleaf e compartilhou o PDF final (7 páginas, dentro do limite 6–18) para revisão. Leitura completa do PDF encontrou dois problemas reais (além de confirmar que o conteúdo/coerência estava correto):
  1. **Linha de autoria estourando a margem da página** — "Pedro Remus de Ávila (NUSP 13682486), Murilo Gabriel Moraes de Azevedo (NUSP 13782776), Bruno Valle Martins (NU..." aparecia literalmente cortada no fim da página, com o NUSP do terceiro autor sumindo. O bloco único de autoria (correção anterior, 20h20) resolveu a centralização mas a linha ficou comprida demais para caber numa linha só.
  2. **Faltavam `\usepackage[utf8]{inputenc}` e `\usepackage[T1]{fontenc}`** — o PDF renderiza visualmente correto, mas o texto extraído (copiar/colar, indexação, sistemas de antiplágio) sai corrompido em palavras acentuadas (ex.: "São Paulo" virando "S ´ ao Paulo ˜"), por falta de mapeamento ToUnicode correto nas fontes.
- **Decisão:** (1) `\IEEEauthorblockN` do bloco único de autoria agora quebra cada autor+NUSP em sua própria linha via `\\`, eliminando o overflow sem reintroduzir o problema de centralização assimétrica das correções anteriores. (2) `inputenc`/`fontenc` adicionados ao preâmbulo, padrão para qualquer documento LaTeX com caracteres acentuados.
- **Alternativas consideradas:** nenhuma — correções diretas de bugs reais encontrados em revisão.
- **Impacto no artigo:** cabeçalho de autoria (visual) e integridade do texto extraído do PDF inteiro (não visível a olho nu, mas relevante para qualquer processamento automatizado do PDF).

## [2026-09-27 20h55] Correção de estouro de margem em identificadores longos no artigo

- **Contexto:** revisão do PDF compilado encontrou um segundo caso de texto estourando a margem da página: a string de código `ConditionExpression=attribute_not_exists(event_id)`, dentro de `\texttt{}`, é longa demais para quebrar de linha sozinha (LaTeX não hifeniza dentro de `\texttt` por padrão).
- **Decisão:** adicionado `\usepackage{seqsplit}` ao preâmbulo e aplicado `\seqsplit{}` a todos os identificadores de código inline com 30+ caracteres sem espaços (`ConditionExpression=attribute_not_exists(event_id)`, `ConditionalCheckFailedException` ×3, `ApproximateNumberOfMessagesVisible`, `ApproximateNumberOfMessages`), permitindo quebra de linha em qualquer ponto do identificador quando necessário.
- **Alternativas consideradas:** reescrever as frases para encurtar os identificadores — descartado por reduzir a precisão técnica (esses são nomes literais de parâmetros/exceções da AWS, não paráfrases).
- **Impacto no artigo:** Seções III-F, V-B, VI-C, VI-D (nenhuma mudança de conteúdo, só de quebra de linha).

## [2026-09-27 21h00] Remoção de menções ao assistente de IA no log de decisões

- **Contexto:** o usuário pediu para remover do repositório remoto qualquer referência à ferramenta de IA usada no desenvolvimento.
- **Decisão:** três entradas deste arquivo (sobre o checklist interativo e sobre a execução delegada dos comandos AWS) foram reescritas em linguagem neutra, sem nomear a ferramenta; o link do checklist interativo (hospedado em domínio da ferramenta) também foi removido do texto. Uma busca completa no repositório confirmou que não restam menções no estado atual dos arquivos. Nota: commits antigos já publicados no histórico do repositório ainda contêm o texto anterior nos seus diffs — remover isso exigiria reescrever o histórico (`git filter-repo` ou rebase interativo) seguido de `push --force`, uma operação destrutiva que não foi executada sem confirmação explícita.
- **Alternativas consideradas:** reescrever o histórico do repositório imediatamente — não executado por ser uma ação destrutiva/irreversível sobre um repositório remoto, que exige confirmação explícita do usuário antes de qualquer `push --force`.
- **Impacto no artigo:** nenhum (o artigo em si nunca mencionou a ferramenta).

---

_Novas entradas devem ser adicionadas ao final deste arquivo, mantendo a ordem cronológica._
