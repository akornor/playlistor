FROM python:3.8

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /app/

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app/

EXPOSE 8000