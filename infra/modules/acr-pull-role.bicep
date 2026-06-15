// Grants AcrPull on an existing Azure Container Registry (in the same
// resource group) to the supplied principal. Used by main.bicep to let
// App Service managed identities pull images from a private ACR.

@description('Required. Name of the existing Azure Container Registry.')
param acrName string

@description('Required. Principal ID (objectId) of the identity to grant AcrPull to.')
param principalId string

@description('Optional. Principal type for the role assignment.')
@allowed([ 'ServicePrincipal', 'User', 'Group', 'Device', 'ForeignGroup' ])
param principalType string = 'ServicePrincipal'

// AcrPull built-in role definition ID
var acrPullRoleDefinitionId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, principalId, acrPullRoleDefinitionId)
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleDefinitionId)
  }
}

@description('The resource ID of the role assignment.')
output roleAssignmentId string = roleAssignment.id
