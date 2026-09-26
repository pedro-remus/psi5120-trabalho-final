#!/usr/bin/env python3
"""
Gera carga contra o endpoint POST /events do pipeline do Trabalho Final
e registra latencia, sucesso/erro por requisicao em um CSV.

So usa biblioteca padrao do Python (urllib + concurrent.futures) para nao
exigir instalar dependencias extras.

Uso:
    python scripts/load_test.py --url https://SEU-ID.execute-api.us-east-1.amazonaws.com \
        --total 100 --concorrencia 10 --taxa-falha 0.1

O parametro --taxa-falha controla a fracao de eventos enviados com
"forcar_falha": true, para observar o caminho de retry -> DLQ sob carga.

Saida: results/raw/load_test_<timestamp>.csv, uma linha por requisicao,
com colunas: indice,event_id,forcar_falha,status_http,latencia_ms,erro
"""

import argparse
import csv
import json
import random
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "raw"


def enviar_evento(url, indice, forcar_falha):
    event_id = str(uuid.uuid4())
    corpo = {
        "event_id": event_id,
        "tipo_evento": "load_test",
        "valor": round(random.uniform(0, 1000), 2),
        "forcar_falha": forcar_falha,
    }
    dados = json.dumps(corpo).encode("utf-8")
    req = urllib.request.Request(
        url.rstrip("/") + "/events",
        data=dados,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    inicio = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status_http = resp.status
            resp.read()
            erro = ""
    except urllib.error.HTTPError as exc:
        status_http = exc.code
        erro = exc.reason
    except urllib.error.URLError as exc:
        status_http = 0
        erro = str(exc.reason)
    latencia_ms = (time.perf_counter() - inicio) * 1000

    return {
        "indice": indice,
        "event_id": event_id,
        "forcar_falha": forcar_falha,
        "status_http": status_http,
        "latencia_ms": round(latencia_ms, 2),
        "erro": erro,
    }


def main():
    parser = argparse.ArgumentParser(description="Teste de carga do pipeline serverless.")
    parser.add_argument("--url", required=True, help="URL base da API (Outputs.ApiEndpoint da stack)")
    parser.add_argument("--total", type=int, default=100, help="Total de requisicoes a enviar")
    parser.add_argument("--concorrencia", type=int, default=10, help="Requisicoes simultaneas")
    parser.add_argument(
        "--taxa-falha",
        type=float,
        default=0.1,
        help="Fracao (0 a 1) de eventos enviados com forcar_falha=true",
    )
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    saida_csv = RESULTS_DIR / f"load_test_{timestamp}.csv"

    print(f"Disparando {args.total} requisicoes (concorrencia={args.concorrencia}, "
          f"taxa_falha={args.taxa_falha}) contra {args.url}/events ...")

    resultados = []
    with ThreadPoolExecutor(max_workers=args.concorrencia) as executor:
        futuros = []
        for i in range(args.total):
            forcar_falha = random.random() < args.taxa_falha
            futuros.append(executor.submit(enviar_evento, args.url, i, forcar_falha))

        for futuro in as_completed(futuros):
            resultados.append(futuro.result())
            if len(resultados) % max(1, args.total // 10) == 0:
                print(f"  {len(resultados)}/{args.total} concluidas")

    resultados.sort(key=lambda r: r["indice"])

    with open(saida_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["indice", "event_id", "forcar_falha", "status_http", "latencia_ms", "erro"]
        )
        writer.writeheader()
        writer.writerows(resultados)

    latencias = sorted(r["latencia_ms"] for r in resultados)
    sucesso = sum(1 for r in resultados if r["status_http"] == 202)
    n = len(latencias)
    p50 = latencias[int(n * 0.50)] if n else 0
    p95 = latencias[min(int(n * 0.95), n - 1)] if n else 0

    print("\n--- Resumo ---")
    print(f"Total: {n} | Sucesso (HTTP 202): {sucesso} ({sucesso / n * 100:.1f}%)")
    print(f"Latencia p50: {p50:.1f} ms | p95: {p95:.1f} ms")
    print(f"CSV salvo em: {saida_csv}")


if __name__ == "__main__":
    main()
