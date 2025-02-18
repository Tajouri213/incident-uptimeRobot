FROM python:3.8-slim-buster

WORKDIR /docker

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY get_username.py /docker/
COPY create_incident.py /docker/app.py

EXPOSE 5000

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0" ]