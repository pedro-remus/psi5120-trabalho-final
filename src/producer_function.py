"""
Lambda "producer" - fica atras do API Gateway (HTTP API).

Recebe POST /events, valida o corpo da requisicao e publica o payload
na fila SQS principal. Nao processa a regra de negocio: apenas
desacopla a ingestao do processamento (feito pela consumer_function).

Extensao do laboratorio serverless da Aula 07 de PSI5120. Ver
docs/DECISIONS.md para o raciocinio por tras desta divisao produtor/consumidor.
"""

import json
import os
import uuid
from datetime import datetime, timezone

import boto3

QUEUE_URL = os.environ["QUEUE_URL"]
AMBIENTE = os.environ.get("AMBIENTE", "didatico")

sqs = boto3.client("sqs")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _resposta(status_code, corpo):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(corpo, ensure_ascii=False),
    }


def lambda_handler(event, context):
    request_id = getattr(context, "aws_request_id", "contexto-local")

    corpo_bruto = event.get("body")
    if event.get("isBase64Encoded"):
        import base64

        corpo_bruto = base64.b64decode(corpo_bruto or "").decode("utf-8")

    if not corpo_bruto:
        return _resposta(400, {"erro": "Corpo da requisicao vazio; envie um objeto JSON."})

    try:
        payload = json.loads(corpo_bruto)
    except json.JSONDecodeError:
        return _resposta(400, {"erro": "Corpo da requisicao nao e um JSON valido."})

    if not isinstance(payload, dict):
        return _resposta(400, {"erro": "Corpo da requisicao deve ser um objeto JSON."})

    payload.setdefault("event_id", str(uuid.uuid4()))
    payload.setdefault("tipo_evento", "nao_definido")

    valor = payload.get("valor")
    if valor is not None and (isinstance(valor, bool) or not isinstance(valor, (int, float))):
        return _resposta(400, {"erro": "Campo 'valor', quando presente, deve ser numerico."})

    log_base = {
        "fase": "producer_recebeu",
        "ambiente": AMBIENTE,
        "request_id": request_id,
        "event_id": payload["event_id"],
        "tipo_evento": payload["tipo_evento"],
        "timestamp": _now(),
    }
    print(json.dumps(log_base, ensure_ascii=False))

    sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps(payload, ensure_ascii=False))

    print(json.dumps({**log_base, "fase": "producer_publicou"}, ensure_ascii=False))

    return _resposta(
        202,
        {
            "status": "aceito",
            "event_id": payload["event_id"],
            "mensagem": "Evento publicado na fila para processamento assincrono.",
        },
    )
