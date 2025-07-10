FROM apache/airflow:2.9.1-python3.9

USER root
COPY ../requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
USER airflow
