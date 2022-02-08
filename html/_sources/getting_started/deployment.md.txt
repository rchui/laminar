# Deployment

To **deploy** an application means to make it available to users. Deploying a `Flow` allows users to run it, perform the defined work, and inspect any generated results.

## Containers

The only supported method of deployment exists with containers. Containers are a form of operating system virtualization in which software is packaged into standard units that can be deployed anywhere.

Unlike virtual machines, containers don't contain the entire operating system. Instead they share the underlying host operating system and use virtualization later in between the containers and the host like Docker.

Docker is not the only method for building, running, and deploy containers, but it will be used throughout for simplicity and consistency.

[For more information on containers.](https://www.docker.com/resources/what-container)

### Building Images

Images are the built units and become containers at runtime. Images are built to a specification like a Dockerfile. A minimal Dockerfile might look like:

```dockerfile
# Dockerfile

FROM rchui/laminar

WORKDIR /laminar

COPY . ./
```

And can be built with:

```
docker build -t my/laminar/image .
```

### Adding Requirements

Your image must contain all of the dependencies necessary to run your flow. Imagine you needed `pandas` in your image, you may have a requirements file like:

```
# requirements.txt

laminar
numpy
pandas
```

This requirements file can be integrated into your Dockerfile so that your requirements are installed when the image is built.

```dockerfile
# Dockerfile

FROM rchui/laminar

WORKDIR /laminar

COPY . ./
RUN pip install --requirement requirements.txt
```

There are many great articles about how to create small, efficient Python images: https://snyk.io/blog/best-practices-containerizing-python-docker/

### Hosting Images

Images can be pushed to and distributed by a container registry. There are several that exist including DockerHub, AWS ECR Public Registry, Google Cloud Container Registry, and Quay.

Your built images can be easily pushed to a container registry with:

```
docker push -t my/laminar/image
```

```{tip}
Docker has an extensive [getting started guide](https://docs.docker.com/get-started/) for a more in-depth dive into containers.
```

### Running

Containers run as long as the main processes continues to run. They typically contain one process but it is possible to start multiple subprocesses from the main one. When the main process stops, the container stops and exits as well.

The main process of a container is driven by the command given to start it. We can make the previously built image print out `"hello world"` before exiting.

```
docker run my/laminar/image echo "hello world"
```

## Processes

A `laminar` deployment consists of starting a scheduler process.

```{note}
It may be helpful to read [Technical Details: Execution](../technical/executions) to get a better understanding of how the processes interact.
```

### Schedulers

The scheduler starts executor processes and tracks their completion. The scheduler is a long running process that runs for the lifetime of a `Flow` execution. Scheduler processes should be run on reliable infrastructure that has high availability guarantees as the scheduler process will not recover on failure.

Consider the following simple flow:

```python
# main.py

from laminar import Flow, Layer

flow = Flow("HelloFlow")

@flow.register()
class A(Layer):
    def __call__(self) -> None:
        print(self.name)

@flow.register()
class B(Layer):
    def __call__(self, a: A) -> None:
        print(self.name)

if __name__ == "__main__":
    flow()
```

The scheduler process can be started locally or inside a container. The scheduler process must reach any invocation of `flow()`. From here the scheduler process will start to schedule layers for execution.

```{tip}
The processes must reach **any invocation** of `flow()` but do not necessarily need to reach the same one.
```

#### VirtualEnv

Virtual environments are isolated python environments. They a useful tool for local development and also serve as a useful demonstration of how to start scheduler processes. [For more information on virtualenvs.](https://virtualenv.pypa.io/en/latest/)

Install the `virtualenv` python package
```
python -m pip install virtualenv
```

Create a virtualenv
```
python -m virtualenv .venv
```

Activate the virtualenv
```
. .venv/bin/activate
```

Install additional python packages
```
python -m pip install ...
```

Start the scheduler process
```
python main.py
```

#### Container

Although scheduler processes can be started outside of a container, we recommend that users also run the scheduler in one. Using the previously built image:
```
docker run my/laminar/image python main.py
```

This command will starts a `my/laminar/image` Docker container and executes `python main.py` within it. Because the container contains all python package dependencies bundled within it, there is no need to install packages before invocation.

### Executors

The executor evaluates a single `Layer` and writes its results to a Datastore. Executors processes are always run inside a Docker container and run ephemerally for the lifetime of a `Layer` evaluation. Because of this, executor processses can be run on infrastructure with low availability guarantees.

```{tip}
With the [Retry](../layers/configuration.html#Retry) layer configuration, executors can be restarted upon failure.
```

Like the scheduler, executor processes must also reach any invocation of `flow()`. From here, the logic will intelligently diverge; executor processes will instead evaluate a single layer based on parameters passed to it by the scheduler.

Internally to start executor containers, the scheduler will (with additional parameters) invoke roughly:

```
docker run my/laminar/image python main.py
```

```{tip}
In order to change this behavior, each layer's container can be configured individually via the [Container](../layers/scaling_up.html#Container) layer configuration.
```
