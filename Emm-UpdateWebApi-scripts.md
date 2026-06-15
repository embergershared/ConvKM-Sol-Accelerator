# Updates API and WebApp images

> **Important — delete `node_modules` first** (handled by the script below). `az acr build`
> walks every file under `node_modules` even when `.dockerignore` excludes it (only `.venv`
> gets a hardcoded skip-recursion fast-path in `azure-cli`'s `_archive_utils.py`). With the
> full `node_modules` tree present the upload can hang for many minutes spamming
> `.dockerignore: no rule for 'node_modules/...'` debug lines. `WebApp.Dockerfile` runs
> `npm ci` inside the image (line 6), so the host `node_modules` is unused by the build
> and safe to delete.

## Bash — single copy-paste block

Updates both the API and the Web App with a shared local-time timestamp tag.

```bash
# Variables
RG=rg-swc-s3-sc-ccanalysis-iter-03
ACR=acriter02n7y67
APP=app-iter02n7y67
IMAGE_WEB=sc-ccanalysis-web
API_APP=api-iter02n7y67
IMAGE_API=sc-ccanalysis-api

# Shared timestamp tag for both images (local time)
TAG=iter03-$(date +%Y%m%d-%H%M)
TAG_API=$TAG
TAG_WEB=$TAG

# Update the API backend first, when big changes
( cd src/api \
  && az acr build -r "$ACR" -t "$IMAGE_API:$TAG_API" -f ApiApp.Dockerfile . \
  && az webapp config container set -g "$RG" -n "$API_APP" --container-image-name "$ACR.azurecr.io/$IMAGE_API:$TAG_API" \
  && az webapp restart -g "$RG" -n "$API_APP" )

# Update the Web App (delete node_modules first — see note above)
( cd src/App \
  && rm -rf node_modules \
  && az acr build -r "$ACR" -t "$IMAGE_WEB:$TAG_WEB" -f WebApp.Dockerfile . \
  && az webapp config container set -g "$RG" -n "$APP" --container-image-name "$ACR.azurecr.io/$IMAGE_WEB:$TAG_WEB" \
  && az webapp restart -g "$RG" -n "$APP" )
```

## PowerShell — single copy-paste block

Same flow as above, using PowerShell syntax (variables, timestamp tags, and `Remove-Item` instead of `rm -rf`).

```powershell
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

# Update the API backend first, when big changes
Push-Location src/api
az acr build -r $ACR -t "${IMAGE_API}:${TAG_API}" -f ApiApp.Dockerfile .
az webapp config container set -g $RG -n $API_APP --container-image-name "$ACR.azurecr.io/${IMAGE_API}:${TAG_API}"
az webapp restart -g $RG -n $API_APP
Pop-Location

# Update the Web App (delete node_modules first — see note above)
Push-Location src/App
if (Test-Path node_modules) { Remove-Item -Recurse -Force node_modules }
az acr build -r $ACR -t "${IMAGE_WEB}:${TAG_WEB}" -f WebApp.Dockerfile . # --debug
az webapp config container set -g $RG -n $APP --container-image-name "$ACR.azurecr.io/${IMAGE_WEB}:${TAG_WEB}"
az webapp restart -g $RG -n $APP
Pop-Location
```

## Local Docker build + push to ACR

Builds both images on the local Docker daemon and pushes them to ACR. Faster when the
build context is large (notably the WebApp's `node_modules`) because nothing is uploaded
to ACR except final image layers, and the local Docker daemon honors `.dockerignore`
properly (so there's no need to delete `node_modules` first). Requires Docker Desktop
running and `az` logged in.

> The Dockerfiles target `linux/amd64`. On Apple Silicon / ARM hosts, the `--platform`
> flag below forces a matching build (via emulation; slower).

### Bash

```bash
# Variables
RG=rg-swc-s3-sc-ccanalysis-iter-03
ACR=acriter02n7y67
APP=app-iter02n7y67
IMAGE_WEB=sc-ccanalysis-web
API_APP=api-iter02n7y67
IMAGE_API=sc-ccanalysis-api

# Shared timestamp tag for both images (local time)
TAG=iter03-$(date +%Y%m%d-%H%M)
TAG_API=$TAG
TAG_WEB=$TAG

# Authenticate the local Docker daemon to ACR
az acr login -n "$ACR"

# Build + push the API image
docker build --platform linux/amd64 \
  -t "$ACR.azurecr.io/$IMAGE_API:$TAG_API" \
  -f src/api/ApiApp.Dockerfile src/api \
  && docker push "$ACR.azurecr.io/$IMAGE_API:$TAG_API" \
  && az webapp config container set -g "$RG" -n "$API_APP" --container-image-name "$ACR.azurecr.io/$IMAGE_API:$TAG_API" \
  && az webapp restart -g "$RG" -n "$API_APP"

# Build + push the Web App image
docker build --platform linux/amd64 \
  -t "$ACR.azurecr.io/$IMAGE_WEB:$TAG_WEB" \
  -f src/App/WebApp.Dockerfile src/App \
  && docker push "$ACR.azurecr.io/$IMAGE_WEB:$TAG_WEB" \
  && az webapp config container set -g "$RG" -n "$APP" --container-image-name "$ACR.azurecr.io/$IMAGE_WEB:$TAG_WEB" \
  && az webapp restart -g "$RG" -n "$APP"
```

### PowerShell

```powershell
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
```


