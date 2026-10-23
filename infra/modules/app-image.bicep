// Which image the app should run after this deployment. `azd deploy` sets the real image, but `azd provision`
// redeploys the app from Bicep, which would put the placeholder back. So when the app already exists, its current
// image is kept. (azd's usual pattern; it tells us whether the app exists through SERVICE_WEB_RESOURCE_EXISTS.)

@description('Whether the app has been deployed before.')
param exists bool

@description('The app\'s name.')
param name string

// A small public sample that stands in until azd builds and deploys the real image.
var placeholder = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

resource existingApp 'Microsoft.App/containerApps@2024-03-01' existing = if (exists) {
  name: name
}

output image string = exists ? existingApp!.properties.template.containers[0].image : placeholder
