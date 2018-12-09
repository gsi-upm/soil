FROM python:3.7

WORKDIR /usr/src/app

COPY test-requirements.txt requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r test-requirements.txt -r requirements.txt

COPY ./ /usr/src/app

RUN pip install '.[web]'

ENTRYPOINT ["python", "-m", "soil"]
