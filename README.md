# WynnVentory 🎒

Welcome to WynnVentory, your ultimate tool for managing and keeping track of your Wynncraft items! Below you'll find the
necessary setup steps, links, and API documentation to get you started.

## 🗄️ MongoDB

To interact with the database, you'll need MongoDB Compass. Follow the steps below:

1. Download [MongoDB Compass](https://www.mongodb.com/products/tools/compass)
2. Request a MongoDB user on [Discord](https://discord.gg/b6ATfrePuR)
2. Connect to the database using the following URI:
   `mongodb+srv://<user>:<password>@wynnventory.9axarep.mongodb.net/`

## 🔗 API Endpoints

**API v2** (standardized, recommended for new integrations):
[docs/API_V2.md](docs/API_V2.md) · [OpenAPI spec](docs/openapi_v2.yaml) · [v1 → v2 migration guide](docs/API_V2_MIGRATION.md)

Legacy v1 endpoints ([docs/API.md](docs/API.md)) remain available; Postman documentation:
[API Endpoints](https://documenter.getpostman.com/view/30826165/2sB2j69qVC)

## 🌐 Website

Visit the live site to see WynnVentory in action:
[wynnventory.com](https://www.wynnventory.com/)

## *</>* Setup

- Create .env in root of the project
- Paste the following code into .env

```
ENVIRONMENT=dev
MIN_SUPPORTED_VERSION=1.0.0
PROD_MONGO_URI=mongodb+srv://<user>:<password>@wynnventory.9axarep.mongodb.net/wynnventory
DEV_MONGO_URI=mongodb+srv://<user>:<password>@wynnventory.9axarep.mongodb.net/wynnventory_DEV
ADMIN_MONGO_URI=mongodb+srv://<user>:<password>@wynnventory.9axarep.mongodb.net/wynnventory_admin
```

## Wynnventory Mod

https://github.com/Wynnventory/WynnVentory_Mod
