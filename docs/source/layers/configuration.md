# Configuration

## Access

Configurations are a part of the class definition of a `Layer` and are available as an atttribute of the `Layer`. All `Layer` configurations are nested underneath the `Layer.configuration` attribute.

```python
# main.py

from laminar import Flow, Layer
from laminar.configurations.layers import Container

class ConfiguredFlow(Flow):
    ...

@ConfiguredFlow.register(container=Container(cpu=4, memory=2000, workdir="/app"))
class Task(Layer):
    def __call__(self) -> None:
        print(self.configuration.container.cpu, self.configuration.container.memory)

if flow := ConfiguredFlow():
    flow()
```

```python
python main.py

>>> 4 2000
```

```{warning}
If a [hook](../advanced/hooks) changes a value in `Layer.configuration`, that change will not be reflected in `Layer.__call__`.
```
