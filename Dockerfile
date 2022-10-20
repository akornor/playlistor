FROM python:3.8

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /app/

COPY . /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements/dev.txt

EXPOSE 8000
