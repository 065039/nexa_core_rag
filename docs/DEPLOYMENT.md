# Deployment and Web Access

The app runs on the lab machine. College networks usually block inbound connections, so a phone outside the lab cannot open `http://<lab-ip>:8501` directly. Two options:

## Option A: Same Wi-Fi as the lab machine

```bash
streamlit run app/streamlit_app.py --server.address 0.0.0.0 --server.port 8501
bash scripts/get_ip.sh
```

Open `http://<local-ip>:8501` on a phone connected to the same network. If it does not load, the network isolates clients; use option B.

## Option B: Public HTTPS link with Cloudflare Tunnel (recommended for the demo)

No account is needed for a quick tunnel.

```bash
# install once
curl -L -o /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i /tmp/cloudflared.deb

# terminal 1
streamlit run app/streamlit_app.py --server.port 8501

# terminal 2
cloudflared tunnel --url http://localhost:8501
```

`cloudflared` prints a URL like `https://<random-words>.trycloudflare.com`. Open it on any phone. The link lasts while the command runs. Quick tunnels are meant for testing, so start a fresh one before the demo and keep the terminal open.

`ngrok http 8501` works too but needs a free ngrok account and auth token.

## Keep it running

```bash
docker compose up -d                                   # Qdrant restarts automatically
nohup streamlit run app/streamlit_app.py --server.port 8501 > logs/streamlit.log 2>&1 &
nohup cloudflared tunnel --url http://localhost:8501 > logs/tunnel.log 2>&1 &
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' logs/tunnel.log
```

## Demo script (5 minutes)

1. Qdrant dashboard: show the `nexacore_docs` collection and one point's payload (department, status, access_key).
2. Phone: open the tunnel URL as **Employee**, All departments. Ask "What is the process for onboarding a new vendor?" and point out the four departments in the answer.
3. Ask "Who approves a purchase of INR 3,00,000?" (table row retrieval).
4. Ask "What is the deadline for submitting expense claims?" (conflict between HR and Finance).
5. Ask about NDA confidentiality as **Employee** (restricted message), then switch role to **Legal Counsel** (answered).
6. Turn on "Include superseded versions", choose HR, ask what changed between the 2025 and 2026 leave policies.
7. Ask about international sabbaticals (not found).
8. Show `logs/audit.jsonl` and `evaluation/results/`.
