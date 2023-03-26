
<h1 align="center">Futuresboard</h1>
<p align="center">
A python (3.11+) based scraper and dashboard to monitor the performance of your cryptocurrency Futures accounts.<br>
</p>
<p align="center">
<img alt="GitHub Pipenv locked Python version" src="https://img.shields.io/github/pipenv/locked/python-version/ecoppen/futuresboard"> 
<a href="https://github.com/ecoppen/futuresboard/blob/main/LICENSE"><img alt="License: GPL v3" src="https://img.shields.io/badge/License-GPLv3-blue.svg">
<a href="https://app.fossa.com/projects/git%2Bgithub.com%2Fecoppen%2Ffuturesboard?ref=badge_shield"><img alt="FOSSA Status" src="https://app.fossa.com/api/projects/git%2Bgithub.com%2Fecoppen%2Ffreqdash.svg?type=shield"></a>
<a href="https://codecov.io/gh/ecoppen/futuresboard"><img src="https://codecov.io/gh/ecoppen/futuresboard/branch/main/graph/badge.svg?token=3G8Y52J9E9"/></a>
<a href="https://codeclimate.com/github/ecoppen/futuresboard/maintainability"><img src="https://api.codeclimate.com/v1/badges/ee2153da0bf153eb80bb/maintainability"/></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

### Exchange support
| Exchange | Direct data | Trading history | News |
|:--------:|:-----------:|:---------------:|:----:|
| Binance  |      ✅      |        ✅        |   ✅  |
| Bitget   |      ➖      |        ➖        |   ➖  |
| Bybit    |      ✅      |        ✅        |   ✅  |
| Okx      |      ✅      |        ❌        |   ✅  |

## Quickstart

- Clone the repo `git clone https://github.com/ecoppen/futuresboard.git`
- Navigate to the repo root `cd futuresboard`
- Navigate to the config folder `cd config`
- Create the config file from template `cp config.example.json config.json`
- Populate the `config.json` files as required using a text editor e.g. `nano config.json`
- Navigate back to the repo root `cd ..`
- Install pipenv `pip install pipenv`
- Install required packages `pipenv install`
- Activate the environment `pipenv shell`
- Start the webserver `uvicorn futuresboard.main:app`
- You can add `--host "0.0.0.0"` and/or `--port 5050` if you don't want to serve to `127.0.0.1:8000`

### Developers
- Install developer requirements from pipenv `pipenv install --dev`
- Install pre-commit hooks `pre-commit install`
- Start the webserver in development mode `uvicorn futuresboard.main:app --reload`

### Screenshots
<img width="600" alt="image" src="https://user-images.githubusercontent.com/51025241/227767373-95afac03-27b2-4a19-ac1b-92d748d702eb.png">

<img width="600" alt="image" src="https://user-images.githubusercontent.com/51025241/227767401-e3cb86b6-e9d6-44bf-955e-dcc64e6d414e.png">

<img width="600" alt="image" src="https://user-images.githubusercontent.com/51025241/227767495-196a0f16-feab-4af2-93dd-31f3b6e73bfe.png">

## License
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fecoppen%2Ffuturesboard.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fecoppen%2Ffuturesboard?ref=badge_large)
