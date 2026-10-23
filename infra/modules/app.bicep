// The container app: the one container that serves the page, the API and the learning engine, on a public HTTPS
// address. Consumption pricing: billed per second while a replica runs, free inside the monthly grant, and nothing
// at all while scaled to zero.

@description('Where the app lives.')
param location string

@description('Tags for every resource, so azd can find what it deployed.')
param tags object

@description('The app\'s name.')
param name string

@description('The Container Apps environment it runs in.')
param environmentId string

@description('The user-assigned identity it runs as.')
param identityId string

@description('That identity\'s client id, which tells the app\'s code which identity to sign in as.')
param identityClientId string

@description('The registry it pulls its image from, e.g. crxxxx.azurecr.io.')
param registryServer string

@description('Whether the app has been deployed before; if so its current image is kept.')
param exists bool

@minValue(0)
@maxValue(1)
@description('0: scale to zero when idle (free, but the first visitor waits about 30 s). 1: always warm.')
param minReplicas int

@allowed(['template', 'foundry'])
@description('Who words questions and feedback: the template, or the model through the Verifier.')
param tutor string

@description('The Foundry resource\'s endpoint and the demo deployment\'s name; used when tutor is foundry.')
param foundryEndpoint string
param foundryDeployment string

@description('Model wordings per viewer a day, and for everyone; past either, the template words it.')
param wordingsPerViewer int
param wordingsPerDay int

@description('Where learners are kept: the storage account\'s blob endpoint, and the container.')
param blobEndpoint string
param blobContainer string

module image 'app-image.bicep' = {
  name: '${name}-image'
  params: {
    exists: exists
    name: name
  }
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  // azd deploys the "web" service to the resource with this tag.
  tags: union(tags, { 'azd-service-name': 'web' })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    environmentId: environmentId
    workloadProfileName: 'Consumption'
    configuration: {
      // One revision at a time: a deploy replaces the old version rather than splitting traffic with it.
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        // HTTP is redirected to HTTPS.
        allowInsecure: false
      }
      // Pull from the registry signed in as the identity, which holds AcrPull: no registry password.
      registries: [
        {
          server: registryServer
          identity: identityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'web'
          image: image.outputs.image
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          // The app's configuration, read by `btl serve` (docs/setup.md). None of it is secret.
          env: [
            { name: 'AZURE_CLIENT_ID', value: identityClientId }
            { name: 'BTL_STORE', value: 'blob' }
            { name: 'BTL_BLOB_ACCOUNT_URL', value: blobEndpoint }
            { name: 'BTL_BLOB_CONTAINER', value: blobContainer }
            { name: 'BTL_TUTOR', value: tutor }
            { name: 'BTL_FOUNDRY_ENDPOINT', value: foundryEndpoint }
            { name: 'BTL_FOUNDRY_DEPLOYMENT', value: foundryDeployment }
            { name: 'BTL_WORDINGS_PER_VIEWER', value: string(wordingsPerViewer) }
            { name: 'BTL_WORDINGS_PER_DAY', value: string(wordingsPerDay) }
          ]
          // In the order Azure stores them, so a preview doesn't report the list as changed.
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/api/health', port: 8000 }
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: { path: '/api/health', port: 8000 }
              periodSeconds: 10
            }
            // Up to 30 s to start; it answers in about 2 s, since the threat model is in the image.
            {
              type: 'Startup'
              httpGet: { path: '/api/health', port: 8000 }
              periodSeconds: 2
              failureThreshold: 15
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        // One replica at most: the caches and limits live in memory, and are correct only with one.
        maxReplicas: 1
      }
    }
  }
}

output uri string = 'https://${app.properties.configuration.ingress.fqdn}'
