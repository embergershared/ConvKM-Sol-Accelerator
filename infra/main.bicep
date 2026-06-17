// ========== main.bicep ========== //
targetScope = 'resourceGroup'

@minLength(3)
@maxLength(16)
@description('Optional. A unique prefix for all resources in this deployment. This should be 3-20 characters long.')
param solutionName string = 'kmgen'

@metadata({ azd: { type: 'location' } })
@description('Required. Azure region for all services. Regions are restricted to guarantee compatibility with paired regions and replica locations for data redundancy and failover scenarios based on articles [Azure regions list](https://learn.microsoft.com/azure/reliability/regions-list) and [Azure Database for MySQL Flexible Server - Azure Regions](https://learn.microsoft.com/azure/mysql/flexible-server/overview#azure-regions).')
@allowed([
  'australiaeast'
  'centralus'
  'eastasia'
  'eastus2'
  'japaneast'
  'northeurope'
  'southeastasia'
  'uksouth'
  'swedencentral'
])
param location string

@allowed([
  'australiaeast'
  'eastus'
  'eastus2'
  'francecentral'
  'japaneast'
  'swedencentral'
  'uksouth'
  'westus'
  'westus3'
])
@metadata({
  azd: {
    type: 'location'
    usageName: [
      'OpenAI.GlobalStandard.gpt-4o-mini,150'
      'OpenAI.GlobalStandard.text-embedding-3-small,80'
    ]
  }
})
@description('Required. Location for AI Foundry deployment. This is the location where the AI Foundry resources will be deployed.')
param aiServiceLocation string

@minLength(1)
@description('Required. Industry use case for deployment.')
@allowed([
  'telecom'
  'IT_helpdesk'
])
param usecase string

@minLength(1)
@description('Optional. Location for the Content Understanding service deployment.')
@allowed(['swedencentral', 'australiaeast'])
@metadata({
  azd: {
    type: 'location'
  }
})
param contentUnderstandingLocation string = 'swedencentral'

@minLength(1)
@description('Optional. Secondary location for databases creation (example: eastus2).')
param secondaryLocation string = 'eastus2'

@minLength(1)
@description('Optional. GPT model deployment type.')
@allowed([
  'Standard'
  'GlobalStandard'
])
param deploymentType string = 'GlobalStandard'

@description('Optional. Name of the GPT model to deploy.')
param gptModelName string = 'gpt-4o-mini'

@description('Optional. Version of the GPT model to deploy.')
param gptModelVersion string = '2024-07-18'

@description('Optional. Version of AI Agent API.')
param azureAiAgentApiVersion string = '2025-05-01'

@description('Optional. Name of the Conversation Agent in Foundry. Defaults to KM-ConversationAgent-{solutionName}.')
param agentNameConversation string = ''

@description('Optional. Name of the Title Agent in Foundry. Defaults to KM-TitleAgent-{solutionName}.')
param agentNameTitle string = ''

@description('Optional. Comma-separated list of model publishers allowed in the model selector dropdown. Defaults to OpenAI,Microsoft,xAI,DeepSeek,Meta.')
param modelFilterAllowedPublishers string = 'OpenAI,Microsoft,xAI,DeepSeek,Meta'

@description('Optional. Whether to filter out model deployments that do not advertise function-calling support. Defaults to true.')
param modelFilterRequireFunctionCalling string = 'true'

@description('Optional. Version of Content Understanding API.')
param azureContentUnderstandingApiVersion string = '2024-12-01-preview'

// You can increase this, but capacity is limited per model/region, so you will get errors if you go over
// https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-limits
@minValue(10)
@description('Optional. Capacity of the GPT deployment.')
param gptDeploymentCapacity int = 150

@minLength(1)
@description('Optional. Name of the Text Embedding model to deploy.')
@allowed([
  'text-embedding-3-small'
])
param embeddingModel string = 'text-embedding-3-small'

@minValue(10)
@description('Optional. Capacity of the Embedding Model deployment.')
param embeddingDeploymentCapacity int = 80

@description('Optional. The Container Registry hostname where the docker images for the backend are located.')
param backendContainerRegistryHostname string = 'kmcontainerreg.azurecr.io'

@description('Optional. The Container Image Name to deploy on the backend.')
param backendContainerImageName string = 'km-api'

@description('Optional. The Container Image Tag to deploy on the backend.')
param backendContainerImageTag string = 'latest_afv2_2026-03-10_1326'

@description('Optional. The Container Registry hostname where the docker images for the frontend are located.')
param frontendContainerRegistryHostname string = 'kmcontainerreg.azurecr.io'

@description('Optional. The Container Image Name to deploy on the frontend.')
param frontendContainerImageName string = 'km-app'

@description('Optional. The Container Image Tag to deploy on the frontend.')
param frontendContainerImageTag string = 'latest_afv2_2026-03-10_1326'

@description('Optional. When true, configure the API and Frontend WebApps to pull their container images from the registry using their managed identity instead of admin credentials. Required when using a private ACR that does not allow anonymous pulls. Defaults to false to preserve compatibility with the public accelerator registry (kmcontainerreg.azurecr.io).')
param useManagedIdentityForAcrPull bool = false

@description('Optional. Name of the Azure Container Registry (in this resource group) to grant AcrPull on when useManagedIdentityForAcrPull is true. Leave empty to skip role-assignment provisioning (e.g. when the registry lives in a different RG/subscription and AcrPull must be granted out-of-band).')
param containerRegistryNameForAcrPull string = ''


@description('Optional. The tags to apply to all deployed Azure resources.')
param tags resourceInput<'Microsoft.Resources/resourceGroups@2025-04-01'>.tags = {}

// Mandatory tags applied to every resource regardless of caller-supplied tags.
var mandatoryTags = {
  SecurityControl: 'Ignore'
}
var allTags = union(tags, mandatoryTags)

@description('Optional. Enable private networking for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enablePrivateNetworking bool = false

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Optional. Enable monitoring applicable resources, aligned with the Well Architected Framework recommendations. This setting enables Application Insights and Log Analytics and configures all the resources applicable resources to send logs. Defaults to false.')
param enableMonitoring bool = false

@description('Optional. Enable redundancy for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableRedundancy bool = false

@description('Optional. Enable scalability for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableScalability bool = false

@description('Optional. Admin username for the Jumpbox Virtual Machine. Set to custom value if enablePrivateNetworking is true.')
@secure()
param vmAdminUsername string?

@description('Optional. Admin password for the Jumpbox Virtual Machine. Set to custom value if enablePrivateNetworking is true.')
@secure()
param vmAdminPassword string?

@description('Optional. Size of the Jumpbox Virtual Machine when created. Set to custom value if enablePrivateNetworking is true.')
param vmSize string = 'Standard_D2s_v5'

@description('Optional: Existing Log Analytics Workspace Resource ID')
param existingLogAnalyticsWorkspaceId string = ''

@description('Optional. Use this parameter to use an existing AI project resource ID')
param existingAiFoundryAiProjectResourceId string = ''

@description('Optional. Created by user name.')
param createdBy string = contains(deployer(), 'userPrincipalName')? split(deployer().userPrincipalName, '@')[0]: deployer().objectId

@maxLength(5)
@description('Optional. A unique text value for the solution. This is used to ensure resource names are unique for global resources. Defaults to a 5-character substring of the unique string generated from the subscription ID, resource group name, and solution name.')
param solutionUniqueText string = substring(uniqueString(subscription().id, resourceGroup().name, solutionName), 0, 5)

var solutionSuffix = toLower(trim(replace(
  replace(
    replace(replace(replace(replace('${solutionName}${solutionUniqueText}', '-', ''), '_', ''), '.', ''), '/', ''),
    ' ',
    ''
  ),
  '*',
  ''
)))

var acrName = 'kmcontainerreg'
// Replica regions list based on article in [Azure regions list](https://learn.microsoft.com/azure/reliability/regions-list) and [Enhance resilience by replicating your Log Analytics workspace across regions](https://learn.microsoft.com/azure/azure-monitor/logs/workspace-replication#supported-regions) for supported regions for Log Analytics Workspace.
var replicaRegionPairs = {
  australiaeast: 'australiasoutheast'
  centralus: 'westus'
  eastasia: 'japaneast'
  eastus: 'centralus'
  eastus2: 'centralus'
  japaneast: 'eastasia'
  northeurope: 'westeurope'
  southeastasia: 'eastasia'
  uksouth: 'westeurope'
  westeurope: 'northeurope'
  swedencentral: 'northeurope'
}
var replicaLocation = replicaRegionPairs[resourceGroup().location]

// Region pairs list based on article in [Azure Database for MySQL Flexible Server - Azure Regions](https://learn.microsoft.com/azure/mysql/flexible-server/overview#azure-regions) for supported high availability regions for CosmosDB.
var cosmosDbZoneRedundantHaRegionPairs = {
  australiaeast: 'uksouth' //'southeastasia'
  centralus: 'eastus2'
  eastasia: 'southeastasia'
  eastus: 'centralus'
  eastus2: 'centralus'
  japaneast: 'australiaeast'
  northeurope: 'westeurope'
  southeastasia: 'eastasia'
  uksouth: 'westeurope'
  westeurope: 'northeurope'
  swedencentral: 'northeurope'
}
// Paired location calculated based on 'location' parameter. This location will be used by applicable resources if `enableScalability` is set to `true`
var cosmosDbHaLocation = cosmosDbZoneRedundantHaRegionPairs[resourceGroup().location]

// Extracts subscription, resource group, and workspace name from the resource ID when using an existing Log Analytics workspace
var useExistingLogAnalytics = !empty(existingLogAnalyticsWorkspaceId)
var logAnalyticsWorkspaceResourceId = useExistingLogAnalytics
  ? existingLogAnalyticsWorkspaceId
  : logAnalyticsWorkspace!.outputs.resourceId
var existingTags = resourceGroup().tags ?? {}

// ========== Resource Group Tag ========== //
resource resourceGroupTags 'Microsoft.Resources/tags@2025-04-01' = {
  name: 'default'
  properties: {
    tags: union(
      existingTags,
      allTags,
      {
        TemplateName: 'KM-Generic'
        Type: enablePrivateNetworking ? 'WAF' : 'Non-WAF'
        CreatedBy: createdBy
        DeploymentName: deployment().name
        UseCase: usecase
      }
    )
  }
}

#disable-next-line no-deployments-resources
resource avmTelemetry 'Microsoft.Resources/deployments@2024-03-01' = if (enableTelemetry) {
  name: '46d3xbcp.ptn.sa-convknowledgemining.${replace('-..--..-', '.', '-')}.${substring(uniqueString(deployment().name, location), 0, 4)}'
  properties: {
    mode: 'Incremental'
    template: {
      '$schema': 'https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#'
      contentVersion: '1.0.0.0'
      resources: []
      outputs: {
        telemetry: {
          type: 'String'
          value: 'For more information, see https://aka.ms/avm/TelemetryInfo'
        }
      }
    }
  }
}

// ========== Log Analytics Workspace ========== //
// WAF best practices for Log Analytics: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-log-analytics
// WAF PSRules for Log Analytics: https://azure.github.io/PSRule.Rules.Azure/en/rules/resource/#azure-monitor-logs
var logAnalyticsWorkspaceResourceName = 'law-${solutionSuffix}'
module logAnalyticsWorkspace 'br/public:avm/res/operational-insights/workspace:0.14.2' = if (enableMonitoring && !useExistingLogAnalytics) {
  name: take('avm.res.operational-insights.workspace.${logAnalyticsWorkspaceResourceName}', 64)
  params: {
    name: logAnalyticsWorkspaceResourceName
    tags: allTags
    location: location
    enableTelemetry: enableTelemetry
    skuName: 'PerGB2018'
    dataRetention: 365
    features: { enableLogAccessUsingOnlyResourcePermissions: true }
    diagnosticSettings: [{ useThisWorkspace: true }]
    // WAF aligned configuration for Redundancy
    dailyQuotaGb: enableRedundancy ? 10 : null //WAF recommendation: 10 GB per day is a good starting point for most workloads
    replication: enableRedundancy
      ? {
          enabled: true
          location: replicaLocation
        }
      : null
    // WAF aligned configuration for Private Networking
    publicNetworkAccessForIngestion: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    publicNetworkAccessForQuery: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    dataSources: enablePrivateNetworking
      ? [
          {
            tags: allTags
            eventLogName: 'Application'
            eventTypes: [
              {
                eventType: 'Error'
              }
              {
                eventType: 'Warning'
              }
              {
                eventType: 'Information'
              }
            ]
            kind: 'WindowsEvent'
            name: 'applicationEvent'
          }
          {
            counterName: '% Processor Time'
            instanceName: '*'
            intervalSeconds: 60
            kind: 'WindowsPerformanceCounter'
            name: 'windowsPerfCounter1'
            objectName: 'Processor'
          }
          {
            kind: 'IISLogs'
            name: 'sampleIISLog1'
            state: 'OnPremiseEnabled'
          }
        ]
      : null
  }
}

// ========== Application Insights ========== //
// WAF best practices for Application Insights: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/application-insights
// WAF PSRules for  Application Insights: https://azure.github.io/PSRule.Rules.Azure/en/rules/resource/#application-insights
var applicationInsightsResourceName = 'appi-${solutionSuffix}'
module applicationInsights 'br/public:avm/res/insights/component:0.7.1' = if (enableMonitoring) {
  name: take('avm.res.insights.component.${applicationInsightsResourceName}', 64)
  params: {
    name: applicationInsightsResourceName
    tags: allTags
    location: location
    enableTelemetry: enableTelemetry
    retentionInDays: 365
    kind: 'web'
    disableIpMasking: false
    flowType: 'Bluefield'
    // WAF aligned configuration for Monitoring
    workspaceResourceId: enableMonitoring ? logAnalyticsWorkspaceResourceId : ''
  }
}
// ========== Virtual Network and Networking Components ========== //

// Virtual Network with NSGs and Subnets
module virtualNetwork 'modules/virtualNetwork.bicep' = if (enablePrivateNetworking) {
  name: take('module.virtualNetwork.${solutionSuffix}', 64)
  params: {
    name: 'vnet-${solutionSuffix}'
    addressPrefixes: ['10.0.0.0/20'] // 4096 addresses (enough for 8 /23 subnets or 16 /24)
    location: location
    tags: allTags
    logAnalyticsWorkspaceId: logAnalyticsWorkspaceResourceId
    resourceSuffix: solutionSuffix
    enableTelemetry: enableTelemetry
  }
}
// Azure Bastion Host
var bastionHostName = 'bas-${solutionSuffix}'
module bastionHost 'br/public:avm/res/network/bastion-host:0.8.2' = if (enablePrivateNetworking) {
  name: take('avm.res.network.bastion-host.${bastionHostName}', 64)
  params: {
    name: bastionHostName
    skuName: 'Standard'
    location: location
    virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
    diagnosticSettings: [
      {
        name: 'bastionDiagnostics'
        workspaceResourceId: logAnalyticsWorkspaceResourceId
        logCategoriesAndGroups: [
          {
            categoryGroup: 'allLogs'
            enabled: true
          }
        ]
      }
    ]
    tags: allTags
    enableTelemetry: enableTelemetry
    publicIPAddressObject: {
      name: 'pip-${bastionHostName}'
    }
  }
}

// Jumpbox Virtual Machine
var jumpboxVmName = take('vm-jumpbox-${solutionSuffix}', 15)
module jumpboxVM 'br/public:avm/res/compute/virtual-machine:0.21.0' = if (enablePrivateNetworking) {
  name: take('avm.res.compute.virtual-machine.${jumpboxVmName}', 64)
  params: {
    name: take(jumpboxVmName, 15) // Shorten VM name to 15 characters to avoid Azure limits
    vmSize: vmSize ?? 'Standard_D2s_v5'
    location: location
    adminUsername: vmAdminUsername ?? 'JumpboxAdminUser'
    adminPassword: vmAdminPassword ?? 'JumpboxAdminP@ssw0rd1234!'
    tags: allTags
    availabilityZone: -1
    imageReference: {
      publisher: 'microsoft-dsvm'
      offer: 'dsvm-win-2022'
      sku: 'winserver-2022'
      version: 'latest'
    }
    osType: 'Windows'
    osDisk: {
      name: 'osdisk-${jumpboxVmName}'
      managedDisk: {
        storageAccountType: 'Standard_LRS'
      }
    }
    encryptionAtHost: false // Some Azure subscriptions do not support encryption at host
    nicConfigurations: [
      {
        name: 'nic-${jumpboxVmName}'
        ipConfigurations: [
          {
            name: 'ipconfig1'
            subnetResourceId: virtualNetwork!.outputs.jumpboxSubnetResourceId
          }
        ]
        diagnosticSettings: [
          {
            name: 'jumpboxDiagnostics'
            workspaceResourceId: logAnalyticsWorkspaceResourceId
            logCategoriesAndGroups: [
              {
                categoryGroup: 'allLogs'
                enabled: true
              }
            ]
            metricCategories: [
              {
                category: 'AllMetrics'
                enabled: true
              }
            ]
          }
        ]
      }
    ]
    enableTelemetry: enableTelemetry
  }
}

// ========== Private DNS Zones ========== //
var privateDnsZones = [
  'privatelink.cognitiveservices.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.services.ai.azure.com'
  'privatelink.blob.${environment().suffixes.storage}'
  'privatelink.queue.${environment().suffixes.storage}'
  'privatelink.file.${environment().suffixes.storage}'
  'privatelink.dfs.${environment().suffixes.storage}'
  'privatelink.documents.azure.com'
  'privatelink${environment().suffixes.sqlServerHostname}'
  'privatelink.search.windows.net'
  'privatelink.azurewebsites.net'
]

// DNS Zone Index Constants
var dnsZoneIndex = {
  cognitiveServices: 0
  openAI: 1
  aiServices: 2
  storageBlob: 3
  storageQueue: 4
  storageFile: 5
  storageDfs: 6
  cosmosDB: 7
  sqlServer: 8
  search: 9
  webApp: 10
}

// ===================================================
// DEPLOY PRIVATE DNS ZONES
// - Deploys all zones if no existing Foundry project is used
// - Excludes AI-related zones when using with an existing Foundry project
// ===================================================
@batchSize(5)
module avmPrivateDnsZones 'br/public:avm/res/network/private-dns-zone:0.8.0' = [
  for (zone, i) in privateDnsZones: if (enablePrivateNetworking) {
    name: 'avm.res.network.private-dns-zone.${split(zone, '.')[1]}'
    params: {
      name: zone
      tags: allTags
      enableTelemetry: enableTelemetry
      virtualNetworkLinks: [
        {
          name: take('vnetlink-${virtualNetwork!.outputs.name}-${split(zone, '.')[1]}', 80)
          virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
        }
      ]
    }
  }
]

// WAF best practices for identity and access management: https://learn.microsoft.com/en-us/azure/well-architected/security/identity-access

// ========== User Assigned Identity ========== //
var userAssignedIdentityResourceName = 'id-${solutionSuffix}'
module userAssignedIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.3' = {
  name: take('avm.res.managed-identity.user-assigned-identity.${userAssignedIdentityResourceName}', 64)
  params: {
    name: userAssignedIdentityResourceName
    location: location
    tags: allTags
    enableTelemetry: enableTelemetry
  }
}

// ========== SQL Operations User Assigned Identity ========== //
// Dedicated identity for backend SQL operations with limited permissions (db_datareader, db_datawriter)
var backendUserAssignedIdentityResourceName = 'id-backend-${solutionSuffix}'
module backendUserAssignedIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.3' = {
  name: take('avm.res.managed-identity.user-assigned-identity.${backendUserAssignedIdentityResourceName}', 64)
  params: {
    name: backendUserAssignedIdentityResourceName
    location: location
    tags: allTags
    enableTelemetry: enableTelemetry
  }
}

// ========== AVM WAF ========== //
// ==========AI Foundry and related resources ========== //
// ========== AI Foundry: AI Services ========== //
// WAF best practices for Open AI: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-openai

var existingOpenAIEndpoint = !empty(existingAiFoundryAiProjectResourceId) ? format('https://{0}.openai.azure.com/', split(existingAiFoundryAiProjectResourceId, '/')[8]) : ''
var existingProjEndpoint = !empty(existingAiFoundryAiProjectResourceId) ? format('https://{0}.services.ai.azure.com/api/projects/{1}', split(existingAiFoundryAiProjectResourceId, '/')[8], split(existingAiFoundryAiProjectResourceId, '/')[10]) : ''
var existingAIServicesName = !empty(existingAiFoundryAiProjectResourceId) ? split(existingAiFoundryAiProjectResourceId, '/')[8] : ''
var existingAIProjectName = !empty(existingAiFoundryAiProjectResourceId) ? split(existingAiFoundryAiProjectResourceId, '/')[10] : ''

var aiFoundryAiServicesSubscriptionId = useExistingAiFoundryAiProject
  ? split(existingAiFoundryAiProjectResourceId, '/')[2]
  : subscription().id
var useExistingAiFoundryAiProject = !empty(existingAiFoundryAiProjectResourceId)
var aiFoundryAiServicesResourceGroupName = useExistingAiFoundryAiProject
  ? split(existingAiFoundryAiProjectResourceId, '/')[4]
  : 'rg-${solutionSuffix}'
var aiFoundryAiServicesResourceName = useExistingAiFoundryAiProject
  ? split(existingAiFoundryAiProjectResourceId, '/')[8]
  : 'aif-${solutionSuffix}'
var aiFoundryAiProjectResourceName = useExistingAiFoundryAiProject
  ? split(existingAiFoundryAiProjectResourceId, '/')[10]
  : 'proj-${solutionSuffix}' 

// NOTE: Required version 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' not available in AVM
// var aiFoundryAiServicesResourceName = 'aif-${solutionSuffix}'
var aiFoundryAiServicesAiProjectResourceName = 'proj-${solutionSuffix}'
var aiFoundryAIservicesEnabled = true
var aiModelDeployments = [
  {
    name: gptModelName
    format: 'OpenAI'
    model: gptModelName
    sku: {
      name: deploymentType
      capacity: gptDeploymentCapacity
    }
    version: gptModelVersion
    raiPolicyName: 'Microsoft.Default'
  }
  {
    name: embeddingModel
    format: 'OpenAI'
    model: embeddingModel
    sku: {
      name: 'GlobalStandard'
      capacity: embeddingDeploymentCapacity
    }
    version: '1'
    raiPolicyName: 'Microsoft.Default'
  }
]

resource existingAiFoundryAiServices 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = if (useExistingAiFoundryAiProject) {
  name: aiFoundryAiServicesResourceName
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
}

resource existingAiFoundryAiServicesProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' existing = if (useExistingAiFoundryAiProject) {
  name: aiFoundryAiProjectResourceName
  parent: existingAiFoundryAiServices
}

module aiFoundryAiServices 'modules/ai-services.bicep' = if (aiFoundryAIservicesEnabled) {
  name: take('avm.res.cognitive-services.account.${aiFoundryAiServicesResourceName}', 64)
  params: {
    name: aiFoundryAiServicesResourceName
    location: aiServiceLocation
    tags: allTags
    existingFoundryProjectResourceId: existingAiFoundryAiProjectResourceId
    projectName: !empty(existingAIProjectName) ? existingAIProjectName : aiFoundryAiServicesAiProjectResourceName
    projectDescription: 'AI Foundry Project'
    sku: 'S0'
    kind: 'AIServices'
    disableLocalAuth: true
    customSubDomainName: aiFoundryAiServicesResourceName
    apiProperties: {
      //staticsEnabled: false
    }
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
      bypass: 'AzureServices'
    }
    managedIdentities: { userAssignedResourceIds: [userAssignedIdentity!.outputs.resourceId] } //To create accounts or projects, you must enable a managed identity on your resource
    roleAssignments: [
      {
        roleDefinitionIdOrName: '53ca6127-db72-4b80-b1b0-d745d6d5456d' // Azure AI User
        principalId: userAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: '53ca6127-db72-4b80-b1b0-d745d6d5456d' // Azure AI User
        principalId: backendUserAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: '64702f94-c441-49e6-a78b-ef80e0188fee' // Azure AI Developer
        principalId: userAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
        principalId: userAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: '64702f94-c441-49e6-a78b-ef80e0188fee' // Azure AI Developer
        principalId: backendUserAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
        principalId: backendUserAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
    ]
    // WAF aligned configuration for Monitoring
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    privateEndpoints: []
    deployments: [
      for aiModelDeployment in aiModelDeployments: {
        name: aiModelDeployment.name
        model: {
          format: aiModelDeployment.format
          name: aiModelDeployment.model
          version: aiModelDeployment.version
        }
        raiPolicyName: aiModelDeployment.raiPolicyName
        sku: {
          name: aiModelDeployment.sku.name
          capacity: aiModelDeployment.sku.capacity
        }
      }
    ]
  }
}

// ========== AI Foundry Private Endpoint ========== //
module aiFoundryPrivateEndpoint 'br/public:avm/res/network/private-endpoint:0.8.1' = if (enablePrivateNetworking && !useExistingAiFoundryAiProject) {
  name: take('pep-${aiFoundryAiServicesResourceName}-deployment', 64)
  params: {
    name: 'pep-${aiFoundryAiServicesResourceName}'
    customNetworkInterfaceName: 'nic-${aiFoundryAiServicesResourceName}'
    location: location
    tags: allTags
    privateLinkServiceConnections: [
      {
        name: 'pep-${aiFoundryAiServicesResourceName}-connection'
        properties: {
          privateLinkServiceId: aiFoundryAiServices!.outputs.resourceId
          groupIds: ['account']
        }
      }
    ]
    privateDnsZoneGroup: {
      privateDnsZoneGroupConfigs: [
        {
          name: 'ai-services-dns-zone-cognitiveservices'
          privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.cognitiveServices]!.outputs.resourceId
        }
        {
          name: 'ai-services-dns-zone-openai'
          privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.openAI]!.outputs.resourceId
        }
        {
          name: 'ai-services-dns-zone-aiservices'
          privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.aiServices]!.outputs.resourceId
        }
      ]
    }
    subnetResourceId: virtualNetwork!.outputs.pepsSubnetResourceId
  }
}

// AI Foundry: AI Services Content Understanding
var aiFoundryAiServicesCUResourceName = 'aif-${solutionSuffix}-cu'
var aiServicesNameCu = 'aisa-${solutionSuffix}-cu'
module cognitiveServicesCu 'br/public:avm/res/cognitive-services/account:0.14.1' = {
  name: take('avm.res.cognitive-services.account.${aiFoundryAiServicesCUResourceName}', 64)
  params: {
    name: aiServicesNameCu
    location: contentUnderstandingLocation
    tags: allTags
    enableTelemetry: enableTelemetry
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
    sku: 'S0'
    kind: 'AIServices'
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
    }
    managedIdentities: { userAssignedResourceIds: [userAssignedIdentity!.outputs.resourceId] } //To create accounts or projects, you must enable a managed identity on your resource
    disableLocalAuth: true
    customSubDomainName: aiServicesNameCu
    apiProperties: {
      // staticsEnabled: false
    }
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    privateEndpoints: []
    roleAssignments: [
      {
        roleDefinitionIdOrName: '53ca6127-db72-4b80-b1b0-d745d6d5456d' // Azure AI User
        principalId: userAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
    ]
  }
}

// ========== AI Services CU: Separate Private Endpoint ========== //
module cognitiveServicesCuPrivateEndpoint 'br/public:avm/res/network/private-endpoint:0.8.1' = if (enablePrivateNetworking) {
  name: take('pep-${aiFoundryAiServicesCUResourceName}-deployment', 64)
  params: {
    name: 'pep-${aiFoundryAiServicesCUResourceName}'
    customNetworkInterfaceName: 'nic-${aiFoundryAiServicesCUResourceName}'
    location: location
    tags: allTags
    privateLinkServiceConnections: [
      {
        name: 'pep-${aiFoundryAiServicesCUResourceName}-connection'
        properties: {
          privateLinkServiceId: cognitiveServicesCu.outputs.resourceId
          groupIds: ['account']
        }
      }
    ]
    privateDnsZoneGroup: {
      privateDnsZoneGroupConfigs: [
        {
          name: 'ai-services-cu-dns-zone-cognitiveservices'
          privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.cognitiveServices]!.outputs.resourceId
        }
        {
          name: 'ai-services-cu-dns-zone-openai'
          privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.openAI]!.outputs.resourceId
        }
        {
          name: 'ai-services-cu-dns-zone-aiservices'
          privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.aiServices]!.outputs.resourceId
        }
      ]
    }
    subnetResourceId: virtualNetwork!.outputs.pepsSubnetResourceId
  }
}

// ========== AVM WAF ========== //
// ========== AI Foundry: AI Search ========== //
var aiSearchName = 'srch-${solutionSuffix}'
var aiSearchConnectionName = 'foundry-search-connection-${solutionSuffix}'

resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: aiSearchName
  location: location
  sku: {
    name: 'standard'
  }
}

// Separate module for Search Service to enable managed identity and update other properties, as this reduces deployment time
module searchServiceUpdate 'br/public:avm/res/search/search-service:0.12.0' = {
  name: take('avm.res.search.enable-identity.${aiSearchName}', 64)
  params: {
    // Required parameters
    name: aiSearchName
    location: location
    enableTelemetry: enableTelemetry
    diagnosticSettings: enableMonitoring ? [
      {
        workspaceResourceId: logAnalyticsWorkspaceResourceId
      }
    ] : null
    disableLocalAuth: true
    hostingMode: 'Default'
    managedIdentities: {
      systemAssigned: true
    }
    networkRuleSet: {
      bypass: 'AzureServices'
      ipRules: []
    }
    roleAssignments: [
      {
        roleDefinitionIdOrName: '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
        principalId: userAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
        principalId: userAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: '8ebe5a00-799e-43f5-93ac-243d3dce84a7' //'Search Index Data Contributor'
        principalId: userAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
        principalId: userAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
        principalId: backendUserAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: '1407120a-92aa-4202-b7e9-c0e197c71c8f' // Search Index Data Reader
        principalId: !useExistingAiFoundryAiProject ? aiFoundryAiServices.outputs.aiProjectInfo.aiprojectSystemAssignedMIPrincipalId : existingAiFoundryAiServicesProject!.identity.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: '7ca78c08-252a-4471-8644-bb5ff32d4ba0' // Search Service Contributor
        principalId: !useExistingAiFoundryAiProject ? aiFoundryAiServices.outputs.aiProjectInfo.aiprojectSystemAssignedMIPrincipalId : existingAiFoundryAiServicesProject!.identity.principalId
        principalType: 'ServicePrincipal'
      }
    ]
    partitionCount: 1
    replicaCount: 1
    sku: 'standard'
    semanticSearch: 'free'
    // Use the deployment tags provided to the template
    tags: allTags
    publicNetworkAccess: 'Enabled' //enablePrivateNetworking ? 'Disabled' : 'Enabled'
    privateEndpoints: false //enablePrivateNetworking
    ? [
        {
          name: 'pep-${aiSearchName}'
          customNetworkInterfaceName: 'nic-${aiSearchName}'
          privateDnsZoneGroup: {
            privateDnsZoneGroupConfigs: [
              { privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.search]!.outputs.resourceId }
            ]
          }
          service: 'searchService'
          subnetResourceId: virtualNetwork!.outputs.pepsSubnetResourceId
        }
      ]
    : []
  }
  dependsOn: [
    searchService
  ]
}

// ========== Search Service to AI Services Role Assignment ========== //
resource searchServiceToAiServicesRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAiFoundryAiProject) {
  name: guid(aiSearchName, '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd', aiFoundryAiServicesResourceName)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd') // Cognitive Services OpenAI User
    principalId: searchServiceUpdate.outputs.systemAssignedMIPrincipalId!
    principalType: 'ServicePrincipal'
  }
}

resource projectAISearchConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-10-01-preview' = if (!useExistingAiFoundryAiProject) {
  name: '${aiFoundryAiServicesResourceName}/${aiFoundryAiServicesAiProjectResourceName}/${aiSearchConnectionName}'
  properties: {
    category: 'CognitiveSearch'
    target: 'https://${aiSearchName}.search.windows.net'
    authType: 'AAD'
    isSharedToAll: true
    metadata: {
      ApiType: 'Azure'
      ResourceId: searchService.id
      location: searchService.location
    }
  }
  dependsOn: [
    aiFoundryAiServices
  ]
}

module existing_AIProject_SearchConnectionModule 'modules/deploy_aifp_aisearch_connection.bicep' = if (useExistingAiFoundryAiProject) {
  name: 'aiProjectSearchConnectionDeployment'
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  params: {
    existingAIProjectName: aiFoundryAiProjectResourceName
    existingAIFoundryName: aiFoundryAiServicesResourceName
    aiSearchName: aiSearchName
    aiSearchResourceId: searchService.id
    aiSearchLocation: searchService.location
    aiSearchConnectionName: aiSearchConnectionName
  }
}

// Role assignment for existing AI Services scenario
module searchServiceToExistingAiServicesRoleAssignment 'modules/role-assignment.bicep' = if (useExistingAiFoundryAiProject) {
  name: 'searchToExistingAiServices-roleAssignment'
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  params: {
    principalId: searchServiceUpdate.outputs.systemAssignedMIPrincipalId!
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
    targetResourceName: aiFoundryAiServices.outputs.name
  }
}

// ========== Storage account module ========== //
var storageAccountName = 'st${solutionSuffix}'
module storageAccount 'br/public:avm/res/storage/storage-account:0.31.0' = {
  name: take('avm.res.storage.storage-account.${storageAccountName}', 64)
  params: {
    name: storageAccountName
    location: location
    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [ userAssignedIdentity!.outputs.resourceId ]
    }
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'
    enableTelemetry: enableTelemetry
    tags: allTags
    enableHierarchicalNamespace: true
    roleAssignments: [
      {
        principalId: userAssignedIdentity.outputs.principalId
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
        principalType: 'ServicePrincipal'
      }
      {
        principalId: userAssignedIdentity.outputs.principalId
        roleDefinitionIdOrName: 'Storage Account Contributor'
        principalType: 'ServicePrincipal'
      }
      {
        principalId: userAssignedIdentity.outputs.principalId
        roleDefinitionIdOrName: 'Storage File Data Privileged Contributor'
        principalType: 'ServicePrincipal'
      }
      {
        principalId: userAssignedIdentity.outputs.principalId
        roleDefinitionIdOrName: 'Storage Blob Delegator'
        principalType: 'ServicePrincipal'
      }
    ]
    networkAcls: {
      bypass: 'AzureServices, Logging, Metrics'
      defaultAction: enablePrivateNetworking ? 'Deny' : 'Allow'
      virtualNetworkRules: []
    }
    allowSharedKeyAccess: true
    allowBlobPublicAccess: false
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    privateEndpoints: enablePrivateNetworking
      ? [
          {
            name: 'pep-blob-${solutionSuffix}'
            service: 'blob'
            subnetResourceId: virtualNetwork!.outputs.pepsSubnetResourceId
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'storage-dns-zone-group-blob'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.storageBlob]!.outputs.resourceId
                }
              ]
            }
          }
          {
            name: 'pep-queue-${solutionSuffix}'
            service: 'queue'
            subnetResourceId: virtualNetwork!.outputs.pepsSubnetResourceId
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'storage-dns-zone-group-queue'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.storageQueue]!.outputs.resourceId
                }
              ]
            }
          }
          {
            name: 'pep-file-${solutionSuffix}'
            service: 'file'
            subnetResourceId: virtualNetwork!.outputs.pepsSubnetResourceId
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'storage-dns-zone-group-file'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.storageFile]!.outputs.resourceId
                }
              ]
            }
          }
          {
            name: 'pep-dfs-${solutionSuffix}'
            service: 'dfs'
            subnetResourceId: virtualNetwork!.outputs.pepsSubnetResourceId
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'storage-dns-zone-group-dfs'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.storageDfs]!.outputs.resourceId
                }
              ]
            }
          }
        ]
      : []
    blobServices: {
      corsRules: [
        {
          allowedOrigins: [
            'https://app-${solutionSuffix}.azurewebsites.net'
          ]
          allowedMethods: [ 'GET', 'HEAD', 'OPTIONS' ]
          allowedHeaders: [ '*' ]
          exposedHeaders: [ 'Content-Length', 'Content-Type' ]
          maxAgeInSeconds: 3600
        }
      ]
      deleteRetentionPolicyEnabled: false
      changeFeedEnabled: false
      restorePolicyEnabled: false
      isVersioningEnabled: false
      containerDeleteRetentionPolicyEnabled: false
      lastAccessTimeTrackingPolicyEnabled: false
      containers: [
        {
          name: 'data'
        }
      ]
    }
  }
}

//========== Cosmos DB module ========== //
var cosmosDbResourceName = 'cosmos-${solutionSuffix}'
var cosmosDbDatabaseName = 'db_conversation_history'
var collectionName = 'conversations'
module cosmosDb 'br/public:avm/res/document-db/database-account:0.18.0' = {
  name: take('avm.res.document-db.database-account.${cosmosDbResourceName}', 64)
  params: {
    // Required parameters
    name: cosmosDbResourceName
    location: location
    tags: allTags
    enableTelemetry: enableTelemetry
    sqlDatabases: [
      {
        name: cosmosDbDatabaseName
        containers: [
          {
            name: collectionName
            paths: [
              '/userId'
            ]
          }
        ]
      }
    ]
    sqlRoleDefinitions: [
      {
        // Cosmos DB Built-in Data Contributor: https://docs.azure.cn/en-us/cosmos-db/nosql/security/reference-data-plane-roles#cosmos-db-built-in-data-contributor
        roleName: 'Cosmos DB SQL Data Contributor'
        dataActions: [
          'Microsoft.DocumentDB/databaseAccounts/readMetadata'
          'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/*'
          'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*'
        ]
        assignments: [{ principalId: backendUserAssignedIdentity.outputs.principalId }]
      }
    ]
    // WAF aligned configuration for Monitoring
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
    // WAF aligned configuration for Private Networking
    networkRestrictions: {
      networkAclBypass: 'None'
      publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    }
    privateEndpoints: enablePrivateNetworking
      ? [
          {
            name: 'pep-${cosmosDbResourceName}'
            customNetworkInterfaceName: 'nic-${cosmosDbResourceName}'
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                { privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.cosmosDB]!.outputs.resourceId }
              ]
            }
            service: 'Sql'
            subnetResourceId: virtualNetwork!.outputs.pepsSubnetResourceId
          }
        ]
      : []
    // WAF aligned configuration for Redundancy
    zoneRedundant: enableRedundancy
    capabilitiesToAdd: enableRedundancy ? null : ['EnableServerless']
    enableAutomaticFailover: enableRedundancy
    failoverLocations: enableRedundancy
      ? [
          {
            failoverPriority: 0
            isZoneRedundant: true
            locationName: location
          }
          {
            failoverPriority: 1
            isZoneRedundant: true
            locationName: cosmosDbHaLocation
          }
        ]
      : [
          {
            locationName: location
            failoverPriority: 0
            isZoneRedundant: false
          }
        ]
  }
  dependsOn: [storageAccount]
}

//========== SQL Database module ========== //
var sqlServerResourceName = 'sql-${solutionSuffix}'
var sqlDbModuleName = 'sqldb-${solutionSuffix}'
module sqlDBModule 'br/public:avm/res/sql/server:0.21.1' = {
  name: take('avm.res.sql.server.${sqlServerResourceName}', 64)
  params: {
    // Required parameters
    name: sqlServerResourceName
    enableTelemetry: enableTelemetry
    // Non-required parameters
    administrators: {
      azureADOnlyAuthentication: true
      login: userAssignedIdentity.outputs.name
      principalType: 'Application'
      sid: userAssignedIdentity.outputs.principalId
      tenantId: subscription().tenantId
    }
    connectionPolicy: 'Redirect'
    databases: [
      {
        availabilityZone: enableRedundancy ? 1 : -1
        collation: 'SQL_Latin1_General_CP1_CI_AS'
        diagnosticSettings: enableMonitoring
          ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }]
          : null
        licenseType: 'LicenseIncluded'
        maxSizeBytes: 34359738368
        name: sqlDbModuleName
        minCapacity: '1'
        sku: {
          name: 'GP_S_Gen5'
          tier: 'GeneralPurpose'
          family: 'Gen5'
          capacity: 2
        }
        // Note: Zone redundancy is not supported for serverless SKUs (GP_S_Gen5)
        zoneRedundant: enableRedundancy
      }
    ]
    location: secondaryLocation
    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        userAssignedIdentity.outputs.resourceId
        backendUserAssignedIdentity.outputs.resourceId
      ]
    }
    primaryUserAssignedIdentityResourceId: userAssignedIdentity.outputs.resourceId
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    firewallRules: (!enablePrivateNetworking)
      ? [
          {
            endIpAddress: '255.255.255.255'
            name: 'AllowSpecificRange'
            startIpAddress: '0.0.0.0'
          }
          {
            endIpAddress: '0.0.0.0'
            name: 'AllowAllWindowsAzureIps'
            startIpAddress: '0.0.0.0'
          }
        ]
      : []
    tags: allTags
  }
}

// ========== SQL Server Private Endpoint (separated) ========== //
module sqlDbPrivateEndpoint 'br/public:avm/res/network/private-endpoint:0.11.1' = if (enablePrivateNetworking) {
  name: take('avm.res.network.private-endpoint.sql-${solutionSuffix}', 64)
  params: {
    name: 'pep-sql-${solutionSuffix}'
    location: location
    tags: allTags
    enableTelemetry: enableTelemetry
    subnetResourceId: virtualNetwork!.outputs.pepsSubnetResourceId
    customNetworkInterfaceName: 'nic-sql-${solutionSuffix}'
    privateLinkServiceConnections: [
      {
        name: 'pl-sqlserver-${solutionSuffix}'
        properties: {
          privateLinkServiceId: sqlDBModule.outputs.resourceId
          groupIds: ['sqlServer']
        }
      }
    ]
    privateDnsZoneGroup: {
      privateDnsZoneGroupConfigs: [
        {
          privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.sqlServer]!.outputs.resourceId
        }
      ]
    }
  }
}

// ========== AVM WAF server farm ========== //
// WAF best practices for Web Application Services: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/app-service-web-apps
// PSRule for Web Server Farm: https://azure.github.io/PSRule.Rules.Azure/en/rules/resource/#app-service
var webServerFarmResourceName = 'asp-${solutionSuffix}'
module webServerFarm 'br/public:avm/res/web/serverfarm:0.5.0' = {
  name: 'deploy_app_service_plan_serverfarm'
  params: {
    name: webServerFarmResourceName
    tags: allTags
    enableTelemetry: enableTelemetry
    location: location
    reserved: true
    kind: 'linux'
    // WAF aligned configuration for Monitoring
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
    // WAF aligned configuration for Scalability
    skuName: enableScalability || enableRedundancy ? 'P1v3' : 'B3'
    skuCapacity: enableScalability ? 1 : 1
    // WAF aligned configuration for Redundancy
    zoneRedundant: enableRedundancy ? true : false
  }
}

var reactAppLayoutConfig = '''{
  "appConfig": {
    "THREE_COLUMN": {
      "DASHBOARD": 50,
      "CHAT": 33,
      "CHATHISTORY": 17
    },
    "TWO_COLUMN": {
      "DASHBOARD_CHAT": {
        "DASHBOARD": 65,
        "CHAT": 35
      },
      "CHAT_CHATHISTORY": {
        "CHAT": 80,
        "CHATHISTORY": 20
      }
    }
  },
  "charts": [
    {
      "id": "SATISFIED",
      "name": "Satisfied",
      "type": "card",
      "layout": { "row": 1, "column": 1, "height": 11 }
    },
    {
      "id": "TOTAL_CALLS",
      "name": "Total Calls",
      "type": "card",
      "layout": { "row": 1, "column": 2, "span": 1 }
    },
    {
      "id": "AVG_HANDLING_TIME",
      "name": "Average Handling Time",
      "type": "card",
      "layout": { "row": 1, "column": 3, "span": 1 }
    },
    {
      "id": "SENTIMENT",
      "name": "Sentiment overview",
      "type": "donutchart",
      "layout": { "row": 2, "column": 1, "width": 40, "height": 44.5 }
    },
    {
      "id": "AVG_HANDLING_TIME_BY_TOPIC",
      "name": "Average Handling Time By Topic",
      "type": "bar",
      "layout": { "row": 2, "column": 2, "row-span": 2, "width": 60 }
    },
    {
      "id": "TOPICS",
      "name": "Trending Topics",
      "type": "table",
      "layout": { "row": 3, "column": 1, "span": 2 }
    },
    {
      "id": "KEY_PHRASES",
      "name": "Key Phrases",
      "type": "wordcloud",
      "layout": { "row": 3, "column": 2, "height": 44.5 }
    }
  ]
}'''

// ========== AcrPull role assignments for App Service managed-identity pulls ========== //
// Only deployed when the registry name is provided AND MI-based pulls are enabled.
// Must run before the WebApp modules so the role exists at first image pull.
module backendAcrPullRole 'modules/acr-pull-role.bicep' = if (useManagedIdentityForAcrPull && !empty(containerRegistryNameForAcrPull)) {
  name: take('module.acr-pull.backend.${containerRegistryNameForAcrPull}', 64)
  params: {
    acrName: containerRegistryNameForAcrPull
    principalId: backendUserAssignedIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

module frontendAcrPullRole 'modules/acr-pull-role.bicep' = if (useManagedIdentityForAcrPull && !empty(containerRegistryNameForAcrPull)) {
  name: take('module.acr-pull.frontend.${containerRegistryNameForAcrPull}', 64)
  params: {
    acrName: containerRegistryNameForAcrPull
    principalId: userAssignedIdentity!.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

// ========== Web App module ========== //
var backendWebSiteResourceName = 'api-${solutionSuffix}'
module webSiteBackend 'modules/web-sites.bicep' = {
  name: take('module.web-sites.${backendWebSiteResourceName}', 64)
  dependsOn: useManagedIdentityForAcrPull && !empty(containerRegistryNameForAcrPull) ? [ backendAcrPullRole ] : []
  params: {
    name: backendWebSiteResourceName
    tags: allTags
    location: location
    kind: 'app,linux,container'
    serverFarmResourceId: webServerFarm.?outputs.resourceId
    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        backendUserAssignedIdentity.outputs.resourceId
      ]
    }
    siteConfig: {
      linuxFxVersion: 'DOCKER|${backendContainerRegistryHostname}/${backendContainerImageName}:${backendContainerImageTag}'
      minTlsVersion: '1.2'
      // When pulling from a private ACR, App Service must be told to authenticate
      // using its managed identity. When acrUserManagedIdentityID is omitted the
      // system-assigned managed identity is used, which avoids policies that block
      // user-assigned identities. The SAMI AcrPull role assignment is granted by
      // the backendWebSiteSamiAcrPullRole module.
      acrUseManagedIdentityCreds: useManagedIdentityForAcrPull || !empty(containerRegistryNameForAcrPull)
    }
    configs: [
      {
        name: 'appsettings'
        properties: {
          REACT_APP_LAYOUT_CONFIG: reactAppLayoutConfig
          AGENT_NAME_CONVERSATION: !empty(agentNameConversation) ? agentNameConversation : 'KM-ConversationAgent-${solutionSuffix}'
          AGENT_NAME_TITLE: !empty(agentNameTitle) ? agentNameTitle : 'KM-TitleAgent-${solutionSuffix}'
          MODEL_FILTER_ALLOWED_PUBLISHERS: modelFilterAllowedPublishers
          MODEL_FILTER_REQUIRE_FUNCTION_CALLING: modelFilterRequireFunctionCalling
          API_APP_NAME: 'api-${solutionSuffix}'
          AI_FOUNDRY_RESOURCE_ID: aiFoundryAiServices.outputs.resourceId
          AZURE_AI_AGENT_ENDPOINT: !empty(existingProjEndpoint) ? existingProjEndpoint : aiFoundryAiServices.outputs.aiProjectInfo.apiEndpoint
          AZURE_AI_AGENT_API_VERSION: azureAiAgentApiVersion
          AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME: gptModelName
          USE_CHAT_HISTORY_ENABLED: 'True'
          AZURE_COSMOSDB_ACCOUNT: cosmosDb.outputs.name
          AZURE_COSMOSDB_CONVERSATIONS_CONTAINER: collectionName
          AZURE_COSMOSDB_DATABASE: cosmosDbDatabaseName
          AZURE_COSMOSDB_ENABLE_FEEDBACK: 'True'
          SQLDB_DATABASE: 'sqldb-${solutionSuffix}'
          SQLDB_SERVER: '${sqlDBModule.outputs.name }${environment().suffixes.sqlServerHostname}'
          SQLDB_USER_MID: backendUserAssignedIdentity.outputs.clientId
          AZURE_AI_SEARCH_ENDPOINT: 'https://${aiSearchName}.search.windows.net'
          AZURE_AI_SEARCH_INDEX: 'call_transcripts_index'
          AZURE_AI_SEARCH_CONNECTION_NAME: aiSearchConnectionName
          USE_AI_PROJECT_CLIENT: 'True'
          DISPLAY_CHART_DEFAULT: 'False'
          DISPLAY_CHAT_BY_DEFAULT: 'True'
          APPLICATIONINSIGHTS_CONNECTION_STRING: enableMonitoring ? applicationInsights!.outputs.connectionString : ''
          DUMMY_TEST: 'True'
          SOLUTION_NAME: solutionSuffix
          APP_ENV: 'Prod'
          AZURE_CLIENT_ID: backendUserAssignedIdentity.outputs.clientId
          STORAGE_ACCOUNT_NAME: storageAccount.outputs.name
          AZURE_BASIC_LOGGING_LEVEL: 'INFO'
          AZURE_PACKAGE_LOGGING_LEVEL: 'WARNING'
          AZURE_LOGGING_PACKAGES: ''
        }
        // WAF aligned configuration for Monitoring
        applicationInsightResourceId: enableMonitoring ? applicationInsights!.outputs.resourceId : null
      }
    ]
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
    // WAF aligned configuration for Private Networking
    vnetRouteAllEnabled: enablePrivateNetworking ? true : false
    vnetImagePullEnabled: enablePrivateNetworking ? true : false
    virtualNetworkSubnetId: enablePrivateNetworking ? virtualNetwork!.outputs.webSubnetResourceId : null
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    privateEndpoints: enablePrivateNetworking
      ? [
          {
            name: 'pep-${backendWebSiteResourceName}'
            customNetworkInterfaceName: 'nic-${backendWebSiteResourceName}'
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                { privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.webApp]!.outputs.resourceId }
              ]
            }
            service: 'sites'
            subnetResourceId: virtualNetwork!.outputs.pepsSubnetResourceId
          }
        ]
      : []
  }
}

// ========== Web App module ========== //
// WAF best practices for Web Application Services: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/app-service-web-apps
//NOTE: AVM module adds 1 MB of overhead to the template. Keeping vanilla resource to save template size.
var webSiteResourceName = 'app-${solutionSuffix}'
module webSiteFrontend 'modules/web-sites.bicep' = {
  name: take('module.web-sites.${webSiteResourceName}', 64)
  dependsOn: useManagedIdentityForAcrPull && !empty(containerRegistryNameForAcrPull) ? [ frontendAcrPullRole ] : []
  params: {
    name: webSiteResourceName
    tags: allTags
    location: location
    kind: 'app,linux,container'
    serverFarmResourceId: webServerFarm.outputs.resourceId
    managedIdentities: {
      systemAssigned: true
      // When MI-based ACR pull is enabled, attach the shared user-assigned identity
      // so AcrPull can be granted before the WebApp is created (avoids the
      // chicken-and-egg problem with system-assigned identities).
      userAssignedResourceIds: useManagedIdentityForAcrPull ? [ userAssignedIdentity!.outputs.resourceId ] : []
    }
    siteConfig: {
      linuxFxVersion: 'DOCKER|${frontendContainerRegistryHostname}/${frontendContainerImageName}:${frontendContainerImageTag}'
      minTlsVersion: '1.2'
      acrUseManagedIdentityCreds: useManagedIdentityForAcrPull || !empty(containerRegistryNameForAcrPull)
    }
    configs: [
      {
        name: 'appsettings'
        properties: {
          APP_API_BASE_URL: enablePrivateNetworking ? '' : 'https://api-${solutionSuffix}.azurewebsites.net'
          BACKEND_API_HOST: enablePrivateNetworking ? 'api-${solutionSuffix}.azurewebsites.net' : ''
        }
        applicationInsightResourceId: enableMonitoring ? applicationInsights!.outputs.resourceId : null
      }
    ]
    vnetRouteAllEnabled: enablePrivateNetworking ? true : false
    vnetImagePullEnabled: enablePrivateNetworking ? true : false
    virtualNetworkSubnetId: enablePrivateNetworking ? virtualNetwork!.outputs.webSubnetResourceId : null
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
    publicNetworkAccess: 'Enabled'
  }
}

// ===================================================================
// ========== System-assigned identity RBAC mirror ===================
// ===================================================================
// Azure Policy in some tenants force-enables a system-assigned managed
// identity (SAMI) on every App Service in addition to the user-assigned
// managed identity (UAMI) this solution provisions. When both identities
// are attached, ``DefaultAzureCredential`` / ``ManagedIdentityCredential``
// can pick either one depending on which code path runs (and whether
// AZURE_CLIENT_ID is set on the specific call). Any path that resolves to
// the SAMI then fails with 401/403 against data-plane services because
// only the UAMI was granted permissions above.
//
// To make the deployment resilient in those tenants, we redundantly grant
// the SAMI of each App Service the SAME data-plane roles its UAMI has on
// the SAME target services. The assignments are idempotent (deterministic
// GUIDs) and harmless when the policy is not enforced — they simply give
// the SAMI a superset of permissions it would otherwise never use.
//
// NOTE: SQL Server admin (line ~1140) only accepts a single identity and
// cannot be dual-assigned, so it is intentionally NOT mirrored. Contained
// SQL users for the SAMI would need to be provisioned at the data plane
// (T-SQL ``CREATE USER ... FROM EXTERNAL PROVIDER``) which is out of scope
// for this Bicep template.
// ===================================================================

// --- Built-in role definition GUIDs (extracted for readability) ---
var roleId_AzureAIUser                          = '53ca6127-db72-4b80-b1b0-d745d6d5456d'
var roleId_AzureAIDeveloper                     = '64702f94-c441-49e6-a78b-ef80e0188fee'
var roleId_CognitiveServicesOpenAIUser          = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
var roleId_SearchServiceContributor             = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
var roleId_SearchIndexDataContributor           = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
var roleId_SearchIndexDataReader                = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
var roleId_StorageBlobDataContributor           = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var roleId_StorageAccountContributor            = '17d1049b-9a84-46fb-8f53-869881c3d3ab'
var roleId_StorageFileDataPrivilegedContributor = '69566ab7-960f-475b-8e7c-b3118f30c6bd'
var roleId_StorageBlobDelegator                 = 'db58b8e5-c6ad-4a2a-8342-4190687cbf4a'
// Cosmos DB Built-in Data Contributor (data plane). Has the same
// dataActions as the custom 'Cosmos DB SQL Data Contributor' role
// defined on the cosmos account above. Using the built-in avoids the
// circular dependency that referencing the AVM-created custom role
// definition would introduce.
var cosmosBuiltinDataContributorRoleId          = '00000000-0000-0000-0000-000000000002'

// ----------------------------------------------------------------
// --- Backend App Service (api-${suffix}) SAMI role assignments ---
// ----------------------------------------------------------------
// Mirrors every role granted to backendUserAssignedIdentity above on
// every service the backend touches. Search Service Contributor is
// additionally granted here because the backend startup probe needs to
// read index metadata.
//
// AI Foundry roles are mirrored via a dedicated module call when the AI
// Foundry account lives in a remote subscription/resource group
// (existing-foundry case), to avoid cross-RG ``existing`` references.

module backendWebSiteSamiMirror 'modules/web-site-sami-rbac-mirror.bicep' = {
  name: take('module.sami-mirror.${backendWebSiteResourceName}', 64)
  params: {
    appServiceName: backendWebSiteResourceName
    principalId: webSiteBackend.outputs.systemAssignedMIPrincipalId!
    aiFoundryAccountName: useExistingAiFoundryAiProject ? '' : aiFoundryAiServicesResourceName
    aiFoundryRoleIds: useExistingAiFoundryAiProject ? [] : [
      roleId_AzureAIUser
      roleId_AzureAIDeveloper
      roleId_CognitiveServicesOpenAIUser
    ]
    searchServiceName: aiSearchName
    searchRoleIds: [
      roleId_SearchIndexDataReader
      roleId_SearchServiceContributor
    ]
    cosmosAccountName: cosmosDbResourceName
    cosmosRoleIds: [
      cosmosBuiltinDataContributorRoleId
    ]
  }
  dependsOn: [
    cosmosDb
    searchServiceUpdate
  ]
}

// Cross-RG AI Foundry case: deploy role assignments in the remote RG.
module backendWebSiteSamiOnExistingAiFoundry 'modules/role-assignment.bicep' = [
  for roleId in [
    roleId_AzureAIUser
    roleId_AzureAIDeveloper
    roleId_CognitiveServicesOpenAIUser
  ]: if (useExistingAiFoundryAiProject) {
    name: take('module.ra.beSami-aiFoundry.${roleId}', 64)
    scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
    params: {
      principalId: webSiteBackend.outputs.systemAssignedMIPrincipalId!
      roleDefinitionId: roleId
      targetResourceName: '${aiFoundryAiServicesResourceName}-beSami'
    }
  }
]

module backendWebSiteSamiAcrPullRole 'modules/acr-pull-role.bicep' = if (!empty(containerRegistryNameForAcrPull)) {
  name: take('module.acr-pull.sami.backend.${containerRegistryNameForAcrPull}', 64)
  params: {
    acrName: containerRegistryNameForAcrPull
    principalId: webSiteBackend.outputs.systemAssignedMIPrincipalId!
    principalType: 'ServicePrincipal'
  }
}

// -----------------------------------------------------------------
// --- Frontend App Service (app-${suffix}) SAMI role assignments ---
// -----------------------------------------------------------------
// Mirrors every role granted to userAssignedIdentity above for the
// services the frontend touches. SQL Server admin (line ~1140) is
// intentionally NOT mirrored: SQL Server accepts a single administrator
// identity only.

module frontendWebSiteSamiMirror 'modules/web-site-sami-rbac-mirror.bicep' = {
  name: take('module.sami-mirror.${webSiteResourceName}', 64)
  params: {
    appServiceName: webSiteResourceName
    principalId: webSiteFrontend.outputs.systemAssignedMIPrincipalId!
    aiFoundryAccountName: useExistingAiFoundryAiProject ? '' : aiFoundryAiServicesResourceName
    aiFoundryRoleIds: useExistingAiFoundryAiProject ? [] : [
      roleId_AzureAIUser
      roleId_AzureAIDeveloper
      roleId_CognitiveServicesOpenAIUser
    ]
    aiFoundryCuAccountName: aiServicesNameCu
    aiFoundryCuRoleIds: [
      roleId_AzureAIUser
    ]
    searchServiceName: aiSearchName
    searchRoleIds: [
      roleId_SearchServiceContributor
      roleId_CognitiveServicesOpenAIUser
      roleId_SearchIndexDataContributor
      roleId_SearchIndexDataReader
    ]
    storageAccountName: storageAccountName
    storageRoleIds: [
      roleId_StorageBlobDataContributor
      roleId_StorageAccountContributor
      roleId_StorageFileDataPrivilegedContributor
      roleId_StorageBlobDelegator
    ]
  }
  dependsOn: [
    searchServiceUpdate
    storageAccount
  ]
}

module frontendWebSiteSamiOnExistingAiFoundry 'modules/role-assignment.bicep' = [
  for roleId in [
    roleId_AzureAIUser
    roleId_AzureAIDeveloper
    roleId_CognitiveServicesOpenAIUser
  ]: if (useExistingAiFoundryAiProject) {
    name: take('module.ra.feSami-aiFoundry.${roleId}', 64)
    scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
    params: {
      principalId: webSiteFrontend.outputs.systemAssignedMIPrincipalId!
      roleDefinitionId: roleId
      targetResourceName: '${aiFoundryAiServicesResourceName}-feSami'
    }
  }
]

module frontendWebSiteSamiAcrPullRole 'modules/acr-pull-role.bicep' = if (!empty(containerRegistryNameForAcrPull)) {
  name: take('module.acr-pull.sami.frontend.${containerRegistryNameForAcrPull}', 64)
  params: {
    acrName: containerRegistryNameForAcrPull
    principalId: webSiteFrontend.outputs.systemAssignedMIPrincipalId!
    principalType: 'ServicePrincipal'
  }
}

// ========== Outputs ========== //
@description('Contains Solution Name.')
output SOLUTION_NAME string = solutionSuffix

@description('Contains Resource Group Name.')
output RESOURCE_GROUP_NAME string = resourceGroup().name

@description('Contains Resource Group Location.')
output RESOURCE_GROUP_LOCATION string = location

@description('Contains Azure Content Understanding Location.')
output AZURE_ENV_CU_LOCATION string = contentUnderstandingLocation

// @description('Contains Azure Secondary Location.')
// output AZURE_SECONDARY_LOCATION string = secondaryLocation

@description('Contains Application Insights Instrumentation Key.')
output APPINSIGHTS_INSTRUMENTATIONKEY string = enableMonitoring ? applicationInsights!.outputs.instrumentationKey : ''

@description('Contains AI Project Connection String.')
output AZURE_AI_PROJECT_CONN_STRING string = !empty(existingProjEndpoint) ? existingProjEndpoint : aiFoundryAiServices.outputs.endpoint

@description('Contains Azure AI Agent API Version.')
output AZURE_AI_AGENT_API_VERSION string = azureAiAgentApiVersion

@description('Contains Azure AI Foundry service name.')
output AZURE_AI_FOUNDRY_NAME string = !empty(existingAIServicesName) ? existingAIServicesName : aiFoundryAiServices.outputs.name

@description('Contains Azure AI Project name.')
output AZURE_AI_PROJECT_NAME string = !empty(existingAIProjectName) ? existingAIProjectName : aiFoundryAiServices.outputs.aiProjectInfo.name

@description('Contains Azure AI Search service name.')
output AZURE_AI_SEARCH_NAME string = aiSearchName

@description('Contains Azure AI Search endpoint URL.')
output AZURE_AI_SEARCH_ENDPOINT string = 'https://${aiSearchName}.search.windows.net'

@description('Contains Azure AI Search index name.')
output AZURE_AI_SEARCH_INDEX string = 'call_transcripts_index'

@description('Contains Azure AI Search connection name.')
output AZURE_AI_SEARCH_CONNECTION_NAME string = aiSearchConnectionName

@description('Contains Azure Cosmos DB account name.')
output AZURE_COSMOSDB_ACCOUNT string = cosmosDb.outputs.name

@description('Contains Azure Cosmos DB conversations container name.')
output AZURE_COSMOSDB_CONVERSATIONS_CONTAINER string = 'conversations'

@description('Contains Azure Cosmos DB database name.')
output AZURE_COSMOSDB_DATABASE string = 'db_conversation_history'

@description('Contains Azure Cosmos DB feedback enablement setting.')
output AZURE_COSMOSDB_ENABLE_FEEDBACK string = 'True'

@description('Contains Azure OpenAI deployment model name.')
output AZURE_ENV_GPT_MODEL_NAME string = gptModelName

@description('Contains Azure OpenAI deployment model capacity.')
output AZURE_ENV_GPT_MODEL_CAPACITY int = gptDeploymentCapacity

@description('Contains Azure OpenAI endpoint URL.')
output AZURE_OPENAI_ENDPOINT string = 'https://${aiFoundryAiServices.outputs.name}.openai.azure.com/'

@description('Contains Azure OpenAI model deployment type.')
output AZURE_ENV_MODEL_DEPLOYMENT_TYPE string = deploymentType

@description('Contains Azure OpenAI embedding model name.')
output AZURE_ENV_EMBEDDING_MODEL_NAME string = embeddingModel

@description('Contains Azure OpenAI embedding model capacity.')
output AZURE_ENV_EMBEDDING_DEPLOYMENT_CAPACITY int = embeddingDeploymentCapacity

@description('Contains Content Understanding API version.')
output AZURE_CONTENT_UNDERSTANDING_API_VERSION string = azureContentUnderstandingApiVersion

@description('Contains Azure OpenAI resource name.')
output AZURE_OPENAI_RESOURCE string = aiFoundryAiServices.outputs.name

@description('Contains React app layout configuration.')
output REACT_APP_LAYOUT_CONFIG string = reactAppLayoutConfig

@description('Contains SQL database name.')
output SQLDB_DATABASE string = 'sqldb-${solutionSuffix}'

@description('Contains SQL server name.')
output SQLDB_SERVER string = '${sqlDBModule.outputs.name }${environment().suffixes.sqlServerHostname}'

@description('Display name of the backend API user-assigned managed identity (also used for SQL database access).')
output BACKEND_USER_MID_NAME string = backendUserAssignedIdentity.outputs.name

@description('Client ID of the backend API user-assigned managed identity (also used for SQL database access).')
output BACKEND_USER_MID string = backendUserAssignedIdentity.outputs.clientId

@description('Contains AI project client usage setting.')
output USE_AI_PROJECT_CLIENT string = 'False'

@description('Contains chat history enablement setting.')
output USE_CHAT_HISTORY_ENABLED string = 'True'

@description('Contains default chart display setting.')
output DISPLAY_CHART_DEFAULT string = 'False'

@description('Contains default chat display setting.')
output DISPLAY_CHAT_BY_DEFAULT string = 'True'

@description('Contains Azure AI Agent endpoint URL.')
output AZURE_AI_AGENT_ENDPOINT string = !empty(existingProjEndpoint) ? existingProjEndpoint : aiFoundryAiServices.outputs.aiProjectInfo.apiEndpoint

@description('Contains Azure AI Agent model deployment name.')
output AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME string = gptModelName

@description('Contains Azure Container Registry name.')
output ACR_NAME string = acrName

@description('Contains Azure environment image tag.')
output AZURE_ENV_IMAGE_TAG string = backendContainerImageTag

@description('Contains Application Insights connection string.')
output APPLICATIONINSIGHTS_CONNECTION_STRING string = enableMonitoring ? applicationInsights!.outputs.connectionString : ''

@description('Contains API application URL.')
output API_APP_URL string = 'https://api-${solutionSuffix}.azurewebsites.net'

@description('Contains web application URL.')
output WEB_APP_URL string = 'https://app-${solutionSuffix}.azurewebsites.net'

@description('Name of the Storage Account.')
output STORAGE_ACCOUNT_NAME string = storageAccount.outputs.name

@description('Name of the Storage Container.')
output STORAGE_CONTAINER_NAME string = 'data'

@description('Resource ID of the AI Foundry.')
output AI_FOUNDRY_RESOURCE_ID string = aiFoundryAiServices.outputs.resourceId

@description('Resource ID of the Content Understanding AI Foundry.')
output CU_FOUNDRY_RESOURCE_ID string = cognitiveServicesCu.outputs.resourceId

@description('Azure OpenAI Content Understanding endpoint URL.')
output AZURE_OPENAI_CU_ENDPOINT string = cognitiveServicesCu.outputs.endpoint

@description('Contains API application name.')
output API_APP_NAME string = 'api-${solutionSuffix}'

@description('Contains Conversation Agent name.')
output AGENT_NAME_CONVERSATION string = !empty(agentNameConversation) ? agentNameConversation : 'KM-ConversationAgent-${solutionSuffix}'

@description('Contains Title Agent name.')
output AGENT_NAME_TITLE string = !empty(agentNameTitle) ? agentNameTitle : 'KM-TitleAgent-${solutionSuffix}'

@description('Industry Use Case.')
output USE_CASE string = usecase
