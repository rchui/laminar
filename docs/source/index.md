# laminar

> "slow is smooth, and smooth is fast"

`laminar` is the workflow framework that works for you. It aims to be a modern container first framework that enables you to rapidly go from local development into production as quickly as possible.

## Key Features

* **Easy to Write**: `laminar` brings together many of the best ideas from the various workflow frameworks that came before it. The dependencies are declarative and the logic is imperative. Concepts are consistent throughout the framework making it easy to understand and implement.
* **Container First**: Containers are first class citizens in `laminar` flows. Containers are both used as a "write once, deploy anywhere" method of packaging software applications for portability, and for comparmentalization and isolation of `laminar` flow layers from each other.
* **Total Control**: `laminar` flows are highly configurable, both statically at definition time, and dynamically at run time. Every component comes with sane defaults out of the box with the ability to customize them to suite your needs.
* **Any Scale**: `laminar` can scale to the size of the compute you can throw at it. From small locally run prototypes to tens of thousands of concurrent executions running in the cloud, `laminar` gives you the capabilities to handle it all.

## Why laminar?

```{rubric} Custom DSLs
```

Many workflow frameworks come with custom DSls that you must learn and adhere to. Many of them implement imperative directives within declarative specifications, attempting to put a round peg into a square hole. `laminar` is written and allows the user to write their workflows in pure python. It is designed to give you the guard rails of a DSL with the power of a full programming language.

* [nextflow](https://www.nextflow.io/)
* [snakemake](https://snakemake.readthedocs.io/en/stable/)
* [cromwell](https://cromwell.readthedocs.io/en/stable/)

```{rubric} Uncomposable Workflows
```

Many workflow frameworks were not designed to chain workflows together (passing the outputs of one workflow to the inputs of another workflow). This hampers reusability of workflow logic and causes tedious logic duplication and indirection. `laminar` treats workflow chaining as a first-class citizen and was designed with this use case in mind.

```{rubric} Poor Test Strategies
```

Many workflow frameworks don't consider how a user would test the workflow after it has been authored. In many times it leaves it to the user to figure out how to test the business logic appropriately, but this is often difficult and typically involves black box end to end testing. `laminar` has a pluggable component system that enables local/remote execution for easy testing.

* [airflow](https://airflow.apache.org/)
* [luigi](https://luigi.readthedocs.io/en/stable/#)

```{rubric} Static Resource Allocation
```

Many workflow frameworks require you to declare your resource requirements up front. This may be useful for well characterized use cases, but when your workflow needs to adjust based off of a set of inputs it is unable to. This requires the user to re-deploy the workflow with different resource requirements or repetitively retry within the workflow by incrementing the resources. This is slow and wasteful. `laminar` provides the capabilities to dynamically react to resource needs and adjust on the fly as needs change.


```{rubric} Lack of Conditional Branching
```

Many workflow frameworks lack conditional branching (a logical fork where none, one, or many of the child tasks need to be executed depending on a condition). There are many cases in which a branch may not need to be executed but whether or not is indeterminate until runtime. Many workflows provide hacky workarounds to get around this limitation. `laminar` has conditional branching out of the box.

```{rubric} Behind the Scenes Magic
```

Many workflow frameworks implement behind the scenes magic in an attempt to improve the user experience. This ranges from injecting custom code at runtime to parsing the AST to determine flow information. In many cases it hijacks the environment in a way that breaks the expectations of the user and creates a set of "gotchas" and sharp edges for the user to easily cut themselves on. `laminar` does not use any magic. It may be more verbose in some areas, but that is because it adheres strictly to the Python syntax to give you the predictability you desire.

* [metaflow](https://metaflow.org/)

## Why Not laminar?

I like to think that `laminar` can grow into something great. It has a great foundation to succeed but there are many headwinds facing it that you should consider:

* **Immature**: There are many other battle-hardened workflow frameworks that are out there that have faced the test of time and have consistently delivered.
* **Small**: Other workflow frameworks have large communities to feed off of and get help with your work.
* **Scheduling**: `laminar` does not provide scheduling out of the box. It relies on users to determine when flows should be scheduled.
* **Deployment**: `laminar` does not provide help deploying flows. It relies on users to determine how flows are deployed and all the infrastructure around managing containers.
* **UI**: `laminar` does not provide a user interface to visualize the flows as they are running.

```{toctree}
:maxdepth: 4
:caption: Getting Started
:hidden:

Introduction <self>
Installation <getting_started/installation>
Basics <getting_started/basics>
Deployment <getting_started/deployment>
```

```{toctree}
:maxdepth: 4
:caption: Layers
:hidden:

Scaling Up <layers/scaling_up>
Scaling Out <layers/scaling_out>
Branching <layers/branching>
Configuration <layers/configuration>
```

```{toctree}
:maxdepth: 4
:caption: Flows
:hidden:

Parameters <flows/parameters>
Datastores <flows/datastores>
Executors <flows/executors>
Schedulers <flows/schedulers>
Results <flows/results>
```

```{toctree}
:maxdepth: 4
:caption: Advanced
:hidden:

Recovery <advanced/recovery>
Composition <advanced/composition>
Hooks <advanced/hooks>
Ser(De) <advanced/serde>
Testing <advanced/testing>
```

```{toctree}
:maxdepth: 4
:caption: Technical Details
:hidden:

Datastores <technical/datastores>
Executions <technical/executions>
laminar <api/laminar>
```
