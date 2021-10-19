from laminar import Flow, Layer

flow = Flow(name="TestFlow")


@flow.layer
class One(Layer):
    def __call__(self) -> None:
        ...


@flow.layer
class Two(Layer):
    def __call__(self, one: One) -> None:
        ...


@flow.layer
class Three(Layer):
    def __call__(self, one: One) -> None:
        ...


@flow.layer
class Four(Layer):
    def __call__(self, two: Two, three: Three) -> None:
        ...


# for layer in [One, Two, Three, Four]:
#     print(type(layer()).__name__, {k: v for k, v in vars(layer).items() if not callable(v)}, vars(layer()))

print(flow.dependencies)
print(flow.dependents)
