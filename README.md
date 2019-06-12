# SelfStabilizingReconfiguration
This repository contains a distributed system implementing self-stabilizing reconfiguration, as described by [Dolev, Georgiou, Marcoullis and Schiller](https://arxiv.org/abs/1606.00195). This repository is intended to be used together with [Thor](), which is used to boot up the system with all intended configuration.

## Set up
First, make sure that you have [Python 3.7.2](https://www.python.org/downloads/release/python-372/) installed. Then, follow the commands below.

```
python3.7 -m venv env
source ./env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
chmod +x ./scripts/*
```

Instructions for how to run this application without using [Thor](https://github.com/practicalbft/thor) (which you should not, since Thor was built for this exact use case) may (most probably no) be added later.

### Linting
The code base is linted using [flake8](https://pypi.org/project/flake8/) with [pydocstyle](https://github.com/PyCQA/pydocstyle), so make sure to lint the code by running `flake8` before pushing any code.

### Testing
[unittest](https://docs.python.org/2/library/unittest.html) is setup so add appropriate unit tests in the `tests/unit_tests` folder (make sure the file starts with `test_`) and appropriate integration tests in the `tests/integration_tests` folder. Tests can run as seen below.

```
./scripts/test              # runs all tests
./scripts/test unit         # runs only unit tests
./scripts/test it           # runs only integration tests
./scripts/test <pattern>    # runs all test files with a filename matching pattern
```

### Travis integration
Unit testing is setup to be run for all Pull Requests and on each push to master by Travis.

## System description

### Ports
Each running node uses three ports: one for the API (default to `400{node_id}`), one for the main communication channel running over TCP with other nodes (`500{node_id}`), one for exposing metrics to the Prometheus scraper (`300{node_id}`) and lastly one for the self-stabilizing UDP communication channel (`700{node_id}`). Node with id `1` would therefore be using ports `3001`, `4001`, `5001` and `7001` for example. Note that port ranges `7000-->` was selected rather than `6000-->` since many firewalls on PlanetLab block port `6000` from being used.

| Port number   | Service                           | 
| ------------- |:---------------------------------:|
| 300{ID}       | Prometheus metrics endpoint       |
| 400{ID}       | REST API                          |
| 500{ID}       | TCP Inter-node communication      |
| 700{ID}       | UDP Inter-node communication      |