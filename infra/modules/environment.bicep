// Log Analytics and the Container Apps environment: where the app runs, and where its logs go.

@description('Where both resources live; main.bicep passes its own location.')
param location string

@description('Tags for every resource, so azd can find what it deployed.')
param tags object

@description('The Log Analytics workspace\'s name.')
param workspaceName string

@description('The Container Apps environment\'s name.')
param environmentName string

// Where the environment's logs land, queried with KQL. Pay per GB ingested; the first 5 GB a month are free.
resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    // Up to 31 days is free; 30 is the shortest allowed.
    retentionInDays: 30
    // About 4.5 GB a month, inside the free 5 GB. If the cap is hit, logs stop until midnight UTC; the app doesn't.
    workspaceCapping: {
      dailyQuotaGb: json('0.15')
    }
    features: {
      // Logs arrive only through Azure Monitor, signed in with Entra ID; the workspace's shared keys don't work.
      disableLocalAuth: true
    }
  }
}

// The boundary the app runs in: its network, its shared ingress, and where its logs go. It costs nothing
// itself; the app inside is what's billed.
resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  tags: tags
  properties: {
    // Logs go to Azure Monitor; the diagnostic setting below sends them on to the workspace, with no key.
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
    // Billed per second while running, and scales to zero. The other profiles are dedicated machines, billed always.
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    zoneRedundant: false
  }
}

// Sends every log the environment makes to the workspace: the app's console output and the platform's own events.
resource environmentLogs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'logs-to-workspace'
  scope: environment
  properties: {
    workspaceId: workspace.id
    logs: [
      {
        categoryGroup: 'allLogs'
        enabled: true
      }
    ]
  }
}

output environmentId string = environment.id
output workspaceId string = workspace.id
output workspaceCustomerId string = workspace.properties.customerId
