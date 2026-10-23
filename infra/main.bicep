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

// Outputs land in the azd environment (.azure/<env>/.env), where later commands and the docs' queries read them.
output AZURE_LOCATION string = location
output AZURE_RESOURCE_GROUP string = group.name
output AZURE_CONTAINER_APPS_ENVIRONMENT_ID string = environment.outputs.environmentId
output AZURE_LOG_ANALYTICS_WORKSPACE_ID string = environment.outputs.workspaceId
output AZURE_LOG_ANALYTICS_CUSTOMER_ID string = environment.outputs.workspaceCustomerId
