FROM python:3.14-slim
RUN pip install --upgrade pip

WORKDIR /

RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY api ./api
COPY core ./core
COPY main.py .
COPY schemas.py .
COPY config.py .
COPY .env .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

