// =====================================================================
// Mirror UAMI data-plane role assignments onto an App Service's SAMI.
// =====================================================================
//
// In tenants where Azure Policy force-enables a system-assigned managed
// identity (SAMI) on every App Service, having both SAMI and UAMI
// attached confuses ``DefaultAzureCredential`` / ``ManagedIdentityCredential``
// when ``AZURE_CLIENT_ID`` isn't set on every call path. Any code path
// that picks the SAMI then fails with 401/403 against data-plane
// services because only the UAMI was granted permissions.
//
// This module redundantly grants the supplied SAMI principalId the same
// set of data-plane roles its sibling UAMI has on the same target
// services. The assignments are idempotent (deterministic GUIDs).
//
// All ``*RoleIds`` parameters default to empty arrays, so a caller only
// passes the resource it actually needs to mirror against.
//
// Wrapping these in a module (rather than declaring the role assignments
// inline in main.bicep) is required so the runtime ``principalId`` can
// be used in the ``guid(...)`` name expression: ARM requires role
// assignment names to be calculable at the start of their containing
// deployment, and a module's parameters are resolved at the start of
// the module's deployment.
//
// =====================================================================

@description('Required. Principal ID (objectId) of the App Service system-assigned managed identity.')
param principalId string

@description('Required. Name of the target App Service. Used only to disambiguate deployment names.')
param appServiceName string

@description('Optional. Name of the AI Foundry / Cognitive Services account to grant roles on.')
param aiFoundryAccountName string = ''

@description('Optional. Role definition IDs (GUIDs) to grant on the AI Foundry account.')
param aiFoundryRoleIds array = []

@description('Optional. Name of the AI Foundry Content Understanding account to grant roles on.')
param aiFoundryCuAccountName string = ''

@description('Optional. Role definition IDs (GUIDs) to grant on the AI Foundry CU account.')
param aiFoundryCuRoleIds array = []

@description('Optional. Name of the Azure AI Search service to grant roles on.')
param searchServiceName string = ''

@description('Optional. Role definition IDs (GUIDs) to grant on the search service.')
param searchRoleIds array = []

@description('Optional. Name of the Storage account to grant roles on.')
param storageAccountName string = ''

@description('Optional. Role definition IDs (GUIDs) to grant on the storage account.')
param storageRoleIds array = []

@description('Optional. Name of the Cosmos DB account to grant the built-in Cosmos DB Data Contributor data-plane role on.')
param cosmosAccountName string = ''

@description('Optional. Cosmos DB data-plane role definition GUIDs (relative). Defaults to the built-in Data Contributor.')
param cosmosRoleIds array = []

// --- AI Foundry account ---
resource aiFoundryAccount 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' existing = if (!empty(aiFoundryAccountName)) {
  name: aiFoundryAccountName
}

resource aiFoundryAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for roleId in aiFoundryRoleIds: if (!empty(aiFoundryAccountName)) {
    scope: aiFoundryAccount
    name: guid('sami-mirror', appServiceName, aiFoundryAccountName, principalId, roleId)
    properties: {
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleId)
      principalId: principalId
      principalType: 'ServicePrincipal'
    }
  }
]

// --- AI Foundry Content Understanding account ---
resource aiFoundryCuAccount 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' existing = if (!empty(aiFoundryCuAccountName)) {
  name: aiFoundryCuAccountName
}

resource aiFoundryCuAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for roleId in aiFoundryCuRoleIds: if (!empty(aiFoundryCuAccountName)) {
    scope: aiFoundryCuAccount
    name: guid('sami-mirror', appServiceName, aiFoundryCuAccountName, principalId, roleId)
    properties: {
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleId)
      principalId: principalId
      principalType: 'ServicePrincipal'
    }
  }
]

// --- Azure AI Search service ---
resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' existing = if (!empty(searchServiceName)) {
  name: searchServiceName
}

resource searchAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for roleId in searchRoleIds: if (!empty(searchServiceName)) {
    scope: searchService
    name: guid('sami-mirror', appServiceName, searchServiceName, principalId, roleId)
    properties: {
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleId)
      principalId: principalId
      principalType: 'ServicePrincipal'
    }
  }
]

// --- Storage account ---
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = if (!empty(storageAccountName)) {
  name: storageAccountName
}

resource storageAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for roleId in storageRoleIds: if (!empty(storageAccountName)) {
    scope: storageAccount
    name: guid('sami-mirror', appServiceName, storageAccountName, principalId, roleId)
    properties: {
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleId)
      principalId: principalId
      principalType: 'ServicePrincipal'
    }
  }
]

// --- Cosmos DB account (data-plane assignment, not Azure RBAC) ---
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = if (!empty(cosmosAccountName)) {
  name: cosmosAccountName
}

resource cosmosAssignments 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = [
  for roleId in cosmosRoleIds: if (!empty(cosmosAccountName)) {
    parent: cosmosAccount
    name: guid('sami-mirror', appServiceName, cosmosAccountName, principalId, roleId)
    properties: {
      principalId: principalId
      roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/${roleId}'
      scope: cosmosAccount.id
    }
  }
]
