// The app's identity in Microsoft Entra ID. It exists before the app, so every role it needs can be granted
// before the app first starts; the app signs in as it, and no key or password exists anywhere.

@description('Where the identity lives.')
param location string

@description('Tags for every resource, so azd can find what it deployed.')
param tags object

@description('The identity\'s name.')
param name string

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: name
  location: location
  tags: tags
}

// The resource id attaches the identity to the app; the principal id is who roles are granted to; the client id
// tells the app's code which identity to sign in as.
output id string = identity.id
output principalId string = identity.properties.principalId
output clientId string = identity.properties.clientId
