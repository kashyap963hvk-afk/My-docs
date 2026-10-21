"""Airflow DAG: every day at 02:00 UTC, load the newest arXiv papers into QueryMesh."""
from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag

PROJECT = "/home/ubuntu/querymesh"
TOPICS = {
    "rag": "cat:cs.CL AND abs:retrieval",
    "agents": "cat:cs.AI AND abs:agent",
}


@dag(
    dag_id="querymesh_ingest",
    schedule="0 2 * * *",
    start_date=datetime(2026, 10, 1),
    catchup=False,
    tags=["querymesh"],
)
def querymesh_ingest():
    previous = None
    for name, query in TOPICS.items():
        task = BashOperator(
            task_id=f"ingest_{name}",
            bash_command=(
                f"cd {PROJECT} && .venv/bin/python -m querymesh.ingest "
                f"--query '{query}' --max-papers 10"
            ),
            retries=2,
        )
        if previous:
            previous >> task  # one topic after the other: arXiv allows 1 request per 3 seconds
        previous = task


querymesh_ingest()
