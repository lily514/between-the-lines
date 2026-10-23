// The public demo's infrastructure: one resource group holding everything azd creates.
// `azd provision` deploys this file; azd fills the parameters from its environment (main.parameters.json).
targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('The azd environment name, e.g. btl-demo. It names the resource group and goes into every name.')
param environmentName string

// Only eastus2, where the Foundry resource and its quota are; a typo can't put the demo somewhere else.
@allowed(['eastus2'])
@description('Where every resource lives.')
param location string

@description('Who gets the budget alerts. Kept in the azd environment (ALERT_EMAIL), never in the repo.')
param alertEmail string

@minValue(0)
@maxValue(1)
@description('The app\'s minimum replicas: 0 normally (free when idle), 1 while judges are likely to visit.')
param minReplicas int = 0

@description('Whether the app has been deployed before; azure.yaml\'s hooks keep SERVICE_WEB_RESOURCE_EXISTS.')
param webExists bool = false

@allowed(['template', 'foundry'])
@description('Who words questions and feedback (azd env TUTOR): the template, or the model.')
param tutor string = 'template'

// The model lives on Lily's existing Foundry resource, outside this deployment (docs/deployment.md). Its real
// endpoint is kept in the azd environment, never in the repo.
@description('The Foundry resource\'s endpoint (azd env FOUNDRY_ENDPOINT).')
param foundryEndpoint string = ''

@description('The demo\'s model deployment (azd env FOUNDRY_DEPLOYMENT).')
param foundryDeployment string = ''

@description('Model wordings per viewer a day, then the template\'s. A wording is at most two model calls.')
param wordingsPerViewer int = 60

@description('Model wordings a day for everyone, then the template\'s: at most 2,000 calls, about $0.50.')
param wordingsPerDay int = 1000

@description('Who runs azd (azd sets AZURE_PRINCIPAL_ID): given a data role to browse learners in the portal.')
param principalId string = ''

// The budgets' first month. Fixed, so a provision in a later month doesn't try to move it.
var budgetStart = '2026-10-01'

// azd finds what it deployed by this tag.
var tags = { 'azd-env-name': environmentName }
// The same for the same subscription, environment and region, so names stay put between runs and never clash
// with another deployment's.
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

resource group 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

module environment 'modules/environment.bicep' = {
  name: 'environment'
  scope: group
  params: {
    location: location
    tags: tags
    workspaceName: 'log-${resourceToken}'
    environmentName: 'cae-${resourceToken}'
  }
}

module identity 'modules/identity.bicep' = {
  name: 'identity'
  scope: group
  params: {
    location: location
    tags: tags
    name: 'id-${resourceToken}'
  }
}

module registry 'modules/registry.bicep' = {
  name: 'registry'
  scope: group
  params: {
    location: location
    tags: tags
    // Registry names allow letters and digits only.
    name: 'cr${resourceToken}'
    pullPrincipalId: identity.outputs.principalId
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  scope: group
  params: {
    location: location
    tags: tags
    // Storage account names allow lower-case letters and digits only.
    name: 'st${resourceToken}'
    appPrincipalId: identity.outputs.principalId
    userPrincipalId: principalId
  }
}

module app 'modules/app.bicep' = {
  name: 'app'
  scope: group
  params: {
    location: location
    tags: tags
    name: 'ca-web-${resourceToken}'
    environmentId: environment.outputs.environmentId
    identityId: identity.outputs.id
    identityClientId: identity.outputs.clientId
    registryServer: registry.outputs.loginServer
    exists: webExists
    minReplicas: minReplicas
    tutor: tutor
    foundryEndpoint: foundryEndpoint
    foundryDeployment: foundryDeployment
    wordingsPerViewer: wordingsPerViewer
    wordingsPerDay: wordingsPerDay
    blobEndpoint: storage.outputs.blobEndpoint
    blobContainer: storage.outputs.containerName
  }
}

// The demo's own budget, deleted with its resource group by `azd down`.
module demoBudget 'modules/budget.bicep' = {
  name: 'demo-budget'
  scope: group
  params: {
    name: 'budget-demo'
    amount: 10
    startDate: budgetStart
    alertEmail: alertEmail
  }
}

// The whole subscription against its $150 monthly credit, including Lily's own Foundry use. It sits at subscription
// scope, so `azd down` leaves it in place, on purpose.
resource creditBudget 'Microsoft.Consumption/budgets@2023-11-01' = {
  name: 'budget-monthly-credit'
  properties: {
    category: 'Cost'
    amount: 150
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: budgetStart
    }
    notifications: {
      half: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 50
        thresholdType: 'Actual'
        contactEmails: [alertEmail]
      }
      mostOf: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        thresholdType: 'Actual'
        contactEmails: [alertEmail]
      }
      all: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        thresholdType: 'Actual'
        contactEmails: [alertEmail]
      }
      // Warns before the money is spent: the month's spending so far, projected to its end.
      allForecast: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        thresholdType: 'Forecasted'
        contactEmails: [alertEmail]
      }
    }
  }
}

// Outputs land in the azd environment (.azure/<env>/.env), where later commands and the docs' queries read them.
output AZURE_LOCATION string = location
output AZURE_RESOURCE_GROUP string = group.name
output AZURE_CONTAINER_APPS_ENVIRONMENT_ID string = environment.outputs.environmentId
output AZURE_LOG_ANALYTICS_WORKSPACE_ID string = environment.outputs.workspaceId
output AZURE_LOG_ANALYTICS_CUSTOMER_ID string = environment.outputs.workspaceCustomerId
// azd pushes the image to this registry.
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = registry.outputs.loginServer
// T6's `az` command grants the model role to this principal.
output AZURE_IDENTITY_PRINCIPAL_ID string = identity.outputs.principalId
output WEB_URL string = app.outputs.uri
