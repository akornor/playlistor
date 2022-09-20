FROM python:3.8

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /app/

COPY requirements/dev.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements/dev.txt

COPY . /app/

EXPOSE 8000
