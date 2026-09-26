# Roteiro de execução (passo a passo para quem nunca usou AWS)

Este roteiro assume que você não tem nenhuma experiência prévia com o Console ou o CLI da AWS. Siga os passos **na ordem**. Cada comando vem acompanhado de uma explicação do que ele faz e do que você deve conferir depois de rodá-lo.

Convenções usadas abaixo:
- Comandos de terminal aparecem em blocos ```bash```. Rode-os no WSL/Ubuntu (mesmo ambiente usado no Tutorial 2 da Aula 07) ou em qualquer terminal com `bash` e o AWS CLI instalado.
- Troque `SEU_EMAIL@exemplo.com` pelo seu e-mail de verdade.
- Troque `psi5120-tf-serverless` pelo nome de stack que preferir, se quiser (mas mantenha o mesmo nome em todos os comandos depois).

---

## 1. Pré-requisitos: conta AWS e usuário IAM

1. Você precisa de uma conta AWS (a mesma usada nas aulas anteriores serve).
2. **Nunca use as credenciais da conta root do dia a dia.** No Console AWS, vá em **IAM → Users → Create user**, crie um usuário (ex.: `psi5120-trabalho-final`) e anexe a policy gerenciada `AdministratorAccess` **apenas para o escopo deste trabalho** (em produção isso seria excesso de permissão; aqui simplifica o roteiro didático — ver `docs/DECISIONS.md` se quiser justificar essa escolha no artigo).
3. Nesse usuário, vá em **Security credentials → Access keys → Create access key** e escolha o caso de uso "Command Line Interface (CLI)". Anote a **Access Key ID** e a **Secret Access Key** — a secret só aparece uma vez.

## 2. Instalar e configurar o AWS CLI

1. Verifique se já está instalado:
   ```bash
   aws --version
   ```
   Se não aparecer nada, siga a documentação oficial de instalação do AWS CLI v2 para o seu sistema (o mesmo procedimento já usado no Tutorial 2 da Aula 07).

2. Configure um perfil nomeado (evita conflito com outros perfis que você já tenha):
   ```bash
   aws configure --profile psi5120
   ```
   Informe, quando pedido:
   - AWS Access Key ID: (a que você anotou no passo 1.3)
   - AWS Secret Access Key: (idem)
   - Default region name: `us-east-1` (ou a região que você usar; mantenha a mesma em todos os comandos)
   - Default output format: `json`

3. Confirme que funcionou:
   ```bash
   aws sts get-caller-identity --profile psi5120
   ```
   **O que conferir:** a saída deve mostrar `UserId`, `Account` e `Arn` do usuário IAM que você criou. Se der erro de credenciais, revise o passo 2.2.

   **Evidência a salvar:** cole essa saída em `evidencias/cli-output/E1_identidade_aws.txt` (ver `evidencias/README.md`).

4. **Nunca** coloque essas credenciais em nenhum arquivo do repositório. Elas ficam apenas em `~/.aws/credentials`, gerenciadas pelo próprio comando `aws configure`. O `.gitignore` deste repositório já bloqueia arquivos comuns de credenciais, mas a responsabilidade final é sua: nunca faça `git add` de um arquivo `.env` ou similar com chaves.

## 3. Deploy da stack CloudFormation

O script `scripts/deploy.sh` faz tudo isso por você. Rode a partir da raiz do repositório:

```bash
chmod +x scripts/deploy.sh scripts/cleanup.sh
./scripts/deploy.sh SEU_EMAIL@exemplo.com psi5120-tf-serverless us-east-1 psi5120
```

**O que este comando faz:** cria (ou atualiza) todos os recursos definidos em `infra/template.yaml` — DynamoDB, filas SQS, as duas funções Lambda, API Gateway, tópico SNS, alarme e dashboard do CloudWatch.

**O que conferir:**
- O comando deve terminar imprimindo uma tabela de "Outputs" da stack. Guarde o valor de `ApiEndpoint` (você vai usá-lo nos próximos passos).
- Se aparecer erro `ROLLBACK_COMPLETE` ou `CREATE_FAILED`, veja a seção **Troubleshooting** no final deste documento.
- Isso demora tipicamente 1 a 3 minutos (bem mais rápido que subir um cluster EKS).

**Evidência a salvar:** cole a saída completa do comando (incluindo a tabela de Outputs) em `evidencias/cli-output/E2_deploy_outputs.txt`.

**Confirme a assinatura do e-mail:** a AWS manda um e-mail de "AWS Notification - Subscription Confirmation" para o endereço que você passou. **Você precisa clicar no link "Confirm subscription"** dentro dele, senão o alarme da DLQ nunca chega até você por e-mail (a stack sobe normalmente mesmo sem essa confirmação, mas a notificação não funciona).

**Evidência a salvar:** print da tela de confirmação em `evidencias/screenshots/E3_confirmacao_sns.png`.

## 4. Testes manuais dos três cenários

Pegue o valor de `ApiEndpoint` que apareceu no passo 3 (algo como `https://abc123xyz.execute-api.us-east-1.amazonaws.com`).

### 4.1 Evento normal (caminho feliz)

```bash
curl -i -X POST "https://SEU-ID.execute-api.us-east-1.amazonaws.com/events" \
  -H "Content-Type: application/json" \
  -d '{"tipo_evento": "teste_manual", "valor": 42.5}'
```

**O que conferir:** resposta HTTP `202` com um `event_id` no corpo. Depois de alguns segundos, confira que o item foi gravado no DynamoDB:

```bash
aws dynamodb scan --table-name psi5120-tf-serverless-events --region us-east-1 --profile psi5120
```

Deve aparecer um item com o `event_id` retornado pela chamada anterior e `"status": "processado"`.

**Evidência a salvar:** cole a resposta do `curl` e do `dynamodb scan` em `evidencias/cli-output/E4_evento_normal.txt`.

### 4.2 Falha controlada → DLQ

```bash
curl -i -X POST "https://SEU-ID.execute-api.us-east-1.amazonaws.com/events" \
  -H "Content-Type: application/json" \
  -d '{"tipo_evento": "teste_falha", "forcar_falha": true}'
```

**O que conferir:** a API ainda responde `202` (ela só publica na fila; quem falha é o consumidor). Espere ~1 minuto (a fila tem `VisibilityTimeout=30s` e `maxReceiveCount=2`, então a mensagem é reprocessada e falha 2 vezes antes de ir para a DLQ) e confira:

```bash
aws sqs get-queue-attributes \
  --queue-url "$(aws cloudformation describe-stacks --stack-name psi5120-tf-serverless --region us-east-1 --profile psi5120 --query "Stacks[0].Outputs[?OutputKey=='DLQUrl'].OutputValue" --output text)" \
  --attribute-names ApproximateNumberOfMessages \
  --region us-east-1 --profile psi5120
```

**O que conferir:** `ApproximateNumberOfMessages` deve ser `1` (ou mais, se você repetiu o teste). Você também deve receber o e-mail de alarme do CloudWatch (se confirmou a assinatura no passo 3).

**Evidência a salvar:** saída do `get-queue-attributes` em `evidencias/cli-output/E5_dlq.txt` e print do e-mail de alarme recebido em `evidencias/screenshots/E5_alarme_email.png`.

> **Atenção:** não faça `aws sqs receive-message` manualmente na fila principal durante esse teste — ler a mensagem manualmente também consome uma tentativa de recebimento e atrapalha a contagem (mesmo alerta já dado no README da Aula 07).

### 4.3 Idempotência (reenvio do mesmo event_id)

```bash
curl -i -X POST "https://SEU-ID.execute-api.us-east-1.amazonaws.com/events" \
  -H "Content-Type: application/json" \
  -d '{"event_id": "teste-idempotencia-001", "tipo_evento": "teste_idempotente", "valor": 1}'

# rode o mesmo comando de novo, exatamente igual
curl -i -X POST "https://SEU-ID.execute-api.us-east-1.amazonaws.com/events" \
  -H "Content-Type: application/json" \
  -d '{"event_id": "teste-idempotencia-001", "tipo_evento": "teste_idempotente", "valor": 1}'
```

**O que conferir:** nos CloudWatch Logs da função consumer (`/aws/lambda/psi5120-tf-serverless-consumer`), a segunda execução deve logar `"fase": "duplicata_idempotente"` em vez de `"fase": "gravado"`. O DynamoDB deve ter só 1 item com esse `event_id` (não dois).

Para ver os logs pelo CLI:
```bash
aws logs tail /aws/lambda/psi5120-tf-serverless-consumer --region us-east-1 --profile psi5120 --since 10m
```

**Evidência a salvar:** cole o trecho relevante do log (mostrando `"fase": "gravado"` na primeira execução e `"fase": "duplicata_idempotente"` na segunda) em `evidencias/logs/E6_idempotencia.txt`.

## 5. Rodar o teste de carga

```bash
python3 scripts/load_test.py \
  --url "https://SEU-ID.execute-api.us-east-1.amazonaws.com" \
  --total 150 \
  --concorrencia 15 \
  --taxa-falha 0.1
```

**O que este comando faz:** dispara 150 requisições (15 simultâneas por vez), sendo ~10% delas com `forcar_falha: true`, mede a latência de cada uma e salva tudo em `results/raw/load_test_<timestamp>.csv`.

**O que conferir:** o resumo impresso no final (taxa de sucesso, latência p50/p95). Rode mais de uma vez se quiser comparar cenários (ex.: `--taxa-falha 0` vs `--taxa-falha 0.3`) — isso vira o experimento principal da seção de avaliação do artigo.

**Evidência a salvar:** cole o resumo impresso no terminal em `evidencias/cli-output/E7_load_test_resumo.txt`. Depois de rodar o teste de carga, abra o CloudWatch Dashboard (link nos Outputs da stack ou Console → CloudWatch → Dashboards) e salve um print em `evidencias/screenshots/E8_dashboard.png` — os widgets só ficam interessantes depois que houver tráfego de verdade.

## 6. Gerar os gráficos para o artigo

```bash
pip install --user pandas matplotlib   # só na primeira vez
python3 scripts/analyze_results.py
```

**O que conferir:** arquivos `.png` novos em `results/figures/` e um `resumo_estatistico.txt` com os números prontos para citar no artigo.

## 7. Limpeza (fazer sempre ao terminar de coletar dados)

```bash
./scripts/cleanup.sh psi5120-tf-serverless us-east-1 psi5120
```

**O que conferir:** o script lista, ao final, se sobrou alguma função Lambda, fila, tabela ou log group com o prefixo da stack. Se sobrar algo, remova manualmente pelo Console AWS antes de encerrar a sessão, para não gerar cobrança inesperada.

**Evidência a salvar:** cole a saída completa do script em `evidencias/cli-output/E9_limpeza.txt` — é a prova de que os recursos foram desligados ao final do trabalho.

## 8. Troubleshooting (erros mais prováveis)

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `An error occurred (AccessDenied)` | O usuário IAM não tem permissão suficiente, ou `CAPABILITY_NAMED_IAM` foi esquecido | Confirme que usou o `deploy.sh` (ele já inclui a flag); revise as policies do usuário IAM |
| Stack fica em `ROLLBACK_COMPLETE` | Algum recurso não pôde ser criado (ex.: nome de tabela/fila já existe de um deploy anterior mal limpo) | Rode `aws cloudformation delete-stack` para essa stack e tente o deploy de novo com um nome diferente |
| `curl` retorna HTML de erro em vez de JSON | Endpoint errado (faltou `/events` no final, ou a stage não é `$default`) | Confirme o valor exato de `ApiEndpoint` nos Outputs e sempre acrescente `/events` |
| Não chega e-mail do alarme | Assinatura do SNS não foi confirmada | Procure o e-mail "Subscription Confirmation" (inclusive em spam) e clique no link |
| `region errada` / recursos não aparecem no Console | Você está olhando outra região no navegador | Confira que a região selecionada no canto superior direito do Console é a mesma passada em `--region` |
| `Throttling` / `Rate exceeded` durante o load test | Taxa de requisições passou de algum limite padrão da conta (raro dentro do Free Tier para esses volumes) | Reduza `--concorrencia` no `load_test.py` |
