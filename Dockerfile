FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/paymentguard
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home paymentguard
COPY --chown=paymentguard:paymentguard . .
RUN mkdir -p data/workspaces && chown -R paymentguard:paymentguard data
USER paymentguard
EXPOSE 8000 8501
CMD ["python", "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
