FROM python:3.11-slim
MAINTAINER Daniel Lassahn <daniel.lassahn@meteointelligence.de>

RUN apt-get update && apt-get install -y gcc g++ build-essential

COPY ./requirements.txt /opt/requirements.txt
RUN pip install -r /opt/requirements.txt

ENV PYTHONPATH "/:/app"
ENV PYTHONUNBUFFERED 1
WORKDIR /app
COPY entrypoint.sh /
COPY . .

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8050", "zarr_browser.app:server"]
