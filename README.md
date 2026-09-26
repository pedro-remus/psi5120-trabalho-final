# PSI5120 — Trabalho Final: Extensão do pipeline serverless da Aula 07

Trabalho final da disciplina PSI5120 (Tópicos em Computação em Nuvem). Estende o laboratório serverless da Aula 07 (Lambda + SQS + DLQ + CloudFormation) com API Gateway, DynamoDB (persistência idempotente), observabilidade (CloudWatch + SNS) e uma avaliação experimental de latência/throughput/confiabilidade sob carga.

## Links rápidos

- **Quer só entender a decisão de escopo?** Leia [`docs/DECISIONS.md`](docs/DECISIONS.md) — é o registro cronológico de toda escolha de arquitetura, com o "porquê" de cada uma. É a fonte usada para redigir o artigo.
- **Quer rodar o projeto na sua conta AWS?** Siga [`docs/ROTEIRO_EXECUCAO.md`](docs/ROTEIRO_EXECUCAO.md) — passo a passo completo, sem assumir experiência prévia com AWS.
- **O artigo IEEE está em** [`paper/main.tex`](paper/main.tex). Para compilar: não há LaTeX instalado nesta máquina, então a forma mais simples é criar um projeto novo no [Overleaf](https://www.overleaf.com) (New Project → Upload Project, ou cole o conteúdo em um projeto "Blank"), enviar `paper/main.tex` e a pasta `results/figures/` (as figuras só existem depois de rodar o pipeline — ver `docs/ROTEIRO_EXECUCAO.md`). A classe `IEEEtran` já vem pronta no Overleaf, não precisa instalar nada. Os trechos marcados com `[PREENCHER]` no `.tex` precisam ser substituídos pelos números reais gerados em `results/figures/resumo_estatistico.txt` antes da entrega.

## Arquitetura (resumo)

```
Cliente → API Gateway (HTTP API) → Lambda "producer" → SQS (fila principal)
                                                            │
                                        (falha após 2 tentativas)
                                                            │
                                                            ▼
                                        Lambda "consumer" → DynamoDB (escrita idempotente)
                                                            │
                                           (em caso de falha) → DLQ → Alarme CloudWatch → SNS (e-mail)
```

Detalhes completos em `docs/DECISIONS.md` e no artigo (`paper/main.tex`, seção System Design).

## Estrutura do repositório

```
.
├── docs/
│   ├── DECISIONS.md            # log de decisões do projeto (fonte para o artigo)
│   └── ROTEIRO_EXECUCAO.md     # passo a passo de deploy/teste/limpeza na AWS
├── evidencias/
│   ├── README.md                # checklist de evidências mínimas, mapeado ao roteiro
│   ├── screenshots/              # capturas de tela do Console AWS
│   ├── cli-output/                # saídas de comandos salvas em .txt
│   └── logs/                      # exportações de CloudWatch Logs
├── infra/
│   └── template.yaml           # CloudFormation: toda a infraestrutura da stack
├── src/
│   ├── producer_function.py    # Lambda atrás do API Gateway (cópia legível do código embutido no template)
│   └── consumer_function.py    # Lambda disparada pela fila SQS (idem)
├── scripts/
│   ├── deploy.sh                # deploy da stack via AWS CLI
│   ├── cleanup.sh               # remoção da stack + checagem de resíduos
│   ├── load_test.py             # gera carga e mede latência/sucesso
│   └── analyze_results.py       # gera os gráficos usados no artigo
├── results/
│   ├── raw/                     # CSVs brutos do teste de carga
│   └── figures/                 # gráficos gerados a partir dos CSVs
└── paper/
    └── main.tex                 # artigo em formato IEEE (IEEEtran)
```

## Origem do código

Este projeto parte do laboratório didático da Aula 07 (`Aula 07/04_software/psi5120_a07_lambda_function.py` e `template_cloudformation.yaml`, disponíveis no material da disciplina), que demonstra o mecanismo básico de retry/DLQ com uma única função Lambda. A lógica de normalização de evento SQS/direto e a demonstração de falha controlada foram mantidas como estão nesse laboratório; o que foi adicionado está descrito em `docs/DECISIONS.md`.

## Início rápido

```bash
chmod +x scripts/deploy.sh scripts/cleanup.sh
./scripts/deploy.sh SEU_EMAIL@exemplo.com psi5120-tf-serverless us-east-1 psi5120
```

Depois, siga o `docs/ROTEIRO_EXECUCAO.md` a partir da seção 4 para testar, gerar carga e limpar os recursos.

## Autoria

Trabalho individual (grupo formalmente cadastrado, executado por um integrante), disciplina PSI5120 — 2026.
