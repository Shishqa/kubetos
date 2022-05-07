# KUBETOS <img src="https://i.pinimg.com/originals/7a/18/32/7a1832f436598f9ff9c557783a4ca7d0.png" width="30">

A TOSCA framework for deploying Kubernetes.

> Work in progress

## Getting started

1. Create a python [`virtualenv`](https://virtualenv.pypa.io/en/latest/)
and install required packages. Also install [`cfssl`](https://github.com/cloudflare/cfssl).

```bash
pip install -r requirements.txt
sudo apt install golang-cfssl
```

2. Get your openstack RC file and source it (it is convenient to put it inside `configs` folder).
3. Edit [`configs/opera.sh`](./configs/opera.sh) and source it.

```bash
source configs/cloud.rc
source configs/opera.sh
```

4. Edit [`service.yaml`](./service.yaml) topology template (__TODO:__ use topology template inputs) and deploy it with [Opera](https://github.com/xlab-si/xopera-opera) orchestrator

```bash
opera deploy service.yaml
```
