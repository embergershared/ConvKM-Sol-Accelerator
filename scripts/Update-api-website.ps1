# Variables
$RG        = "rg-swc-s3-sc-ccanalysis-iter-03"
$ACR       = "acriter02n7y67"
$APP       = "app-iter02n7y67"
$IMAGE_WEB = "sc-ccanalysis-web"
$API_APP   = "api-iter02n7y67"
$IMAGE_API = "sc-ccanalysis-api"

# Shared timestamp tag for both images (local time)
$TAG     = "iter03-$((Get-Date).ToLocalTime().ToString('yyyyMMdd-HHmm'))"
$TAG_API = $TAG
$TAG_WEB = $TAG

# Authenticate the local Docker daemon to ACR
az acr login -n $ACR

# Build + push the API image
docker build --platform linux/amd64 `
  -t "$ACR.azurecr.io/${IMAGE_API}:${TAG_API}" `
  -f src/api/ApiApp.Dockerfile src/api
docker push "$ACR.azurecr.io/${IMAGE_API}:${TAG_API}"
az webapp config container set -g $RG -n $API_APP --container-image-name "$ACR.azurecr.io/${IMAGE_API}:${TAG_API}"
az webapp restart -g $RG -n $API_APP

# Build + push the Web App image
docker build --platform linux/amd64 `
  -t "$ACR.azurecr.io/${IMAGE_WEB}:${TAG_WEB}" `
  -f src/App/WebApp.Dockerfile src/App
docker push "$ACR.azurecr.io/${IMAGE_WEB}:${TAG_WEB}"
az webapp config container set -g $RG -n $APP --container-image-name "$ACR.azurecr.io/${IMAGE_WEB}:${TAG_WEB}"
az webapp restart -g $RG -n $APP