FROM python:3.10
COPY . /app
WORKDIR /app
RUN python3 -m pip install --upgrade pip
RUN pip install -r requirements.txt
CMD python3 main.py
