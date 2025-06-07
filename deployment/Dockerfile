FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src ./src
COPY tailwind.config.js ./


WORKDIR /usr/src/app/src

CMD [ "python", "./app.py" ]