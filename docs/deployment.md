# Deployment

How the public demo runs in Azure, and how to change it. `docs/setup.md` has the one-time setup (the tools, `azd auth login`, `azd env new`); this page is the reference for what is deployed. Values in angle brackets are your own, kept in the azd environment (`.azure/<env>/.env`, gitignored) or your shell, never in the repo.

## What is deployed

One `azd up` builds the app's image in Azure and creates everything in `infra/` (Bicep), in the resource group `rg-<env>` in eastus2:

| Resource | What it does |
|---|---|
| Container app `ca-web-…` | The one container: the page, the API and the learning engine. At most one replica; minimum 0 (or 1 while judges visit) |
| Container Apps environment `cae-…` | Where the app runs; sends its logs to Azure Monitor |
| Diagnostic setting `logs-to-workspace` | Carries the environment's logs to the workspace, with no key |
| Log Analytics workspace `log-…` | The logs, queried with KQL; 30 days, capped at 0.15 GB a day |
| Container Registry `cr…` (Basic) | The app's image, built here by azd |
| User-assigned identity `id-…` | Who the app signs in as, for every Azure call |
| Storage account `st…`, container `learners` | Learner records, one JSON blob per viewer. Shared keys are off; the app and you each hold Storage Blob Data Contributor on the `learners` container only |
| Budgets | `budget-demo` ($10, this group) and `budget-monthly-credit` ($150, the whole subscription), emailing `ALERT_EMAIL` |

The model is not in this group. The app calls a deployment on your existing Azure AI Foundry resource (`docs/setup.md`, "Optional: the AI Tutor"), set up by the two commands below.

## The two commands outside Bicep

These touch the Foundry resource's own resource group, which azd must never manage: `azd down` deletes whole resource groups. They are the only part of the demo not created from code. Run them once, after the first `azd up` (the second needs the identity it creates).

1. **The demo's model deployment:** the same model as `btl tutor-ping` uses, with its own small token cap of 10,000 tokens a minute. Past the cap Azure answers 429, which the app treats like any model failure: the template words it.
   ```sh
   az cognitiveservices account deployment create --subscription <subscription-id> \
     --resource-group <foundry-resource-group> --name <foundry-resource> \
     --deployment-name gpt-5.4-nano-demo --model-name gpt-5.4-nano --model-version 2026-03-17 \
     --model-format OpenAI --sku-name GlobalStandard --sku-capacity 10
   ```
2. **The app's role on the Foundry resource.** "Cognitive Services OpenAI User" is a data-plane role: it allows calling the resource's deployments and nothing else, not changing them or reading keys. Azure can't scope it to one deployment; the app's configuration names only the demo's. The principal id is the identity's, from `azd env get-value AZURE_IDENTITY_PRINCIPAL_ID`. A new role takes a few minutes to work; until then the template words everything.
   ```sh
   az role assignment create --subscription <subscription-id> \
     --role "Cognitive Services OpenAI User" \
     --assignee-object-id <identity-principal-id> --assignee-principal-type ServicePrincipal \
     --scope "$(az cognitiveservices account show --subscription <subscription-id> \
       --resource-group <foundry-resource-group> --name <foundry-resource> --query id -o tsv)"
   ```

Then tell the app to use the model, and deploy:
```sh
azd env set TUTOR foundry
azd env set FOUNDRY_ENDPOINT https://<foundry-resource>.openai.azure.com/
azd env set FOUNDRY_DEPLOYMENT gpt-5.4-nano-demo
azd provision --preview
azd up
```

## Learner records

Each viewer is a blob, `<viewer id>.json`, in the `learners` container, holding the same document `btl learn` writes to a file. Azure checks every write against the version the app read (the blob's ETag), so two revisions of the app, as during a deploy, can never overwrite each other. Records survive restarts, scaling to zero and deploys.

To look at them, signed in as yourself (your role is on the container; there is no key to use):
```sh
az storage blob list --subscription <subscription-id> --account-name <storage-account> \
  --container-name learners --auth-mode login -o table
```
In the portal, open the storage account, then **Containers → learners**; it signs in with Entra ID by default.

## The model's limits

A wording is one question or one feedback: at most two model calls (the first try and one repair). Words already in the server's cache are free and not counted.

| Limit | Default | Past it |
|---|---|---|
| Per viewer, per UTC day | 60 wordings (`BTL_WORDINGS_PER_VIEWER`) | That viewer's feedback says "template (daily limit)" |
| Everyone, per UTC day | 1,000 wordings, at most 2,000 calls, about $0.50 (`BTL_WORDINGS_PER_DAY`) | Everyone gets the template's words |
| The deployment | 10,000 tokens a minute | Azure answers 429; the template words it |

The counts are in memory and start again when the app restarts; the deployment's cap holds regardless. Bicep sets the two variables from `wordingsPerViewer` and `wordingsPerDay` in `infra/main.bicep`.

## Costs

| | Idle | In use |
|---|---|---|
| Container Registry (Basic) | about $5 a month | |
| Container app at minimum 0 | $0 | inside the monthly free grant |
| Container app at minimum 1 | about $8–12 a month | |
| Log Analytics | $0 (the daily cap keeps it inside the free 5 GB a month) | |
| Storage account | under a cent a month | fractions of a cent per session |
| The model | $0 | about 1–2¢ per three-match session; at most about $0.50 a day |

The subscription's spending limit is the hard stop; the budgets only email.

## Taking it down

`azd down --purge` deletes the resource group and everything in it, and a hook resets `SERVICE_WEB_RESOURCE_EXISTS`. The subscription budget stays, on purpose. Then remove the two pieces outside Bicep:
```sh
az role assignment delete --subscription <subscription-id> \
  --assignee <identity-principal-id> --role "Cognitive Services OpenAI User" \
  --scope <foundry-resource-id>
az cognitiveservices account deployment delete --subscription <subscription-id> \
  --resource-group <foundry-resource-group> --name <foundry-resource> --deployment-name gpt-5.4-nano-demo
```
