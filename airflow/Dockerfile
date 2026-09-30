FROM apache/airflow:2.10.5-python3.12

COPY requirements.txt /tmp/requirements.txt
# Deliberately installed without Airflow's constraints file. The 2.10.5 / py3.12
# constraints pin pandas==2.1.4 and pyarrow==19.0.0, which conflict with the
# pandas>=2.2 and snowflake-connector-python[pandas] requirements below, so
# applying them fails the build. Pin exact versions in a lockfile instead.
USER root
RUN pip install --no-cache-dir -r /tmp/requirements.txt
USER airflow