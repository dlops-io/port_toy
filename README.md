# Port Toy App

![Flow: browser → gateway → processor](browser-gateway-processor.png)

Your browser sends text to a **gateway**. The gateway forwards it to a **processor**. The processor converts the text to CAPITALS and sends it back.

The text conversion is simple. The goal is to understand how the containers communicate and which ports they use.

## What you’ll learn

You’ll run the app in four steps:

1. **Set it up by hand.** Create a network, build the images, and start both containers.
2. **Check the ports.** See which service your laptop can reach.
3. **Change the ports.** Change the settings without editing Python.
4. **Use Compose.** Run the same app from one configuration file.



## Prerequisites

Complete [Tutorial 0: Setup & Installs](https://github.com/dlops-io/ac215-setup) first.

You only need Docker Desktop. You do not need a GCP account or Python installed on your laptop.

Make sure Docker Desktop is running:

```bash
docker run hello-world
```



## Contents

- [Step 1: Set up the network by hand](#step-1-set-up-the-network-by-hand)
- [Step 2: Check the ports](#step-2-check-the-ports)
- [Step 3: Change the ports](#step-3-change-the-ports)
- [Step 4: Run with Compose](#step-4-run-with-compose)
- [Port and networking cheat sheet](#port-and-networking-cheat-sheet)



## How the app works

The app has two containers:

- **Gateway:** serves the web page and forwards your text.
- **Processor:** converts the text to capitals and returns it.

```text
Browser → localhost:8090 → Gateway → processor:9200 → Processor
```

Port `8090` is published on your laptop. The gateway listens on port `9100` inside its container. The processor listens on port `9200` inside its container.

The project contains:

```text
port_toy/
├── docker-compose.yml   # Used in Step 4
├── gateway/
│   ├── Dockerfile       # Builds the gateway image
│   ├── gateway.py       # Serves the page and forwards requests
│   └── index.html      # The web page
└── processor/
    ├── Dockerfile       # Builds the processor image
    └── processor.py     # Converts text to capitals
```

---



## Step 1: Set up the network by hand

First, run the app without Compose. You’ll create the network, build the images, and start the containers yourself.

### Get the code

Clone or download the [repository](https://github.com/dlops-io/port_toy). Then open a terminal in the project folder:

```bash
cd port_toy
```



### Create the network

```bash
docker network create toynet
```

Both containers will join this network.

### Build the images

```bash
docker build -t toy-processor ./processor
docker build -t toy-gateway ./gateway
```



### Start the processor

```bash
docker run -d --name processor --network toynet \
  -e PORT=9200 toy-processor
```

There is no `-p` flag. The processor listens on port `9200`, but that port is not published on your laptop.

Other containers on `toynet` can reach it.

### Start the gateway

```bash
docker run -d --name gateway --network toynet \
  -p 127.0.0.1:8090:9100 \
  -e PROCESSOR_HOST=processor \
  -e PROCESSOR_PORT=9200 \
  toy-gateway
```

The gateway joins the same network. It forwards your laptop’s port `8090` to port `9100` inside the container.

Check the logs:

```bash
docker logs processor
docker logs gateway
```

Look for messages like these:

```text
processor listening on port 9200 (internal only)
gateway listening on port 9100 → open http://localhost:8090
```

You have now created a network, built two images, and started two containers. Later, Compose will handle these steps for you.

### Send a message

1. Open [http://localhost:8090](http://localhost:8090).
2. Type a message.
3. Click **Send**.

The page returns your text in capitals. It also shows port information:

```text
gateway sent from port          44456
processor listening on port      9200
processor saw it arrive from     44456
```



### Why do the first and third numbers match?

The processor listens on port `9200`. That is the destination.

The gateway also needs a port for its outgoing connection. The operating system chooses one automatically. In this example, it chose `44456`.

The processor sees the request arriving from that same port. That is why the first and third numbers match.

This temporary port is called an **ephemeral source port**. It may change with each new connection. You do not need to configure it for this app.

### Why does the name `processor` work?

Both containers are on the user-defined network `toynet`. Docker lets containers on this network find each other by name.

That is why the gateway can call:

```text
http://processor:9200
```

It does not need to know the processor’s IP address.

Leave both containers running. You’ll inspect them next.

---



## Step 2: Check the ports

In this setup, your laptop can reach the gateway through a published port. The processor has no published port.

### Read the PORTS column

Run:

```bash
docker ps
```

You should see something like:

```text
IMAGE           PORTS                       NAMES
toy-gateway     127.0.0.1:8090->9100/tcp      gateway
toy-processor                               processor
```

The gateway has a port mapping. The processor does not.

An empty `PORTS` column does not mean the processor is not listening. It means this output shows no published or declared port for it.

### Read the port mapping

```text
127.0.0.1:8090->9100/tcp
```

This means:

- Accept connections on your laptop at `127.0.0.1:8090`.
- Forward them to port `9100` inside the gateway container.

The `-p` flag uses this order:

```text
IP address : host port : container port
```

The host port comes first. The container port comes second.

### Why include `127.0.0.1`?

`127.0.0.1` is the loopback address. It limits the published port to your own machine.

If you omit it:

```bash
-p 8090:9100
```

Docker normally publishes the port on all host addresses. Other machines may then be able to connect, depending on your network and firewall.

For this tutorial, keep `127.0.0.1`. You do not need to serve other machines.

### Test from your laptop

Run:

```bash
curl http://localhost:8090
```

This should return the gateway’s HTML page.

Now try:

```bash
curl --max-time 3 http://localhost:9200/health
```

This should fail, assuming nothing else is using port `9200` on your laptop.

The processor listens inside its container. You have not mapped its port to `localhost:9200` on your laptop.

### Test from inside the gateway

`docker exec` runs a command inside a running container.

Run:

```bash
docker exec gateway curl http://processor:9200/health
```

This should return:

```text
ok
```

Now try:

```bash
docker exec gateway curl --max-time 3 http://localhost:9200/health
```

This should fail.

Inside the gateway container, `localhost` means the gateway itself. It does not mean your laptop or the processor.

Use `processor` to reach the processor container.

> The gateway image includes `curl` for these tests. The processor image does not need it.



### Where do the port settings come from?

The processor reads its listening port from the `PORT` environment variable:

```bash
-e PORT=9200
```

The gateway reads the processor’s address from two environment variables:

```bash
-e PROCESSOR_HOST=processor
-e PROCESSOR_PORT=9200
```

The gateway’s published port comes from:

```bash
-p 127.0.0.1:8090:9100
```

These settings do different jobs:

- `PORT` tells the processor where to listen.
- `PROCESSOR_PORT` tells the gateway where to connect.
- `-p` makes the gateway available through a port on your laptop.

Containers on the same Docker network do not need published ports to communicate.

---



## Step 3: Change the ports

Now change the port settings without editing Python.

### Change the host port

Remove the gateway container:

```bash
docker rm -f gateway
```

Start it again, using host port `8095`:

```bash
docker run -d --name gateway --network toynet \
  -p 127.0.0.1:8095:9100 \
  -e PROCESSOR_HOST=processor \
  -e PROCESSOR_PORT=9200 \
  toy-gateway
```

Open [http://localhost:8095](http://localhost:8095).

The gateway still listens on port `9100` inside its container. Only the host port changed. The old address, `localhost:8090`, no longer reaches this app.

### When would you change the host port?

Suppose another application already uses host port `8090`.

You cannot publish both applications on the same host address and port. Choose another host port, such as `8095`.

The containers can still use the same internal port. Each container has its own network environment.

### Change the processor’s port

Remove the processor:

```bash
docker rm -f processor
```

Start it on port `9300`:

```bash
docker run -d --name processor --network toynet \
  -e PORT=9300 toy-processor
```

Send a message from the browser. It should fail.

The processor now listens on `9300`, but the gateway still connects to `9200`.

### Update the gateway

Remove the gateway:

```bash
docker rm -f gateway
```

Start it with the new processor port. Also restore the original host port, `8090`:

```bash
docker run -d --name gateway --network toynet \
  -p 127.0.0.1:8090:9100 \
  -e PROCESSOR_HOST=processor \
  -e PROCESSOR_PORT=9300 \
  toy-gateway
```

Open [http://localhost:8090](http://localhost:8090) and send another message. It should work.

The two settings must agree:

- The processor’s `PORT`.
- The gateway’s `PROCESSOR_PORT`.

Keeping these values in configuration lets you change them without rebuilding the images.

### Clean up before Compose

Remove both containers and the network:

```bash
docker rm -f gateway processor
docker network rm toynet
```

This gives Step 4 a clean starting point.

---



## Step 4: Run with Compose

Docker Compose describes the application in a YAML file. It records the images to build, the containers to start, and the network settings.

Open `docker-compose.yml`. These settings should look familiar:

```yaml
  gateway:
    ports:
      - "127.0.0.1:8090:9100"
    environment:
      PROCESSOR_HOST: processor
      PROCESSOR_PORT: "9200"

  processor:
    environment:
      PORT: "9200"
    # No published port
```

This is an excerpt, not the complete file.

The gateway publishes a port. The processor does not. Both use `9200` for the processor’s listening port.

### Start the app

Run:

```bash
docker compose up
```

Compose builds the images if needed and starts the containers.

You should see the same listening-port messages as before. Open [http://localhost:8090](http://localhost:8090) and send a message.

### What did Compose do?

Using this project’s configuration, Compose:

1. Built the images if they were not already available.
2. Created the network named `toynet`.
3. Started both containers on that network.
4. Made the services reachable by name.

The gateway can therefore call `http://processor:9200`, just as it did before.

This file explicitly names its network `toynet`. Without a custom network setting, Compose would normally create a project-specific default network, such as `port_toy_default`.

### Compare the commands


| By hand                                                         | With Compose                           |
| --------------------------------------------------------------- | -------------------------------------- |
| `docker ps`                                                     | `docker compose ps`                    |
| `docker exec gateway curl ...`                                  | `docker compose exec gateway curl ...` |
| `docker rm -f gateway processor` and `docker network rm toynet` | `docker compose down`                  |
| `-p` on `docker run`                                            | `ports:` in YAML                       |
| `-e` on `docker run`                                            | `environment:` in YAML                 |


You can repeat the port experiments in `docker-compose.yml`.

After changing a setting, run:

```bash
docker compose up -d
```

Compose applies the changes and runs the app in the background.

If you change a Dockerfile or something copied into an image during its build, request a rebuild:

```bash
docker compose up -d --build
```



### Stop and remove the app

If Compose is running in your terminal, press `Ctrl+C` to stop the containers.

Then run:

```bash
docker compose down
```

This removes the containers and the network managed by Compose. The built images remain.

### Why use both commands?

`Ctrl+C` stops the containers but leaves them in place.

You can still see them with:

```bash
docker compose ps -a
```

`docker compose down` removes them and the Compose-managed network.

A stopped container no longer serves its published port. You use `down` to clean up the containers and network—not just to stop traffic.

---



## Port and networking cheat sheet


| Setting or message             | Meaning                                                                                   |
| ------------------------------ | ----------------------------------------------------------------------------------------- |
| `-p 8090:9100`                 | Forward host port `8090` to container port `9100`.                                        |
| `-p 127.0.0.1:8090:9100`       | Publish the port for access from this machine only.                                       |
| `127.0.0.1:8090->9100/tcp`     | The mapping shown by `docker ps`. The host is on the left.                                |
| `0.0.0.0:8090->9100/tcp`       | The port is published on all IPv4 host addresses.                                         |
| No `ports:` or `-p`            | No host port is published. Containers on the same network can still connect.              |
| `EXPOSE 9100`                  | Documents a container port. It does not publish it.                                       |
| `localhost` inside a container | That container itself.                                                                    |
| `http://processor:9200`        | Connect to the processor by name on port `9200`.                                          |
| Listening port                 | The port where a server accepts connections.                                              |
| Source port                    | The port used by the caller for a connection. Usually chosen automatically.               |
| `port is already allocated`    | The requested host address and port are already in use.                                   |
| `Connection refused`           | The connection was rejected, often because nothing is listening at that address and port. |
| `could not resolve host`       | The hostname could not be resolved. Check the name and network.                           |




## Handy commands


| Command                                 | Purpose                                                   |
| --------------------------------------- | --------------------------------------------------------- |
| `docker network create toynet`          | Create the network.                                       |
| `docker build -t toy-gateway ./gateway` | Build the gateway image.                                  |
| `docker ps`                             | List running containers and port mappings.                |
| `docker logs gateway`                   | Show the gateway’s logs.                                  |
| `docker exec -it gateway sh`            | Open an interactive shell in the gateway.                 |
| `docker rm -f gateway processor`        | Stop and remove both containers.                          |
| `docker network rm toynet`              | Remove the network.                                       |
| `docker compose up -d`                  | Start the Compose app in the background.                  |
| `docker compose up -d --build`          | Rebuild the images and start the app.                     |
| `docker compose ps`                     | List the project’s running containers.                    |
| `docker compose logs -f gateway`        | Follow the gateway’s logs.                                |
| `docker compose exec gateway sh`        | Open a shell in the gateway.                              |
| `docker compose down`                   | Stop and remove the app’s containers and managed network. |
| `docker network ls`                     | List Docker networks.                                     |
| `docker network inspect toynet`         | Show the network’s containers and IP addresses.           |


