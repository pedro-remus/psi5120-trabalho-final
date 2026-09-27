# Evidências de execução

Esta pasta guarda as evidências de que cada etapa do `docs/ROTEIRO_EXECUCAO.md` foi realmente executada na AWS — prints, saídas de comando e logs. É o material bruto usado para preencher a seção *Experimental Evaluation* do artigo (`paper/main.tex`) e para provar, se pedido, que o trabalho foi de fato implantado e testado (não só escrito).

Convenção de nomes: `E<número>_<descrição-curta>.<ext>`, numerado na mesma ordem das seções do roteiro (mesma convenção já usada nas pastas `evidencias/` das Aulas 04–06 da disciplina).

## Onde salvar cada tipo de evidência

- `screenshots/` — capturas de tela do Console AWS (CloudFormation, Lambda, DynamoDB, CloudWatch, SNS, etc.) e do e-mail de alarme recebido.
- `cli-output/` — saída de comandos do terminal salva em `.txt` (ex.: `aws sts get-caller-identity`, `aws cloudformation describe-stacks`, `aws dynamodb scan`, resultado do `curl`).
- `logs/` — exportações de CloudWatch Logs (ex.: saída de `aws logs tail`).

Os CSVs brutos do teste de carga ficam em `results/raw/` e os gráficos gerados a partir deles em `results/figures/` (não duplicar aqui — ver `docs/ROTEIRO_EXECUCAO.md` seções 5–6).

## Checklist de evidências mínimas (mapeado ao roteiro)

| ID | O que capturar | Onde (roteiro) | Arquivo sugerido |
|---|---|---|---|
| E1 | Saída de `aws sts get-caller-identity` confirmando o usuário IAM | Seção 2.3 | `cli-output/E1_identidade_aws.txt` |
| E2 | Saída completa do `./scripts/deploy.sh` (tabela de Outputs) | Seção 3 | `cli-output/E2_deploy_outputs.txt` |
| E2b | Snapshot completo dos 19 recursos criados (CloudFormation, Lambda, SQS, DynamoDB, API Gateway, CloudWatch, SNS), consultado via CLI logo após o deploy | Seção 3 | `cli-output/E2b_infraestrutura_criada.txt` |
| E3 | E-mail de "Subscription Confirmation" do SNS, confirmado | Seção 3 | `screenshots/E3_confirmacao_sns.png` |
| E4 | Resposta HTTP 202 do evento normal + item correspondente no `dynamodb scan` | Seção 4.1 | `cli-output/E4_evento_normal.txt` |
| E5 | `ApproximateNumberOfMessages` da DLQ = 1 após falha controlada + e-mail de alarme recebido | Seção 4.2 | `cli-output/E5_dlq.txt`, `screenshots/E5_alarme_email.pdf` |
| E6 | Trecho do CloudWatch Logs mostrando `"fase": "duplicata_idempotente"` no teste de idempotência | Seção 4.3 | `logs/E6_idempotencia.txt` |
| E7 | Resumo impresso pelo `load_test.py` (taxa de sucesso, p50/p95) | Seção 5 | `cli-output/E7_load_test_resumo.txt` |
| E8 | Widgets do CloudWatch Dashboard (gerados via `get-metric-widget-image`, não print manual) | (após seção 5, com dados já fluindo) | `screenshots/E8_dashboard_*.png` + `screenshots/E8_dashboard.md` |
| E9 | Saída do `./scripts/cleanup.sh` confirmando ausência de resíduos | Seção 7 | `cli-output/E9_limpeza.txt` |

Atualize esta tabela se adicionar/remover algum teste — e registre a mudança em `docs/DECISIONS.md` se ela alterar o que o artigo relata.
