# Upgrade to Python 3.11 to fix numpy/pandas binary mismatch
FROM python:3.11-slim

ENV PYTHONUNBUFFERED True

ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Upgrade pip first to ensure it handles wheels correctly
RUN pip install --upgrade pip

RUN pip install --no-cache-dir -r requirements.txt

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
