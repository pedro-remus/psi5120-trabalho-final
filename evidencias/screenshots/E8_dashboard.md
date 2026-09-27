# E8 — CloudWatch Dashboard (renderizado via API, não captura manual de tela)

As imagens `E8_dashboard_*.png` nesta pasta foram geradas via
`aws cloudwatch get-metric-widget-image` (API do CloudWatch que renderiza um widget
de métricas como PNG), em vez de captura de tela manual do Console — método mais
reprodutível e que não depende de acesso à sessão logada do navegador.

| Arquivo | Widget do dashboard `psi5120-tf-serverless-dashboard` |
|---|---|
| `E8_dashboard_lambdas.png` | Invocações e erros das duas Lambdas (producer/consumer) |
| `E8_dashboard_filas.png` | Mensagens visíveis na fila principal e na DLQ |
| `E8_dashboard_metrica_custom.png` | Métrica customizada `EventosProcessados`, por `Resultado` |

## Bug encontrado e corrigido durante a coleta desta evidência

A primeira renderização de `E8_dashboard_metrica_custom.png` veio **vazia**, apesar de
`aws cloudwatch list-metrics` confirmar que a métrica `EventosProcessados` estava sendo
publicada normalmente. Causa raiz: a função `consumer_function.py` publicava cada ponto
com **duas dimensões** (`TipoEvento` + `Resultado`), mas o widget do dashboard (definido
em `infra/template.yaml`) consultava por **apenas uma** (`Resultado`). No CloudWatch, o
conjunto de dimensões faz parte da identidade da métrica — uma consulta com um
subconjunto de dimensões não casa com pontos publicados com dimensões extras.

Correção: `_emitir_metrica` passou a publicar apenas com a dimensão `Resultado` (removida
`TipoEvento`, que não era usada em nenhum widget). Corrigido em `src/consumer_function.py`
e na cópia embutida em `infra/template.yaml`, seguido de um redeploy da stack (só a
função `consumer` foi atualizada). Confirmado com `aws cloudwatch get-metric-statistics`
filtrando só por `Resultado` antes de regerar a imagem acima. Ver `docs/DECISIONS.md`
para o registro completo desta decisão.

## Sobre a janela de tempo das imagens

`get-metric-widget-image` não recebe uma janela padrão útil quando `start`/`end` não são
informados (usa um intervalo amplo, deixando os eventos do teste concentrados numa ponta
do gráfico). As imagens finais usam `start`/`end` explícitos, enquadrando exatamente o
período de cada rodada de teste:

- `E8_dashboard_lambdas.png` e `E8_dashboard_filas.png`: 2026-09-27T21:14Z – 21:29Z
  (Passos 4 e 5 originais).
- `E8_dashboard_metrica_custom.png`: 2026-09-27T22:23Z – 22:26Z (rodada adicional feita
  após a correção do bug de dimensão, para popular o widget com os 3 tipos de resultado).
  Note que `gravado` e `duplicata_idempotente` caem no mesmo bucket de 60s e por isso
  aparecem sobrepostos visualmente — confirmado via `get-metric-statistics` que os dois
  pontos existem de fato (1 cada), a sobreposição é só uma coincidência de timing entre
  chamadas de teste manuais disparadas em sequência rápida, não um erro nos dados.
