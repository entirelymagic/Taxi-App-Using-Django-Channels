# Uber-App-Using-Django-Channels

> Using test-driven development, we'll write and test the server-side code powered by Django and Django Channels. Part 2: We'll set up the client-side Angular app along with authentication and authorization. Also, we'll streamline the development workflow by adding Docker. Part 3: Finally, we'll walk through the process of creating the app UI with Angular.

Our server-side application uses:

Python (v3.9)
Django (v4.0)
Django Channels (v3.0)
Django REST Framework (v3.13)
pytest (v6.2)
Redis (v6.2)
PostgreSQL (v14.1)
Client-side:

Node.js (v16.13)
Angular (v13.0)
Reverse-proxy:

Nginx (v1.21)
We'll also use Docker v20.10.11.

Steps:

- This downloads the official Postgres Docker image from Docker Hub and runs it on port 5435(5432 is used by Local)in the background. It also sets up a database with the user, password, and database name all set to taxi.

`docker run --name some-postgres -p 5435:5435 -e POSTGRES_USER=taxi -e POSTGRES_DB=taxi -e POSTGRES_PASSWORD=taxi -d postgres`

- Next, spin up Redis on port 6379:

`docker run --name some-redis -p 6379:6379 -d redis`

- To test if redis is up and running

`$ docker exec -it some-redis redis-cli ping`

`PONG`
