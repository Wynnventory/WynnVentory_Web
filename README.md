# WynnVentory 🎒
Welcome to WynnVentory, your ultimate tool for managing and keeping track of your Wynncraft items! Below you'll find the necessary setup steps, links, and API documentation to get you started.

## 🗄️ MongoDB
To interact with the database, you'll need MongoDB Compass. Follow the steps below:

1. Download [MongoDB Compass](https://www.mongodb.com/products/tools/compass)
2. Request a MongoDB user on [Discord](https://discord.gg/b6ATfrePuR)
2. Connect to the database using the following URI:
`mongodb+srv://<user>:<password>@wynnventory.9axarep.mongodb.net/`

## 🔗 API Endpoints
Explore and interact with the API using the detailed documentation provided by Postman:
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
https://github.com/Aruloci/WynnVentory
