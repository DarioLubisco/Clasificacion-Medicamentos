FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

RUN pip install --no-cache-dir scrapling[all] curl_cffi playwright browserforge fastapi uvicorn pydantic cloakbrowser
RUN python -m cloakbrowser install

COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
