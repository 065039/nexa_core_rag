# Offline Setup with Docker (Windows downloads, Ubuntu runs)

Use this when Ubuntu (WSL) on the lab PC has no internet but Windows does. Windows builds one Docker image that already contains Docling, LlamaIndex, Streamlit and all models. Ubuntu loads that image from a file and runs parsing and indexing with no internet.

One thing Docker cannot remove: **Ollama Cloud is an online API**, so the question-answering step must run where there is internet. Step 5 covers that.

## What you need

- Docker Desktop running on Windows. Check in PowerShell with `docker version`. If it says "not recognized", Docker Desktop is not installed and this route will not work on this PC.
- About 10 GB free on `C:`.

## 1. Put the project on the C: drive (Windows)

Unzip `nexacore-rag.zip` so the folder is `C:\nexacore-rag`. Both sides can see it:

| Side | Path |
|---|---|
| Windows | `C:\nexacore-rag` |
| Ubuntu | `/mnt/c/nexacore-rag` |

## 2. Build and save the images (Windows PowerShell)

```powershell
cd C:\nexacore-rag
copy .env.example .env
powershell -ExecutionPolicy Bypass -File scripts\windows_build_images.ps1
```

This takes 15 to 25 minutes the first time and creates `C:\nexacore-rag\docker-images\nexacore-images.tar` (about 3 to 5 GB).

## 3. Load the images (Ubuntu)

```bash
cd /mnt/c/nexacore-rag
bash scripts/wsl_load_images.sh
```

The script also runs Docling inside the image with networking switched off (`--network none`) to prove the install is offline. Screenshot this for the installation steps.

If you see `$'\r': command not found`, the script picked up Windows line endings. Fix with `sed -i 's/\r$//' scripts/*.sh` and run again.

## 4. Part-I and indexing, fully offline (Ubuntu)

```bash
cd /mnt/c/nexacore-rag
docker compose -f docker-compose.offline.yml up -d qdrant
docker compose -f docker-compose.offline.yml run --rm app python -m src.parser
docker compose -f docker-compose.offline.yml run --rm app python scripts/validate_markdown.py
docker compose -f docker-compose.offline.yml run --rm app python -m src.indexing --recreate
docker compose -f docker-compose.offline.yml run --rm app python -m evaluation.run_eval --ablation
```

Output lands in `C:\nexacore-rag\data\converted` and `C:\nexacore-rag\evaluation\results`, visible from Windows too. Use `sudo docker compose ...` if Docker asks for permission.

## 5. Question answering with Ollama Cloud (needs internet)

First check whether containers in Ubuntu can reach Ollama Cloud (sometimes they can even when Ubuntu cannot):

```bash
docker compose -f docker-compose.offline.yml run --rm app curl -I --max-time 10 https://ollama.com
```

**If that returns `200`:** stay in Ubuntu.

```bash
nano .env        # add OLLAMA_API_KEY and OLLAMA_MODEL
docker compose -f docker-compose.offline.yml run --rm app python scripts/check_ollama.py
docker compose -f docker-compose.offline.yml up app
```

**If it times out:** run the app on Windows Docker Desktop, which has internet. The same image is already built there. In PowerShell:

```powershell
cd C:\nexacore-rag
notepad .env     # add OLLAMA_API_KEY and OLLAMA_MODEL
docker compose -f docker-compose.offline.yml up -d qdrant
docker compose -f docker-compose.offline.yml run --rm app python -m src.indexing --recreate
docker compose -f docker-compose.offline.yml run --rm app python scripts/check_ollama.py
docker compose -f docker-compose.offline.yml up app
```

Windows Docker keeps its own Qdrant, so indexing runs once more there (under a minute). The Markdown it indexes is the output Docling produced in Ubuntu in step 4.

Open `http://localhost:8501`. For phones, see `docs/DEPLOYMENT.md` (run `cloudflared` on Windows).

## How this meets the brief

| Brief | How |
|---|---|
| Parser installed on WSL Ubuntu | Docling runs in Ubuntu from an Ubuntu 22.04 image, offline, with screenshots from step 3 and 4 |
| LlamaIndex application | Same image, indexing in Ubuntu, answering wherever Ollama Cloud is reachable |
| Machine IP | Same lab PC either way: `ipconfig` in Windows or `bash scripts/get_ip.sh` |
| Installation steps | This page plus `Dockerfile` (every install command is in it) |
