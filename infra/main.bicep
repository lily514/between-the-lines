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

@description('Whether the app has been deployed before; azd sets SERVICE_WEB_RESOURCE_EXISTS.')
param webExists bool = false

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
