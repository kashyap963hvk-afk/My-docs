# QueryMesh lab manual - writing spec (shared by every writer)

## Output
One source file per Google Docs tab, in `QUERYMESH/manual/`, written in the .qm format that
`manual/build_doc.py` reads (see its docstring). Check each file builds with:
`python3 manual/build_doc.py manual/NN_name.qm t.test /tmp/claude-0/-home-user-My-docs/de92a962-a4e9-5edf-ac96-92930df3348e/scratchpad/check_NN`

| File | Tab title | Tab id |
|---|---|---|
| 00_querymesh.qm | Querymesh (parent) | t.pyot26g4fal8 |
| 01_part2a.qm | QM Part 2A - Hyperstack + VS Code + WinSCP | t.5i7aapc10l57 |
| 02_part2b.qm | QM Part 2B - Project + Tools + FakeCloud | t.m62rx15ptjnk |
| 03_part3.qm | QM Part 3 - Core Idea | t.iji8ocum6ele |
| 04_part4.qm | QM Part 4 - Ingestion + Hybrid Search | t.qvpb00nonwua |
| 05_part5.qm | QM Part 5 - Agentic RAG + Supervisor | t.2y3850z5kt1r |
| 06_part6a.qm | QM Part 6A - MCP + A2A + Tracing + UIs | t.rlb8iiodu1v9 |
| 07_part6b.qm | QM Part 6B - Docker + EKS + CI/CD | t.xt7i5anju3q7 |
| 08_part7.qm | QM Part 7 - Elite | t.mandofw0m68g |
| 09_reference.qm | QM Parts 8-14 - Reference | t.la7nqmf29vfq |

## .qm syntax reminders
- One paragraph per line. Blank lines are ignored.
- `#` Part title (once per tab, first line), `##` SECTION, `###` sub-heading.
- Code/commands/file contents go in ``` fences (copied exactly, grey box). Never put `$` or a prompt in them.
- Include a project file with `@code path/relative/to/QUERYMESH` (e.g. `@code querymesh/graph.py`). Never retype project code.
- Tables: `§ a § b § c` rows, first row is the header. Put `!blue` on the line before a FakeCloud/AWS table:
  header `§ Step § FakeCloud (free practice) § Real AWS (same step)`. The last column is painted light blue.
- Inside cells use `\n` for a new line and backticks for commands. No `§` inside text.
- Inline: `**bold**`, backticks for short commands/names. Avoid unmatched backticks or `**`.
- Labels are bolded automatically at the start of a line: `WHERE:` `GOAL:` `Step 1.` `You should see:` `Watch out:` `CHECKPOINT:` `If not:`.
- ASCII only where possible (no emoji). Use straight quotes.

## Hand-holding style (apply to EVERY practical section)
`## SECTION 4.3 - Create querymesh/ingest.py` then `WHERE: ...` then `GOAL: ...`, numbered `Step N.` with ONE action each,
exact input in a code fence, `You should see:` after non-obvious steps, `Watch out:` where people go wrong,
`If you see... | It means... | Do this next` tables for branches, `CHECKPOINT:` + `If not:` at the end of each section.
Placeholders in CAPITALS with a `Placeholder | Replace with | Example` table. Settings screens get `Field | Value | Why`.
After every @code file: a table `Line(s) | What it does (plain English)` explaining EVERY non-obvious line, in easy words.
Each Part 4-7 starts with "What, why, when" (3-5 lines) and ends with "Common mistake at this level".
Never write "configure as needed" or skip steps. Spoon-feed. Write for a smart beginner on Windows 11.

## Fixed facts (use exactly these)
- Laptop: Windows 11, PowerShell, VS Code + "Remote - SSH" extension, WinSCP.
- GPU: Hyperstack, flavor n3-RTX-A6000x1 (1x RTX A6000 48 GB), about US$0.50/h [1]. Image "Ubuntu Server 24.04 LTS R570 CUDA 12.8 with Docker" (Docker + NVIDIA toolkit preinstalled, user `ubuntu` in docker group) [4]. Environment `querymesh-env`, key `querymesh-key`, VM name `querymesh-gpu`. SHUTOFF still bills; HIBERNATE stops GPU billing; delete stops all [3]. Ports other than 22 are closed unless you add a firewall rule [5].
- Everything runs on the VM in `/home/ubuntu/querymesh` (= `~/querymesh`). You open UIs from the laptop with VS Code PORTS tab port forwarding (no firewall change needed).
- Ports: vLLM 8000, Airflow 8080, OpenSearch 9200 (bound to 127.0.0.1 and docker0 172.17.0.1 only), FakeCloud 4566, agents retriever 8101 / grader 8102 / writer 8103 / critic 8104 / scout 8105, API 8090, Gradio 7860.
- Python 3.12 via uv (`uv venv -p 3.12 .venv`, then `source .venv/bin/activate`, `uv pip install -e ".[dev,ingest]"`).
- LLM: vLLM docker image `vllm/vllm-openai:v0.32.0` (verify tag) serving `Qwen/Qwen3-4B-Instruct-2507` (Apache-2.0, non-thinking) as model name `qwen3-4b`, with `--api-key` (scripts/start_vllm.sh).
- OpenSearch 3.9.0 docker (scripts/start_opensearch.sh), security plugin disabled because it is only reachable locally. Hybrid query + `score-ranker-processor` RRF (OpenSearch >= 2.19) [14][15].
- Embeddings: Jina API `https://api.jina.ai/v1/embeddings`, model `jina-embeddings-v5-text-small`, 1024 dims, tasks `retrieval.passage` / `retrieval.query`; new keys get 10M free tokens [17][18]. If the API rejects the task name, set `EMBED_MODEL=jina-embeddings-v3` (also 1024 dims).
- Cache: Upstash Redis free tier: 1 database, 250 MB data, 500K commands per month, 10 GB bandwidth [28]. URL form `rediss://default:TOKEN@ENDPOINT:6379`.
- Logfire: free Personal plan, 10M spans+logs+metrics per month, token env `LOGFIRE_TOKEN` (Project > Settings > Write tokens > New write token) [26]. MCP needs no extra instrumentation (mcp 2 emits spans itself).
- Langfuse Cloud Hobby: free, 50k units/month, 30 days, 2 users. Env `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL=https://cloud.langfuse.com` (EU) or `https://us.cloud.langfuse.com` [27].
- FakeCloud v0.51.0: `curl -fsSL https://fakecloud.dev/install.sh | bash -s -- --version v0.51.0`, start `nohup fakecloud --storage-mode persistent --data-path ~/fakecloud-data > ~/fakecloud.log 2>&1 &`, health `curl -s localhost:4566/_fakecloud/health`, account 123456789012, any keys (`test`) [6][7]. Supports ECR (real docker push to `localhost:4566/REPO`), S3, IAM, STS, Secrets Manager, ELBv2, Logs. EKS is control-plane only: `aws eks create-cluster` stores metadata, there is NO Kubernetes API, so we use kind as the real local cluster [8][9].
- Switch target: `source scripts/use_fakecloud.sh` / `source scripts/use_aws.sh`. Python ingestion reads the AWS_ lines in .env.
- kind v0.33.0, kubectl v1.37.1, Helm v4.3.1 [32][33][34]. OpenSearch Helm chart 3.9.0 with deploy/k8s/opensearch-values.yaml [35].
- AWS: region us-east-1. EKS control plane US$0.10/h [36]; t3.large US$0.0832/h; NAT gateway US$0.045/h + data; ALB US$0.0225/h + LCU; Secrets Manager US$0.40/secret/month; ECR US$0.10/GB-month [41]. eksctl v0.231.0, cluster file deploy/aws/eksctl-cluster.yaml (K8s 1.35) [37]. AWS Load Balancer Controller chart from `https://aws.github.io/eks-charts` (v3.6.x), IAM via eksctl pod identity `wellKnownPolicies.awsLoadBalancerController` [38]. External Secrets Operator chart 2.13.0 from `https://charts.external-secrets.io`, API `external-secrets.io/v1`, ClusterSecretStore with Pod Identity (no auth block) [39]. GitHub OIDC provider `https://token.actions.githubusercontent.com`, audience `sts.amazonaws.com`, no thumbprint needed [40]. Repos created after 2026-07-15 may use immutable `sub` claims (`repo:OWNER@ID/REPO@ID:...`), adjust the trust policy if the role cannot be assumed.
- Actions versions: actions/checkout@v7, astral-sh/setup-uv@v7, aws-actions/configure-aws-credentials@v6, aws-actions/amazon-ecr-login@v2, docker/setup-buildx-action@v4, docker/build-push-action@v7.
- Airflow 3.3.2 standalone in its own venv `~/airflow-venv`, `AIRFLOW_HOME=~/airflow`, `~/airflow/dags` is a symlink to `~/querymesh/dags`, login user `admin`, password in `~/airflow/simple_auth_manager_passwords.json.generated`, UI on 8080 [13]. Install: `uv pip install "apache-airflow==3.3.2" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.3.2/constraints-3.12.txt"`.
- arXiv API: max 1 request every 3 seconds; the `arxiv` 4.0.1 client already waits 3 s [10][11]. arxiv 4 has no download method, we download pdf_url with httpx.
- Docling 2.141.0 (`do_ocr=False`), downloads layout models from Hugging Face on first run (a few hundred MB) [12].
- Library versions are pinned in pyproject.toml (langgraph 1.2.16, fastmcp 4.1.3, a2a-sdk 1.2.3 = A2A spec 1.0, etc.).
- Tests: `pytest -q` prints `10 passed`.
- Verified while writing: the 3 graph routing tests, the API/JWT tests, the chunker tests pass; the 5 agents ran as real servers and the supervisor reached them over MCP/SSE, discovered them via Agent Cards, and the retriever delegated to the scout over A2A; the LLM skills parsed structured output from an OpenAI-compatible server. NOT run in our sandbox (no GPU/internet to these hosts): real vLLM, OpenSearch, Jina, arXiv, Docker builds, kind, EKS. Say "tested" only for the first group.

## Section outline (use these numbers for cross-references)
- 00 Querymesh tab: title; assumptions line; WHERE TO FIND WHAT table; PROJECT MAP table (each of the 11 resume lines -> tab + section); labels table; PART 0 (0.1 what it is, 0.2 journey + Part/What/Time table, 0.3 outcomes, 0.4 every place you work + one-line flow, 0.5 what each piece does, 0.6 cost); PART 1 (1.1 checklist MUST/NICE, 1.2 refreshers + 1-minute checks, 1.3 accounts table, 1.4 what you install where).
- 2A: 2A.1 VS Code, 2A.2 Remote-SSH extension, 2A.3 Hyperstack account + credit, 2A.4 SSH key, 2A.5 environment, 2A.6 import key, 2A.7 deploy VM (every field), 2A.8 ACTIVE + IP, 2A.9 first SSH from PowerShell, 2A.10 VS Code Remote-SSH, 2A.11 WinSCP, 2A.12 port forwarding (PORTS tab), 2A.13 hibernate/restore/delete, 2A.14 troubleshooting.
- 2B: 2B.1 folders, 2B.2 open in VS Code, 2B.3 THE procedure to create any file, 2B.4 system tools + tmux, 2B.5 uv, 2B.6 pyproject.toml + querymesh/__init__.py, 2B.7 venv + install, 2B.8 .env + config.py (generate JWT_SECRET, LLM_API_KEY, API_PASSWORD), 2B.9 GPU + Docker test, 2B.10 vLLM (scripts/start_vllm.sh), 2B.11 OpenSearch (scripts/start_opensearch.sh), 2B.12 FakeCloud + AWS CLI + switch scripts (blue table), 2B.13 Git + GitHub repo `querymesh`, 2B.14 Part 2 result check.
- 3: 3.0 analogy, 3.1 vectors/embeddings, 3.2 BM25, 3.3 hybrid + RRF worked example, 3.4 chunking, 3.5 RAG vs agentic RAG loop, 3.6 LangGraph state/nodes/edges/Command, 3.7 supervisor + 5 agents, 3.8 MCP vs A2A + SSE, 3.9 Agent Cards + discovery + peer delegation, 3.10 SHA-256 exact-match cache, 3.11 spans vs token traces, 3.12 JWT, 3.13 containers/Kubernetes/Helm/ALB/ESO, 3.14 FakeCloud vs AWS.
- 4 (resume lines 3, 4): 4.0 what/why/when, 4.1 embeddings.py, 4.2 search.py + setup, 4.3 ingest.py, 4.4 S3 bucket for PDFs (blue table), 4.5 first ingestion, 4.6 hybrid search test, 4.7 look inside OpenSearch, 4.8 Airflow install + DAG + run, 4.9 common mistake, Part 4 result check.
- 5 (lines 2, 5, 8): 5.0, 5.1 observability.py, 5.2 llm.py, 5.3 skills.py (+ try each skill), 5.4 graph.py, 5.5 run the graph, 5.6 watch the retry/scout loop, 5.7 tests/test_graph.py + pytest, 5.8 Upstash database, 5.9 cache.py + prove it, 5.10 common mistake, result check.
- 6A (lines 6, 7, 9, part of 11): 6A.0, 6A.1 discovery.py, 6A.2 agents.py, 6A.3 start the five agents (tmux) + check cards/MCP/A2A, 6A.4 supervisor in remote mode, 6A.5 Logfire, 6A.6 Langfuse, 6A.7 auth.py + api.py + curl tests, 6A.8 tests/test_api.py + tests/test_ingest.py, 6A.9 api_client.py + ui_gradio.py, 6A.10 Telegram bot, 6A.11 common mistake, result check.
- 6B (lines 10, 11): 6B.0, 6B.1 Dockerfile + .dockerignore + build, 6B.2 docker-compose.yml, 6B.3 kind/kubectl/helm, 6B.4 kind cluster, 6B.5 registry + push (blue), 6B.6 secrets in Secrets Manager (blue), 6B.7 the cluster (blue: FakeCloud eks create-cluster + kind / eksctl), 6B.8 OpenSearch on the cluster, 6B.9 secrets into the cluster (blue: kubectl create secret / ESO), 6B.10 load balancer (blue: port-forward / ALB controller), 6B.11 the Helm chart files, 6B.12 helm install (blue), 6B.13 test + first ingestion job, 6B.14 CI/CD GitHub Actions (blue for OIDC/IAM), 6B.15 teardown (blue), 6B.16 common mistake, result check.
- 7: 7.0 who defines the top level, 7.1 evaluate.py, 7.2 build test set, 7.3 BM25 vs vector vs hybrid, 7.4 end-to-end metrics, 7.5 tuning experiments, 7.6 production hardening checklist, 7.7 common mistake.
- 09 Reference: PART 8 tools map, PART 9 keep it working, PART 10 troubleshooting, PART 11 projects, PART 12 cheat sheet, PART 13 self-test, PART 14 sources, ANSWER KEY.

## Sources (use these numbers everywhere)
[1] Hyperstack GPU pricing https://www.hyperstack.cloud/gpu-pricing
[2] Hyperstack getting started https://docs.hyperstack.cloud/docs/getting-started/
[3] Hyperstack VM states and billing https://docs.hyperstack.cloud/docs/billing/states-and-billing/
[4] Hyperstack Docker-ready images https://docs.hyperstack.cloud/docs/tutorials/docker-support/
[5] Hyperstack firewalls https://docs.hyperstack.cloud/docs/network/firewalls/
[6] FakeCloud https://fakecloud.dev and https://github.com/faiscadev/fakecloud
[7] FakeCloud install https://fakecloud.dev/docs/getting-started/install/
[8] FakeCloud EKS https://fakecloud.dev/docs/services/eks/
[9] FakeCloud ECR https://fakecloud.dev/docs/services/ecr/
[10] arXiv API manual and terms https://info.arxiv.org/help/api/user-manual.html , https://info.arxiv.org/help/api/tou.html
[11] arxiv Python package https://pypi.org/project/arxiv/
[12] Docling https://github.com/docling-project/docling
[13] Apache Airflow quick start https://airflow.apache.org/docs/apache-airflow/stable/start.html
[14] OpenSearch hybrid query https://docs.opensearch.org/latest/query-dsl/compound/hybrid/
[15] OpenSearch score ranker processor (RRF) https://docs.opensearch.org/latest/search-plugins/search-pipelines/score-ranker-processor/
[16] OpenSearch Docker https://docs.opensearch.org/latest/install-and-configure/install-opensearch/docker/
[17] Jina embeddings API https://jina.ai/embeddings/ , https://api.jina.ai/redoc
[18] jina-embeddings-v5-text-small https://jina.ai/models/jina-embeddings-v5-text-small/
[19] RRF paper (Cormack, Clarke, Buettcher, SIGIR 2009) https://dl.acm.org/doi/10.1145/1571941.1572114
[20] LangGraph https://docs.langchain.com/oss/python/langgraph/overview , https://github.com/langchain-ai/langgraph
[21] vLLM https://docs.vllm.ai
[22] Qwen3-4B-Instruct-2507 https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507
[23] FastMCP https://gofastmcp.com
[24] Model Context Protocol https://modelcontextprotocol.io
[25] A2A protocol https://a2a-protocol.org , https://github.com/a2aproject/a2a-python
[26] Pydantic Logfire https://logfire.pydantic.dev/docs/ , pricing https://pydantic.dev/pricing
[27] Langfuse https://langfuse.com/docs , pricing https://langfuse.com/pricing
[28] Upstash Redis https://upstash.com/docs/redis , pricing https://upstash.com/pricing/redis
[29] Gradio https://www.gradio.app/docs
[30] python-telegram-bot https://docs.python-telegram-bot.org , BotFather https://core.telegram.org/bots/tutorial
[31] PyJWT https://pyjwt.readthedocs.io , FastAPI OAuth2 + JWT https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
[32] kind https://kind.sigs.k8s.io/docs/user/quick-start/
[33] kubectl https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/
[34] Helm https://helm.sh/docs/intro/install/
[35] OpenSearch Helm charts https://github.com/opensearch-project/helm-charts
[36] Amazon EKS pricing https://aws.amazon.com/eks/pricing/
[37] eksctl https://eksctl.io/installation/
[38] AWS Load Balancer Controller https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/deploy/installation/
[39] External Secrets Operator (AWS Secrets Manager) https://external-secrets.io/latest/provider/aws-secrets-manager/
[40] GitHub OIDC in AWS https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws , https://github.com/aws-actions/configure-aws-credentials
[41] AWS pricing pages https://aws.amazon.com/ec2/pricing/on-demand/ , https://aws.amazon.com/vpc/pricing/ , https://aws.amazon.com/elasticloadbalancing/pricing/ , https://aws.amazon.com/secrets-manager/pricing/ , https://aws.amazon.com/ecr/pricing/
[42] uv https://docs.astral.sh/uv/
[43] VS Code Remote-SSH https://code.visualstudio.com/docs/remote/ssh , WinSCP https://winscp.net/eng/docs/start
[44] AWS CLI v2 install https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
[45] Papers: Self-RAG https://arxiv.org/abs/2310.11511 , Corrective RAG https://arxiv.org/abs/2401.15884 , RAGAS https://arxiv.org/abs/2309.15217 , ARES https://arxiv.org/abs/2311.09476 , Lost in the Middle https://arxiv.org/abs/2307.03172 , ColBERTv2 https://arxiv.org/abs/2112.01488
[46] Anthropic: Building effective agents https://www.anthropic.com/engineering/building-effective-agents , Contextual retrieval https://www.anthropic.com/news/contextual-retrieval
