# Updates API and WebApp images

## Variables

```bash
RG=rg-swc-s3-sc-ccanalysis-iter-01
ACR=acrsccanalysisit01
APP=app-iter01l2yhy
IMAGE_WEB=sc-ccanalysis-web
API_APP=api-iter01l2yhy
IMAGE_API=sc-ccanalysis-api
```

## Update the Web App

```bash
cd src/App
TAG_WEB=iter01-$(date +%Y%m%d-%H%M)
az acr build -r "$ACR" -t "$IMAGE_WEB:$TAG_WEB" -f WebApp.Dockerfile .
az webapp config container set -g "$RG" -n "$APP" --container-image-name "$ACR.azurecr.io/$IMAGE_WEB:$TAG_WEB"
az webapp restart -g "$RG" -n "$APP"
cd ../..
```

## Update the API backend

```bash
cd src/api
TAG_API=custom-$(date +%Y%m%d-%H%M)
az acr build -r "$ACR" -t "$IMAGE_API:$TAG_API" -f ApiApp.Dockerfile .
az webapp restart -g "$RG" -n "$API_APP"
cd ../..
```

# Windows (PowerShell)

## Variables

```powershell
$RG = "rg-swc-s3-sc-ccanalysis-iter-01"
$ACR = "acrsccanalysisit01"
$APP = "app-iter01l2yhy"
$IMAGE_WEB = "sc-ccanalysis-web"
$API_APP = "api-iter01l2yhy"
$IMAGE_API = "sc-ccanalysis-api"$

```

## Update the Web App

```powershell
Set-Location src/App
$TAG_WEB = "iter01-$(Get-Date -Format 'yyyyMMdd-HHmm')"
az acr build -r $ACR -t "${IMAGE_WEB}:${TAG_WEB}" -f WebApp.Dockerfile .
az webapp config container set -g $RG -n $APP --container-image-name "$ACR.azurecr.io/${IMAGE_WEB}:${TAG_WEB}"
az webapp restart -g $RG -n $APP
Set-Location ../..

```

## Update the API backend

```powershell
Set-Location src/api
$TAG_API = "custom-$(Get-Date -Format 'yyyyMMdd-HHmm')"
az acr build -r $ACR -t "${IMAGE_API}:${TAG_API}" -f ApiApp.Dockerfile .
az webapp config container set -g $RG -n $API_APP --container-image-name "$ACR.azurecr.io/${IMAGE_API}:${TAG_API}"
az webapp restart -g $RG -n $API_APP
Set-Location ../..

```
