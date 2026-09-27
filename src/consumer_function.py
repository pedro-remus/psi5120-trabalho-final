"""
Lambda "consumer" - disparada pelo event source mapping da fila SQS principal.

Esta funcao e uma evolucao direta de psi5120_a07_lambda_function.py
(Aula 07 de PSI5120): a normalizacao de evento SQS/direto e a
demonstracao de falha controlada -> DLQ sao herdadas do laboratorio
original. O que foi adicionado nesta extensao:

  1. persistencia idempotente do resultado em DynamoDB (escrita
     condicional por event_id, ver docs/DECISIONS.md sobre os limites
     dessa abordagem);
  2. emissao de uma metrica customizada no CloudWatch para alimentar
     o dashboard de observabilidade.
"""

import json
import os
import time
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

AMBIENTE = os.environ.get("AMBIENTE", "didatico")
FALHA_CONTROLADA = os.environ.get("FALHA_CONTROLADA", "true").lower() == "true"
TABLE_NAME = os.environ["TABLE_NAME"]
METRIC_NAMESPACE = os.environ.get("METRIC_NAMESPACE", "PSI5120/TrabalhoFinal")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)
cloudwatch = boto3.client("cloudwatch")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _parse_record(record):
    """Converte o body de um registro SQS em objeto JSON de aplicacao."""
    body = record.get("body")
    if body is None:
        raise ValueError("Registro SQS sem campo body")

    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("Body da mensagem SQS nao contem JSON valido") from exc

    if not isinstance(payload, dict):
        raise ValueError("Body da mensagem SQS deve conter um objeto JSON")

    return payload


def _normalize_event(event):
    """Normaliza invocacao direta ou evento SQS da pratica (identico a Aula 07)."""
    if not isinstance(event, dict):
        raise ValueError("O evento Lambda deve ser um objeto JSON")

    if "Records" in event:
        records = event.get("Records")
        if not isinstance(records, list) or not records:
            raise ValueError("Records deve ser uma lista SQS nao vazia")
        if len(records) != 1:
            raise ValueError(
                "A pratica usa BatchSize=1; foi recebido um lote com "
                f"{len(records)} registros. Revise o event source mapping."
            )

        rec = records[0]
        if not isinstance(rec, dict) or rec.get("eventSource") != "aws:sqs":
            raise ValueError("Origem de evento em Records nao suportada nesta pratica")

        payload = _parse_record(rec)
        return {
            "modo": "sqs",
            "message_id": rec.get("messageId"),
            "event_id": payload.get("event_id", rec.get("messageId")),
            "tipo_evento": payload.get("tipo_evento", "nao_definido"),
            "payload": payload,
        }

    return {
        "modo": "direto",
        "message_id": None,
        "event_id": event.get("event_id", "evento-sem-id"),
        "tipo_evento": event.get("tipo_evento", "nao_definido"),
        "payload": event,
    }


def _emitir_metrica(resultado):
    try:
        cloudwatch.put_metric_data(
            Namespace=METRIC_NAMESPACE,
            MetricData=[
                {
                    "MetricName": "EventosProcessados",
                    "Value": 1,
                    "Unit": "Count",
                    "Dimensions": [
                        {"Name": "Resultado", "Value": resultado},
                    ],
                }
            ],
        )
    except ClientError as exc:
        # A emissao de metrica nao deve derrubar o processamento do evento.
        print(json.dumps({"fase": "metrica_falhou", "erro": str(exc)}, ensure_ascii=False))


def _gravar_idempotente(item):
    """Grava o resultado no DynamoDB apenas se o event_id ainda nao existir.

    Retorna True se gravou (primeira vez) e False se era duplicata.
    """
    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(event_id)",
        )
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def lambda_handler(event, context):
    request_id = getattr(context, "aws_request_id", "contexto-local")

    try:
        norm = _normalize_event(event)
    except (TypeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "fase": "normalizacao",
                    "resultado": "erro",
                    "erro": str(exc),
                    "ambiente": AMBIENTE,
                    "request_id": request_id,
                    "timestamp": _now(),
                },
                ensure_ascii=False,
            )
        )
        raise

    log_base = {
        "ambiente": AMBIENTE,
        "request_id": request_id,
        "event_id": norm["event_id"],
        "modo": norm["modo"],
        "tipo_evento": norm["tipo_evento"],
        "timestamp": _now(),
    }
    print(json.dumps({"fase": "inicio", **log_base}, ensure_ascii=False))

    payload = norm["payload"]
    if FALHA_CONTROLADA and payload.get("forcar_falha") is True:
        print(json.dumps({"fase": "falha_controlada", **log_base}, ensure_ascii=False))
        _emitir_metrica("falha_controlada")
        raise RuntimeError("Falha controlada para demonstrar retry e DLQ")

    # Simula validacao de dominio sem acessar servico externo (identico a Aula 07).
    valor = payload.get("valor")
    if valor is not None and (
        isinstance(valor, bool) or not isinstance(valor, (int, float))
    ):
        print(
            json.dumps(
                {"fase": "validacao", "resultado": "valor_invalido", **log_base},
                ensure_ascii=False,
            )
        )
        _emitir_metrica("valor_invalido")
        raise ValueError("Campo valor deve ser numerico")

    time.sleep(0.05)

    item = {
        "event_id": norm["event_id"],
        "status": "processado",
        "modo": norm["modo"],
        "tipo_evento": norm["tipo_evento"],
        "ambiente": AMBIENTE,
        "request_id": request_id,
        "timestamp_processado": _now(),
    }
    if valor is not None:
        # boto3 nao aceita float nativo para atributos Number (exige Decimal);
        # para nao converter, o valor e gravado como String (tipo S), suficiente
        # para fins de auditoria/leitura neste projeto didatico.
        item["valor"] = str(valor)

    gravou = _gravar_idempotente(item)
    fase = "gravado" if gravou else "duplicata_idempotente"
    print(json.dumps({"fase": fase, **log_base}, ensure_ascii=False))
    _emitir_metrica(fase)

    resultado = {
        "status": "processado",
        "idempotente_duplicata": not gravou,
        "event_id": norm["event_id"],
        "modo": norm["modo"],
        "ambiente": AMBIENTE,
        "request_id": request_id,
    }
    print(json.dumps({"fase": "fim", "resultado": resultado, **log_base}, ensure_ascii=False))
    return {"statusCode": 200, "body": json.dumps(resultado, ensure_ascii=False)}
