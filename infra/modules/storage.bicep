// Where learners' records live: one private container of blobs, one JSON blob per viewer. Records survive restarts,
// scale to zero and deploys, and every revision of the app sees the same ones. Less than a cent a month.
// No keys: shared-key access is off, so the only way in is Microsoft Entra ID with a data role.

@description('Where the account lives.')
param location string

@description('Tags for every resource, so azd can find what it deployed.')
param tags object

@description('The storage account\'s name: 3 to 24 lower-case letters and digits, unique across Azure.')
param name string

@description('The app identity\'s principal id: it reads and writes learners.')
param appPrincipalId string

@description('The developer\'s principal id (azd sets AZURE_PRINCIPAL_ID), to look at records in the portal; empty for none.')
param userPrincipalId string

// Built-in role ids are the same in every tenant (`az role definition list --name "Storage Blob Data Contributor"`).
var blobDataContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource account 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: name
  location: location
  tags: tags
  kind: 'StorageV2'
  // Standard, with three copies in one datacentre: the cheapest kind, and plenty for a demo's records.
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    // No account keys or SAS tokens signed with them: every request signs in with Entra ID.
    allowSharedKeyAccess: false
    // The portal uses Entra ID too, rather than asking for a key it can't use.
    defaultToOAuthAuthentication: true
    // Nothing is ever readable anonymously.
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blobs 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: account
  name: 'default'
}

resource learners 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobs
  name: 'learners'
  properties: {
    publicAccess: 'None'
  }
}

// The app reads and writes blobs in this one container, and nothing else in the account.
resource appReadsAndWrites 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(learners.id, appPrincipalId, blobDataContributor)
  scope: learners
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobDataContributor)
    principalId: appPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// So the developer can browse the records in the portal; being Owner isn't enough to read a blob.
resource developerReadsAndWrites 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(userPrincipalId)) {
  name: guid(learners.id, userPrincipalId, blobDataContributor)
  scope: learners
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobDataContributor)
    principalId: userPrincipalId
    principalType: 'User'
  }
}

output blobEndpoint string = account.properties.primaryEndpoints.blob
output containerName string = learners.name
