# dashboard-automation

Pipeline automatizado de geração de dashboards HTML a partir de dados do Databricks — substitui o
processo manual de exportar CSV e colar em um prompt de chat.

Contexto completo do desenho: ver o design doc na sessão de brainstorming original
(`docs/superpowers/specs/2026-09-21-dashboard-automation-design.md`, no repositório
`pagadoria-comissoes`, onde este projeto foi planejado).

## Setup

```bash
uv sync
cp .env.example .env   # preencha com as credenciais reais — .env nunca é commitado
```

> `uv run` **não** carrega o `.env` automaticamente — passe `--env-file .env` em todo comando que
> precise das credenciais, senão a primeira execução falha com `KeyError:
> 'DATABRICKS_SERVER_HOSTNAME'`.

## Rodar um dashboard sob demanda

```bash
uv run --env-file .env run-dashboard dashboards/example-dashboard.yaml --trigger=manual
```

## Adicionar um dashboard novo

1. Copie `dashboards/example-dashboard.yaml` para `dashboards/<novo-id>.yaml` e ajuste `id`, `nome`,
   `query`, `prompt`, `publicacao` e `notificacao`.
2. Se o dashboard deve rodar em um horário fixo, defina `schedule.cron` (formato Quartz, o mesmo
   exigido pelo Databricks Workflows — ex.: `"0 0 7 1 * ?"` para as 7h do dia 1 de cada mês).
   Deixe `schedule.enabled: false` até o item 3 abaixo ser resolvido.
3. **Antes de marcar `schedule.enabled: true` ou rodar manualmente em produção**: se o dashboard
   pode conter dado sensível, confirme com compliance/segurança que o envio via API da Anthropic é
   aceitável para esse dashboard específico (ver "Gate de compliance" abaixo).
4. Rode `uv run python scripts/generate_bundle.py` para regenerar
   `resources/dashboards.generated.yml` incluindo o job do novo dashboard.
5. Rode `databricks bundle deploy -t dev` (requer Databricks CLI autenticado) para publicar o Job.
   **Atenção**: o bundle gerado é um ponto de partida, não um deploy pronto — ele ainda precisa ser
   completado para o workspace de destino antes de rodar de verdade (ver "Pendências do bundle"
   abaixo).

Nenhum passo acima exige alterar código Python — só o arquivo YAML do dashboard.

## Pendências do bundle (antes do primeiro deploy real)

`resources/dashboards.generated.yml` descreve os jobs, mas **não** é suficiente para um deploy
funcional: o job falha ao rodar até que os itens abaixo sejam preenchidos para o workspace alvo.
Nada disso é inferível deste repositório — depende de políticas de compute e de scopes de secret do
workspace do operador.

- **Compute**: a task não tem binding de compute. Adicione `job_cluster_key` (+ um `job_clusters`
  com `new_cluster`), `existing_cluster_id`, ou um `environment_key` serverless, conforme a política
  de compute do workspace.
- **Wheel**: a task é `python_wheel_task`, mas não há entrada `libraries` anexando o wheel buildado
  ao job — sem isso o pacote `dashboard_automation` não existe no cluster.
- **Secrets**: Jobs do Databricks **não leem `.env`**. `ANTHROPIC_API_KEY`, `DATABRICKS_TOKEN`,
  `AZURE_STORAGE_CONNECTION_STRING` e as `SMTP_*` precisam ser injetadas via Databricks secret
  scopes (ex.: `spark_env_vars` / `{{secrets/<scope>/<chave>}}`), com o scope criado previamente.

## Gate de compliance

Alguns dashboards podem conter dado sensível. **Nenhum dashboard com dado sensível deve ser
publicado usando a Anthropic API diretamente em produção sem aprovação explícita de
compliance/segurança** — seja aprovando o envio externo, seja optando por um caminho que mantenha o
dado dentro do perímetro do Databricks (ex.: model serving interno, se disponível no workspace —
confirmar com o time de plataforma/dados). Essa validação é um pré-requisito de rollout por
dashboard, não algo resolvido pela arquitetura sozinha.

## Publicação: Azure Blob vs. Databricks nativo

As duas implementações (`AzureBlobPublisher` e `DatabricksNativePublisher`) coexistem. Escolha por
dashboard via `publicacao.destino` no YAML. Ainda não há uma padronização definitiva — teste as duas
em dashboards reais antes de decidir.

## Testes

```bash
uv run pytest
```

## Integração manual (antes de migrar os primeiros dashboards reais)

A suíte automatizada cobre cada etapa isoladamente com fakes/mocks, mas não substitui uma validação
ponta a ponta contra serviços reais. Antes de migrar os primeiros dashboards reais para este
pipeline:

1. Escolha um dashboard de teste com **dado não-sensível** (nunca o primeiro teste ponta a ponta com
   dado sensível, mesmo com `ANTHROPIC_API_KEY` configurada).
2. Rode `uv run --env-file .env run-dashboard dashboards/<dashboard-de-teste>.yaml --trigger=manual`
   com credenciais reais no `.env`.
3. Confirme manualmente: a query rodou no warehouse certo, o HTML gerado abriu corretamente no
   navegador, o link "latest" ficou acessível no destino escolhido, e a notificação (email/Slack/
   Teams) chegou com o link correto.
4. Só depois disso, avalie levar um dashboard com dado potencialmente sensível — e só após o gate de
   compliance acima ser resolvido para ele especificamente.

## Próximos passos (fora do escopo desta fase)

- **Completar o bundle gerado para o workspace alvo** — binding de compute, `libraries` com o wheel
  e injeção de secrets via secret scopes. Sem isso o `databricks bundle deploy` produz um job que
  não roda. Detalhes em "Pendências do bundle" acima; exige acesso a um workspace real.
- Self-service: permitir que um solicitante não-técnico peça um dashboard novo em linguagem
  natural, sem escrever a query SQL manualmente (exigiria um sistema de texto-para-SQL com
  guardrails próprios — deliberadamente fora desta Fase 1, ver design doc).
- Definir a política de retenção do diretório `archive/` (hoje cresce indefinidamente).
- Agregação/truncamento de dados para dashboards com volumes grandes antes de montar o prompt.
