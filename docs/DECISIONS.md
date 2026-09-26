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

---

_Novas entradas devem ser adicionadas ao final deste arquivo, mantendo a ordem cronológica._
