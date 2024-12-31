FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8766

ENV IS_DOCKER=1

CMD ["python", "__main__.py"]