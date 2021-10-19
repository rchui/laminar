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
