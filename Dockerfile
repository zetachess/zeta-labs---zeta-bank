FROM python:3.12-alpine

# Usuario sin privilegios
RUN adduser -D -H lab
WORKDIR /app
COPY app/zetabank.py /app/zetabank.py

ENV HOST=0.0.0.0 PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
USER lab
CMD ["python", "/app/zetabank.py"]
