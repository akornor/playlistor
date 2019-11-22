FROM python:3.7.5

ENV PYTHONUNBUFFERED 1

WORKDIR /app/

COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt

COPY . /app/

EXPOSE 8000