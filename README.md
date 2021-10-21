# Laminar

## Example

```python
# main.py

from laminar import Flow, Layer

flow = Flow("HelloFlow")

@flow.layer
class Start(Layer):
    def __call__(self) -> None:
        self.message = "Hello World"
        print(f"Sending the message: {self.message}")

@flow.layer
class Middle(Layer):
    def __call__(self, start: Start) -> None:
        print(start.message)
        self.message = start.message

@flow.layer
class End(Layer):
    def __call__(self, middle: Middle) -> None:
        print(f"Sent message: {middle.message}")

if __name__ == '__main__':
    flow()
```

```python
python main.py

>>> "Sending the message: Hello World"
>>> "Hello World"
>>> "Sent message: Hello World"
```

## Forked Artifacts
```python
# main.py
from laminar import Flow, Layer

flow = Flow("ForkedFlow")

@flow.layer
class Fork(Layer):
    def __call__(self) -> None:
        self.fork(foo=[1, 2, 3])

@flow.layer
class Process(Layer):
    def __call__(self, fork: Fork) -> None:
        print(list(fork.foo))
        print(fork.foo[1])

if __name__ == '__main__':
    flow()
```

```python
python main.py

>>> [1, 2, 3]
>>> 2
```