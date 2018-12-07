FROM python:3.4-onbuild

RUN pip install '.[web]'

ENTRYPOINT ["python", "-m", "soil"]
