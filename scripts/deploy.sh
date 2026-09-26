#!/usr/bin/env bash
# Sobe (cria ou atualiza) a stack CloudFormation do Trabalho Final.
#
# Uso:
#   ./scripts/deploy.sh SEU_EMAIL@exemplo.com [nome-da-stack] [regiao] [perfil-aws]
#
# Exemplo:
#   ./scripts/deploy.sh pedro.prda@gmail.com psi5120-tf-serverless us-east-1 psi5120
#
# Antes de rodar, revise docs/ROTEIRO_EXECUCAO.md.

set -euo pipefail

EMAIL="${1:?Informe o e-mail para receber alarmes da DLQ como primeiro argumento}"
STACK_NAME="${2:-psi5120-tf-serverless}"
REGION="${3:-us-east-1}"
PROFILE="${4:-default}"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="$DIR/infra/template.yaml"

echo "== Identidade AWS atual =="
aws sts get-caller-identity --region "$REGION" --profile "$PROFILE"

echo
echo "== Deploy da stack '$STACK_NAME' na regiao '$REGION' (perfil '$PROFILE') =="
aws cloudformation deploy \
  --stack-name "$STACK_NAME" \
  --template-file "$TEMPLATE" \
  --region "$REGION" \
  --profile "$PROFILE" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
      NotificationEmail="$EMAIL" \
      Ambiente=trabalho-final \
      FalhaControlada=true \
  --tags Disciplina=PSI5120 Trabalho=Final

echo
echo "== Outputs da stack =="
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --profile "$PROFILE" \
  --query "Stacks[0].Outputs" \
  --output table

echo
echo "IMPORTANTE: confirme a assinatura do SNS no e-mail '$EMAIL' (a AWS envia um"
echo "e-mail de confirmacao) para que os alarmes da DLQ cheguem de fato."
