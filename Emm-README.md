# Emm-README — Extra Steps Beyond the Standard Deployment

This file captures the additional steps performed on top of the standard
[`README.md`](./README.md) deployment instructions. Run them in order.

Deploy from scratch

azd auth login
azd config set provision.preflight off

azd env new iter02 --location swedencentral --subscription 4c88693f-5cc9-4f30-9d1e-d58d4221cf25 --set-default

azd up




---

## 1. Fix CRLF line endings on shell scripts

Scripts under `infra/scripts/` were checked out with Windows line endings,
which causes `bad interpreter: /bin/bash^M` errors when running them inside
the Linux dev container.

```bash
find ./infra/scripts -type f \( -name "*.sh" -o -name "*.py" \) \
  -exec sed -i 's/\r$//' {} +
```

Run this once after cloning, before executing any `./infra/scripts/*.sh`.

---

## 2. Customize the header (logo / labels)

Branding lives in the React frontend at `src/App/src/App.tsx` (around
lines 256–262):

```tsx
<div className="header-left-section">
  <AppLogo />                                  {/* SVG component in src/components/Svg/Svg.tsx */}
  <Subtitle2>
    Woodgrove <Body2 style={{ gap: "10px" }}>| Call Analysis</Body2>
  </Subtitle2>
</div>
```

- **Text:** edit the `Woodgrove` / `| Call Analysis` strings.
- **Logo:** see section 3 below.

---

## 3. Swap the header logo image

The logo is a Fluent UI `Avatar` whose `image.src` is a giant inline base64
JPEG, defined in `src/App/src/components/Svg/Svg.tsx` (the `AppLogo` export).
Replace that `src` value with your own image. Easiest path:

### Option A — drop a file into `public/` (no imports needed)

1. Copy your image into `src/App/public/`, e.g. `src/App/public/my-logo.png`.
2. Edit `src/App/src/components/Svg/Svg.tsx` and replace the long
   `data:image/jpeg;base64,...` string with `"/my-logo.png"`:

   ```tsx
   <Avatar
     image={{ src: "/my-logo.png" }}
     name="App Logo"
     shape="square"
     size={56}
     aria-label="App Logo"
     style={{ width: "25px", height: "25px" }}
   />
   ```

Anything in `public/` is served from the site root, so `/my-logo.png` works
in the running container.

### Option B — import from `src/` (bundled with content-hash)

1. Put the file under `src/`, e.g. `src/App/src/assets/my-logo.png`.
2. At the top of `Svg.tsx`:
   ```tsx
   import logoSrc from "../../assets/my-logo.png";
   ```
3. Replace the `src` value with `logoSrc`.

### Option C — keep it inline as base64

```bash
echo "data:image/png;base64,$(base64 -w0 my-logo.png)"
```
Paste the output as the new `src` value.

### Tips

- The Avatar is constrained to 25×25 px by the inline `style`. If your logo
  is wider than tall, swap `<Avatar>` for a plain `<img>`:
  ```tsx
  <img src="/my-logo.png" alt="App Logo" style={{ height: 28 }} />
  ```
- For transparent backgrounds, use PNG or SVG (not JPEG).

---

## 4. Renaming dashboard cards (e.g. "Topics Overview" → "Sentiment overview")

Card titles come from **two** places, and the order matters:

1. **Backend SQL query** — `src/api/common/database/sqldb_service.py` (look
   for `as chart_name` in the big `UNION ALL` around lines 227–247). When
   the chart data API returns a row, the frontend uses that `chart_name`.
2. **Layout config JSON** — `REACT_APP_LAYOUT_CONFIG` env var on the
   backend Web App (also defined in `infra/main.bicep` /
   `infra/main_custom.bicep`). Used as a fallback when the API returns
   nothing.

`src/App/src/components/Chart/Chart.tsx` line ~129:
```ts
title: apiData ? apiData.chart_name : configChart.name || "",
```

So **for any card that has live data, you must update the SQL string** and
rebuild the backend image. Updating only the layout config will not change
the title.

### 4a. Edit both sources

In `src/api/common/database/sqldb_service.py`, change the literal in the
SELECT, e.g.:
```python
select 'SENTIMENT' as id, 'Sentiment overview' as chart_name, 'donutchart' as chart_type,
```

In `infra/main.bicep` and `infra/main_custom.bicep`, update the matching
chart `"name"` inside the `reactAppLayoutConfig` JSON so future provisions
stay in sync:
```json
{ "id": "SENTIMENT", "name": "Sentiment overview", "type": "donutchart", ... }
```

### 4b. Rebuild & deploy the backend image

The backend container is `kmcontainerreg.azurecr.io/km-api:<tag>` by
default. Build your own and point the backend Web App at it:

```bash
RG=<your-resource-group>
ACR=<your-acr-name>
API_APP=$(az webapp list -g "$RG" --query "[?starts_with(name,'api-')].name" -o tsv)

TAG=custom-$(date +%Y%m%d-%H%M)
cd src/api
az acr build -r "$ACR" -t "km-api:$TAG" -f ApiApp.Dockerfile .
cd -

ACR_USER=$(az acr credential show -n "$ACR" --query username -o tsv)
ACR_PASS=$(az acr credential show -n "$ACR" --query passwords[0].value -o tsv)
az webapp config container set \
  -g "$RG" -n "$API_APP" \
  --container-image-name "$ACR.azurecr.io/km-api:$TAG" \
  --container-registry-url "https://$ACR.azurecr.io" \
  --container-registry-user "$ACR_USER" \
  --container-registry-password "$ACR_PASS"
az webapp restart -g "$RG" -n "$API_APP"
```

Also bump the matching IaC params in `infra/main.bicep` so future provisions
use your backend image (mirrors section 6 for the frontend):

```bicep
param backendContainerRegistryHostname string = '<your-acr>.azurecr.io'
param backendContainerImageName       string = 'km-api'
param backendContainerImageTag        string = 'custom'
```

### 4c. (Optional) Patch the layout-config env var as a one-off

Only useful for cards/sections whose title falls through to the config
(no live data, or you want a temporary override):

```bash
CURRENT=$(az webapp config appsettings list -g "$RG" -n "$API_APP" \
  --query "[?name=='REACT_APP_LAYOUT_CONFIG'].value | [0]" -o tsv)
UPDATED=$(printf '%s' "$CURRENT" | sed 's/"Topics Overview"/"Sentiment overview"/')
az webapp config appsettings set -g "$RG" -n "$API_APP" \
  --settings REACT_APP_LAYOUT_CONFIG="$UPDATED"
az webapp restart -g "$RG" -n "$API_APP"
```

---

## 5. Build & deploy the customized frontend image

The standard deployment pulls the frontend image from Microsoft's public
registry (`kmcontainerreg.azurecr.io/km-app:<tag>` — see
`infra/main.bicep` lines 115–122). To ship your changes you must build your
own image, push it to a registry you control, and repoint the Web App at it.

### 5a. Set variables

```bash
RG=<your-resource-group>          # same RG the accelerator deployed into
ACR=<your-acr-name>               # globally unique, lowercase, alphanumeric
APP=$(az webapp list -g "$RG" --query "[?starts_with(name,'app-')].name" -o tsv)
echo "Web App: $APP"
```

### 5b. Create an ACR (skip if you already have one)

```bash
az acr create -g "$RG" -n "$ACR" --sku Basic --admin-enabled true
```

### 5c. Build & push the image (cloud build, no local Docker needed)

```bash
cd src/App
az acr build -r $ACR -t sc-ccanalysis:iter01-01 -f WebApp.Dockerfile .
cd -
```

### 5d. Point the Web App at your image

```bash
ACR_USER=$(az acr credential show -n "$ACR" --query username -o tsv)
ACR_PASS=$(az acr credential show -n "$ACR" --query passwords[0].value -o tsv)

az webapp config container set \
  -g "$RG" -n "$APP" \
  --container-image-name "$ACR.azurecr.io/km-app:custom" \
  --container-registry-url "https://$ACR.azurecr.io" \
  --container-registry-user "$ACR_USER" \
  --container-registry-password "$ACR_PASS"

az webapp restart -g "$RG" -n "$APP"
```

Wait ~1–2 minutes for the pull + cold start, then reload the Web App URL.

---

## 6. (Optional) Make the image change persistent in IaC

So that future `azd provision` / `azd up` runs don't revert to the upstream
image, update these params in `infra/main.bicep`:

```bicep
param frontendContainerRegistryHostname string = '<your-acr>.azurecr.io'
param frontendContainerImageName       string = 'km-app'
param frontendContainerImageTag        string = 'custom'
```

---

## Iterating on further frontend changes

Repeat steps **5c** and **5d** (bump the tag, e.g. `custom-v2`, so the Web
App definitely re-pulls):

```bash
# RG=rg-swc-s3-sc-ccanalysis-iter-01
# ACR=acrsccanalysisit01
# APP=app-iter01l2yhy
# IMAGE=sc-ccanalysis-web
TAG=iter01-$(date +%Y%m%d-%H%M)

az acr build -r "$ACR" -t "$IMAGE:$TAG" -f WebApp.Dockerfile .
az webapp config container set -g "$RG" -n "$APP" --container-image-name "$ACR.azurecr.io/$IMAGE:$TAG"
az webapp restart -g "$RG" -n "$APP"
```


## Rebuild the Backend API

```bash
# Rebuild the API backend now:
API_APP=api-iter01l2yhy
IMAGE_API=sc-ccanalysis-api

# build & push from src/api (note: Dockerfile is ApiApp.Dockerfile)
TAG_API=custom-$(date +%Y%m%d-%H%M)
cd src/api
az acr build -r "$ACR" -t "$IMAGE_API:$TAG_API" -f ApiApp.Dockerfile .

# point the backend Web App at it
ACR_USER=$(az acr credential show -n "$ACR" --query username -o tsv)
ACR_PASS=$(az acr credential show -n "$ACR" --query passwords[0].value -o tsv)
az webapp config container set \
  -g "$RG" -n "$API_APP" \
  --container-image-name "$ACR.azurecr.io/$IMAGE_API:$TAG_API" \
  --container-registry-url "https://$ACR.azurecr.io" \
  --container-registry-user "$ACR_USER" \
  --container-registry-password "$ACR_PASS"

az webapp restart -g "$RG" -n "$API_APP"
```

## Samples questions

https://github.com/embergershared/ConvKM-Sol-Accelerator/blob/main/documents/SampleQuestions.md

