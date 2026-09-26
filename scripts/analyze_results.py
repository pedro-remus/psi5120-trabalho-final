#!/usr/bin/env python3
"""
Le o CSV mais recente gerado por load_test.py e gera as figuras usadas
no artigo (results/figures/*.png).

Requer pandas e matplotlib (pip install pandas matplotlib).

Uso:
    python scripts/analyze_results.py [caminho_do_csv]

Sem argumento, usa o CSV mais recente em results/raw/.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "results" / "raw"
FIGURES_DIR = Path(__file__).resolve().parent.parent / "results" / "figures"


def csv_mais_recente():
    candidatos = sorted(RAW_DIR.glob("load_test_*.csv"))
    if not candidatos:
        raise SystemExit(f"Nenhum CSV encontrado em {RAW_DIR}. Rode scripts/load_test.py primeiro.")
    return candidatos[-1]


def main():
    caminho = Path(sys.argv[1]) if len(sys.argv) > 1 else csv_mais_recente()
    print(f"Lendo {caminho}")
    df = pd.read_csv(caminho)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # --- Figura 1: histograma de latencia ---
    plt.figure(figsize=(6, 4))
    plt.hist(df["latencia_ms"], bins=30)
    plt.xlabel("Latencia (ms)")
    plt.ylabel("Numero de requisicoes")
    plt.title("Distribuicao de latencia - POST /events")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "latencia_histograma.png", dpi=150)
    plt.close()

    # --- Figura 2: latencia ao longo da execucao ---
    plt.figure(figsize=(6, 4))
    plt.plot(df["indice"], df["latencia_ms"], marker=".", linestyle="none")
    plt.xlabel("Indice da requisicao (ordem de disparo)")
    plt.ylabel("Latencia (ms)")
    plt.title("Latencia por requisicao ao longo do teste de carga")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "latencia_serie.png", dpi=150)
    plt.close()

    # --- Figura 3: taxa de sucesso por tipo de evento (normal vs forcar_falha) ---
    resumo = (
        df.assign(sucesso=df["status_http"] == 202)
        .groupby("forcar_falha")["sucesso"]
        .mean()
        .reindex([False, True])
    )
    plt.figure(figsize=(5, 4))
    resumo.plot(kind="bar")
    plt.xticks([0, 1], ["Evento normal", "Evento com forcar_falha"], rotation=0)
    plt.ylabel("Taxa de resposta HTTP 202 (aceito)")
    plt.title("Aceitacao pela API por tipo de evento")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "taxa_sucesso.png", dpi=150)
    plt.close()

    # --- Estatisticas resumidas em texto (para colar no artigo) ---
    n = len(df)
    sucesso = (df["status_http"] == 202).sum()
    p50 = df["latencia_ms"].quantile(0.50)
    p95 = df["latencia_ms"].quantile(0.95)
    p99 = df["latencia_ms"].quantile(0.99)

    resumo_txt = FIGURES_DIR / "resumo_estatistico.txt"
    with open(resumo_txt, "w", encoding="utf-8") as f:
        f.write(f"Fonte: {caminho.name}\n")
        f.write(f"Total de requisicoes: {n}\n")
        f.write(f"Sucesso (HTTP 202): {sucesso} ({sucesso / n * 100:.1f}%)\n")
        f.write(f"Latencia p50: {p50:.1f} ms\n")
        f.write(f"Latencia p95: {p95:.1f} ms\n")
        f.write(f"Latencia p99: {p99:.1f} ms\n")
        f.write(f"Latencia media: {df['latencia_ms'].mean():.1f} ms\n")
        f.write(f"Latencia minima: {df['latencia_ms'].min():.1f} ms\n")
        f.write(f"Latencia maxima: {df['latencia_ms'].max():.1f} ms\n")

    print(f"Figuras salvas em {FIGURES_DIR}")
    print(f"Resumo estatistico salvo em {resumo_txt}")
    print(open(resumo_txt, encoding="utf-8").read())


if __name__ == "__main__":
    main()
