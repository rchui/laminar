# Deployment

Once you have authored a `Flow`, you need a way to deploy and run it.

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
