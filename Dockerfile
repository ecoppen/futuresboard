FROM python:3.8-buster

WORKDIR /usr/src
RUN git clone https://github.com/ecoppen/futuresboard.git
WORKDIR /usr/src/futuresboard
RUN python -m pip install .

CMD futuresboard