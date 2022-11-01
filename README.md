# laminar

> "slow is smooth, and smooth is fast"

`laminar` is the workflow framework that works for you. It aims to be a modern container first framework that enables you to rapidly go from local development into production as quickly as possible.

* Easy to write, container first, cloud first
* Configureable statically at definition time and dynamically at runtime
* Fully definined in Python and fully typed
* Easily testable
* Foreach fanouts
* Composable workflows
* Conditional branching
* No AST introspection, shared global state, or function hijacking magic

To learn more, read the [documentation](https://rchui.github.io/laminar/).

```python
# main.py
from laminar import Flow, Layer

# Declare the Flow
class HelloFlow(Flow): ...

# Register Layers
@HelloFlow.register
class Hello(Layer):
    def __call__(self) -> None:
        self.value = "hello"

# Register a Layer dependency
@HelloFlow.register
class World(Layer):
    def __call__(self, hello: Hello) -> None:
        print(f"{hello.value} world")

# Execute the Flow
if flow := HelloFlow():
    flow()
```

```python
python main.py
>>> "hello world"
```

## Installation

To install the latest release of `laminar`:

```bash
python -m pip install laminar
```

To upgrade to the latest release of `laminar`:
```bash
python -m pip install --upgrade laminar
```

## Contributing

We welcome contributions to laminar.
