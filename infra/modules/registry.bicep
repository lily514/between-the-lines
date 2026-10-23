// The Container Registry that holds the app's image. azd builds the image here (a remote build) and the app pulls
// it, signed in as its identity. Basic is the cheapest tier, about $5 a month, and the demo's only fixed cost.

@description('Where the registry lives.')
param location string

@description('Tags for every resource, so azd can find what it deployed.')
param tags object

@description('The registry\'s name: letters and digits only, unique across Azure.')
param name string

@description('Who may pull images: the app identity\'s principal id.')
param pullPrincipalId string

// Built-in role ids are the same in every tenant (`az role definition list --name AcrPull`).
var acrPullRole = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    // No shared admin password: pulls and pushes sign in with Entra ID.
    adminUserEnabled: false
  }
}

// Lets the app identity pull images from this registry, and nothing else.
resource pull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  // A role assignment's name must be a GUID; guid() makes the same one every run, so redeploying doesn't add more.
  name: guid(registry.id, pullPrincipalId, acrPullRole)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRole)
    principalId: pullPrincipalId
    // Says up front that this is an app's identity, so Azure doesn't wait to look it up in the directory.
    principalType: 'ServicePrincipal'
  }
}

output loginServer string = registry.properties.loginServer
