#!/usr/bin/env bash
# Remove a stack CloudFormation do Trabalho Final e verifica residuos.
#
# Uso:
#   ./scripts/cleanup.sh [nome-da-stack] [regiao] [perfil-aws]

set -euo pipefail

STACK_NAME="${1:-psi5120-tf-serverless}"
REGION="${2:-us-east-1}"
PROFILE="${3:-default}"

echo "== Apagando stack '$STACK_NAME' na regiao '$REGION' (perfil '$PROFILE') =="
aws cloudformation delete-stack \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --profile "$PROFILE"

echo "Aguardando conclusao da remocao (pode levar alguns minutos)..."
aws cloudformation wait stack-delete-complete \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --profile "$PROFILE"

echo "Stack removida."
echo
echo "== Verificacao de residuos com prefixo '$STACK_NAME' =="

echo "-- Funcoes Lambda --"
aws lambda list-functions --region "$REGION" --profile "$PROFILE" \
  --query "Functions[?starts_with(FunctionName, '$STACK_NAME')].FunctionName" --output text

echo "-- Filas SQS --"
aws sqs list-queues --region "$REGION" --profile "$PROFILE" \
  --queue-name-prefix "$STACK_NAME" --output text

echo "-- Tabelas DynamoDB --"
aws dynamodb list-tables --region "$REGION" --profile "$PROFILE" \
  --query "TableNames[?starts_with(@, '$STACK_NAME')]" --output text

echo "-- Log groups --"
aws logs describe-log-groups --region "$REGION" --profile "$PROFILE" \
  --log-group-name-prefix "/aws/lambda/$STACK_NAME" \
  --query "logGroups[].logGroupName" --output text

echo
echo "Se algum recurso acima ainda aparecer, remova manualmente pelo Console."
echo "Log groups de Lambda NAO sao removidos automaticamente com a funcao/stack em alguns casos; confira sempre."
