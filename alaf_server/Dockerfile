FROM ubuntu:18.10
RUN apt-get update && apt-get install -y python3 python3-dev python3-pip
RUN apt-get update && apt-get install -y sqlite


WORKDIR /app
COPY app/ /app/app/


COPY requirements.txt /app
RUN pip3 install -r requirements.txt
RUN pip3 install gunicorn eventlet

EXPOSE 5000

COPY run.py config.py /app/

CMD gunicorn -b 0.0.0.0:5000 --worker-class eventlet -w 1 --timeout 30 --access-logfile - "run:app"

#docker run -d -v db:/app/db -p 80:5000 alaf:latest
