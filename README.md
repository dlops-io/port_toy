# Port Toy App

<img src="browser-gateway-processor.png" width="800" alt="Flow: browser → gateway → processor">

Your browser talks to a **gateway** service, which forwards the request to a **processor** service that turns the text into CAPITALS and sends the reply back the same way. The upper-casing is just the toy workload — what you're really learning is **which ports** that request travels through.

You'll run it four ways - progressing from wiring the network by hand, to inspecting the ports, moving them, and finally letting Docker Compose do the same work for you - which introduces the container networking you'll use throughout AC215.

## What you'll build

The goal: **understand how two containers talk to each other, and which ports are involved**. We do it four ways, each pulling back one more layer of the magic:

1. 🧩 **Wire it by hand.** Create the network, build the images, and `docker run` both containers yourself. Two containers, one published port, one reply.
2. 🔍 **See which ports are open.** Read the `PORTS` column, prove the processor is unreachable from your laptop, then reach it by name from inside the network.
3. 🔌 **Move the ports.** Change the numbers on the `docker run` flags and watch the app follow - without touching a line of Python.
4. 🐳 **Do it with Compose.** Put the same network, builds, and runs into `docker-compose.yml` and bring everything up with one command. This is what you've been typing by hand all along.

By the end, you can explain any line in a `ports:` block and debug a container that "can't reach" another one.

## Prerequisites

Complete **[Tutorial 0 - Setup & Installs](https://github.com/dlops-io/ac215-setup)** first. This tutorial
only needs **Docker Desktop** from that list - no GCP account, no service account, no Python installed
locally. Everything runs on your laptop.

> Make sure Docker Desktop is actually running before you start (`docker run hello-world` should succeed).

---

## Contents

Four short walkthroughs :

- [Wire the network by hand](#-wiring-the-network-by-hand)
- [See which ports are open](#-seeing-which-ports-are-open)
- [Move the ports](#-moving-the-ports)
- [Run it with Compose](#-running-it-with-compose)

---

## What's in the box

Two containers. The `gateway` serves a web page and forwards your text; the `processor` upper-cases it and replies.

```
browser  --localhost:8090-->  gateway  --http://processor:9200-->  processor
             (published)     (serves the page,     (by name,        (upper-cases,
                              forwards the text)    internal only)   replies)
```

```
port_toy/
├── docker-compose.yml   # you'll use this in Step 4 — skip it until then
├── gateway/
│   ├── Dockerfile     # builds the gateway image
│   ├── gateway.py     # serves the page + forwards your text to the processor
│   └── index.html     # the page you open at localhost:8090
└── processor/
    ├── Dockerfile     # builds the processor image
    └── processor.py   # listens internally, upper-cases the text, replies
```

---

## 🧩 Wiring the Network by Hand

_**Step 1 of 4** — no Compose. You create the network, build the images, and start both containers yourself. Same app you'll later start with one command, but every step is a command you typed._

### Clone the github repository

- Clone or download from [here](https://github.com/dlops-io/port_toy)
- `cd port_toy`

### Create the network

* `docker network create toynet`

### Build both images

* `docker build -t toy-processor ./processor`
* `docker build -t toy-gateway ./gateway`

### Run the processor — internal only

* `docker run -d --name processor --network toynet -e PORT=9200 toy-processor`

No `-p` flag. This container is on the network but publishes nothing — reachable from other containers, invisible to your laptop.

### Run the gateway — with a published port

```
docker run -d --name gateway --network toynet -p 127.0.0.1:8090:9100 \
  -e PROCESSOR_HOST=processor -e PROCESSOR_PORT=9200 toy-gateway
```

You should see both containers announce themselves in their logs (`docker logs processor`, `docker logs gateway`):

```
processor  | processor listening on port 9200 (internal only)
gateway    | gateway listening on port 9100  →  open http://localhost:8090
```

> [!TIP]
> **What you just typed by hand:** a network, two builds, two runs, two `--name` flags, and a handful of environment variables. Compose will later collapse all of this into one file and one command — but first you should feel every piece.

### Send a message

* Open **http://localhost:8090** in your browser
* Type a message and click **Send**

You get back the upper-cased text, plus the three port numbers that were involved:

```
gateway sent from port          44456
processor listening on port     9200
processor saw it arrive from    44456
```

> [!TIP]
> **Why the first and third numbers match:** `9200` is a *listening* port — the processor chose it and waits there. `44456` is an *ephemeral source port* — when the gateway opened the outgoing connection, its operating system grabbed a free high-numbered port to send **from**. The processor reports it as "arrived from" because that's the return address. Send again and you'll get a different number: source ports are picked per connection and thrown away afterwards. Only the listening port is stable, and only listening ports are ones you configure.

> [!TIP]
> **`--name` is the DNS name.** On a user-defined network like `toynet`, Docker resolves container names automatically, so `--name processor` is precisely what makes `http://processor:9200` work from the gateway. Drop `--network toynet` and both containers land on the default bridge network, where name resolution **doesn't** work and the gateway fails to find the processor. Try it — a deliberate failure you've diagnosed is worth more than one you haven't.

Leave both containers running — Step 2 inspects them.

---

## 🔍 Seeing Which Ports Are Open

_**Step 2 of 4** — the point of the whole demo. Only **one** of these two containers is reachable from your laptop. Here we prove it: the processor's port is invisible from outside, but reachable by name from inside the network._

### Read the PORTS column

* `docker ps`

```
CONTAINER ID   IMAGE           ...   PORTS                      NAMES
...            toy-gateway     ...   127.0.0.1:8090->9100/tcp   gateway
...            toy-processor   ...                              processor
```

The gateway has a mapping. The processor's `PORTS` column is **empty** — it is listening on 9200, but that port was never published to your laptop.

> [!TIP]
> **Reading `127.0.0.1:8090->9100/tcp`:** Left of the arrow is your **laptop**, right of it is **inside the container**. So: "traffic arriving at port 8090 on this laptop gets forwarded to port 9100 inside the gateway container." It comes from the `-p 127.0.0.1:8090:9100` flag you passed to `docker run`, and the rule is always **`host:container`** — host first. Getting the order backwards is the single most common Docker networking mistake; if `localhost:8090` gives you nothing, check which side is which.

> [!TIP]
> **What's that `127.0.0.1` in front?** A published port takes an optional third field on the left: **`ip:host:container`**. The IP says *which of your laptop's network addresses* accept the connection. `127.0.0.1` is loopback — only this machine. Write `-p 8090:9100` with no IP and Docker defaults to **all** addresses, which `docker ps` reports as `0.0.0.0:8090->9100/tcp` — meaning anyone on the same wifi can reach your container. That default is fine at home and a bad idea on campus wifi or in a coffee shop, which is why this demo pins it to `127.0.0.1`. Publish to all addresses only when you actually mean to serve other machines.

### Prove the processor is not reachable from your laptop

* `curl localhost:8090` → returns the HTML page ✅
* `curl --max-time 3 localhost:9200/health` → `Failed to connect ... Connection refused` ❌

Nothing is listening on 9200 *on your laptop*. The processor is listening on 9200 **inside the Docker network**, which is a different place entirely.

### Now reach it from inside the network

`docker exec` runs a command *inside* a running container — so this is the gateway's view of the world, not yours:

* `docker exec gateway curl http://processor:9200/health` → `ok` ✅
* `docker exec gateway curl --max-time 3 http://localhost:9200/health` → `Connection refused` ❌

> [!TIP]
> **Two lessons in those four commands.** First, **`processor` is a hostname.** Putting both containers on `toynet` with `--name` registered each name in that network's DNS, so `http://processor:9200` resolves without you ever knowing an IP. Second, **`localhost` inside a container means *that container*.** Each container gets its own network namespace and its own loopback interface, so from inside the gateway, `localhost` is the gateway — not your Mac, and not the processor. "It works on my machine but the container can't reach it" is almost always this: a service addressed as `localhost` when it should be addressed by its container name.

> [!NOTE]
> **Only the gateway image has `curl`.** Look at the two Dockerfiles: `gateway/Dockerfile` installs it, `processor/Dockerfile` deliberately doesn't. The gateway is the container you run these experiments *from*; the processor only ever answers requests, so it has no use for it. Leaving it out keeps that image ~19 MB smaller and gives anyone who breaks in one less tool to work with. Install a package in the image that needs it — not in every image.

### Where the two ports come from

Notice what is *not* in the Python. `gateway.py` reads `PROCESSOR_HOST` and `PROCESSOR_PORT` from the environment; `processor.py` reads `PORT`. Both came from the `-e` flags on `docker run`:

```
# processor — listens internally, no -p
docker run ... -e PORT=9200 toy-processor

# gateway — publishes 8090→9100, dials the processor by name
docker run ... -p 127.0.0.1:8090:9100 \
  -e PROCESSOR_HOST=processor -e PROCESSOR_PORT=9200 toy-gateway
```

That missing `-p` on the processor is the whole lesson: **a container is unreachable from outside unless you publish a port.** Listening isn't enough.

---

## 🔌 Moving the Ports

_**Step 3 of 4** — now change the numbers. Ports here live in the `docker run` flags, not in code, so you can move them without editing a single line of Python. Do each change, re-run, and predict what breaks before you look._

### Change the published port

Stop and remove just the gateway, then re-run it on a different host port:

* `docker rm -f gateway`
* Re-run with `-p 127.0.0.1:8095:9100` instead of `8090`:

```
docker run -d --name gateway --network toynet -p 127.0.0.1:8095:9100 \
  -e PROCESSOR_HOST=processor -e PROCESSOR_PORT=9200 toy-gateway
```

* Your app is now at **http://localhost:8095**. `localhost:8090` is dead.

Nothing inside the container moved — the gateway still listens on 9100. You only changed which door on your laptop leads to it.

> [!TIP]
> **Why change the host side and not the container side?** The host side is the one that can collide. Two projects can both listen on 9100 *inside* their own containers with no conflict at all, because each has its own network namespace. But they can't both publish to 8090 on your laptop — you'll get `port is already allocated`. That's why the host number is the one you'll find yourself changing, and why published ports are the scarce resource.

### Change the internal port

Move the processor, **and nothing else**:

* `docker rm -f processor`
* `docker run -d --name processor --network toynet -e PORT=9300 toy-processor`
* Send a message from the browser → it fails

The processor moved, but the gateway is still knocking on 9200. Now fix it:

* `docker rm -f gateway`
* Re-run the gateway with `PROCESSOR_PORT=9300` as well (and put the published port back to `8090` while you're at it):

```
docker run -d --name gateway --network toynet -p 127.0.0.1:8090:9100 \
  -e PROCESSOR_HOST=processor -e PROCESSOR_PORT=9300 toy-gateway
```

* Send again → works.

> [!TIP]
> **Both sides have to agree.** A port number is a contract between a listener and a caller, so it appears twice: once where the processor binds it (`PORT`) and once where the gateway dials it (`PROCESSOR_PORT`). Keeping both in the run flags (and later in one compose file) means a mismatch is easy to spot. Hardcoding either one into the Python would hide half the contract inside an image you'd have to rebuild to change. **Config in the run flags / compose file, never in the code** — this is the pattern you'll reuse for every service, database URL, and API endpoint in your project.

### Clean up before Compose

Put things back to the original numbers, then tear everything down so Step 4 starts clean:

* `docker rm -f gateway processor`
* `docker network rm toynet`

---

## 🐳 Running it with Compose

_**Step 4 of 4** — the payoff. Everything you typed by hand is already declared in `docker-compose.yml`. One command builds the images, creates the network, starts both containers, and registers the service names in DNS._

Open `docker-compose.yml` and you'll recognize every piece:

```yaml
  gateway:
    ports:
      - "127.0.0.1:8090:9100"  # ip:host:container — 127.0.0.1 = this laptop only
    environment:
      PROCESSOR_HOST: processor
      PROCESSOR_PORT: "9200"

  processor:
    environment:
      PORT: "9200"
    # no ports: → internal only; reachable only as http://processor:9200
```

### Start both containers

* `docker compose up`

You should see the same announcements as before:

```
processor-1  | processor listening on port 9200 (internal only)
gateway-1    | gateway listening on port 9100  →  open http://localhost:8090
```

> [!TIP]
> **What `docker compose up` just did:** Four things in one command — (1) read `docker-compose.yml` and built an image for each service from its `Dockerfile`, (2) created a private network called `port_toy_default` for this project, (3) started both containers on that network, and (4) registered each one under its **service name** in that network's DNS, so `gateway` can reach `http://processor:9200` with no IP addresses anywhere. That's exactly what you did by hand in Steps 1–3.

* Open **http://localhost:8090** and send a message. Identical behavior — one file instead of a dozen flags.

### Compose equivalents of what you already know

| By hand | With Compose |
| --- | --- |
| `docker ps` | `docker compose ps` |
| `docker exec gateway curl ...` | `docker compose exec gateway curl ...` |
| `docker rm -f gateway processor` + `docker network rm toynet` | `docker compose down` |
| `-p` / `-e` on `docker run` | `ports:` / `environment:` in the YAML |

Try the port experiments again if you like — change the numbers in `docker-compose.yml`, then `docker compose up -d` — and you'll see why Compose is the form you'll use for the rest of the course: the contract lives in one checked-in file that anyone on your team can run.

### Stop it

* Press `Ctrl+C` to stop the containers
* Run `docker compose down` to remove them

> [!TIP]
> **Why both?** `Ctrl+C` only **stops** the containers — it doesn't remove them. Run `docker compose ps -a` (note the `-a`, for "all") and you'll still see both, sitting in the `exited` state; `docker network ls` still lists the `port_toy_default` network Compose created. `docker compose down` is the true inverse of `up`: `up` made containers *and* a network, so `down` removes containers *and* the network, leaving only the built images behind.

> [!NOTE]
> You may hear that you need `down` to "free up the port." Not so — a *stopped* container has already released its port binding, so `localhost:8090` goes dead the moment you press `Ctrl+C`. `down` is about not leaving containers and networks behind, not about the port.

---

## Port and Networking Cheat Sheet

| What you see | What it means |
| --- | --- |
| `"8090:9100"` / `-p 8090:9100` | `host:container` — port 8090 on your laptop forwards to 9100 inside the container |
| `"127.0.0.1:8090:9100"` | `ip:host:container` — same, but only **this** machine may connect |
| `127.0.0.1:8090->9100/tcp` | The mapping as `docker ps` reports it. Left of `->` is the host |
| `0.0.0.0:8090->9100/tcp` | What you get with no IP — **every** address, so others on your wifi can reach it |
| No `ports:` / no `-p` | Container is **internal only** — reachable from the network, invisible to your laptop |
| `EXPOSE 9100` in a Dockerfile | Documentation only. It does **not** publish anything; you still need `-p` |
| `localhost` inside a container | That container itself — not your laptop, not another container |
| `http://processor:9200` | Another container **by name**, resolved by Docker's DNS |
| Listening port (`9200`) | Stable, you configure it, a server waits there |
| Source port (`44456`) | Ephemeral, picked by the OS per connection, discarded afterwards |
| `port is already allocated` | Two containers tried to publish the **same host port**. Change the left number |
| `Connection refused` | Something is listening somewhere, but not at the address you dialed |
| `could not resolve host` | The **name** is wrong, or the containers aren't on the same user-defined network |

### Handy commands

| Command | What it does |
| --- | --- |
| `docker network create toynet` | Create a user-defined network (name DNS included) |
| `docker build -t toy-gateway ./gateway` | Build an image from a Dockerfile |
| `docker run -d --name ... --network ... -p ... -e ...` | Start a container with name, network, ports, env |
| `docker ps` | List running containers and their published ports |
| `docker exec gateway sh` | Open a shell **inside** the gateway container |
| `docker rm -f gateway processor` | Force-remove containers |
| `docker network rm toynet` | Remove the network you created |
| `docker compose up -d` | Build (if needed) and start everything in the background |
| `docker compose ps` | List this project's containers and their published ports |
| `docker compose logs -f gateway` | Follow one service's logs |
| `docker compose exec gateway sh` | Open a shell **inside** the gateway container |
| `docker compose down` | Stop the containers and remove the network |
| `docker network ls` | List networks — you'll see `toynet` or `port_toy_default` while the app is up |
| `docker network inspect toynet` | Show which containers are attached, and their IPs |
