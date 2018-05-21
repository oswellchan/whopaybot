FROM python:3
RUN mkdir /app
RUN mkdir /logs
WORKDIR /app
ADD requirements.txt /app/
RUN pip install -r requirements.txt
ADD src/ /app/
