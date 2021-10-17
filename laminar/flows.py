# class Flow(BaseModel):
#     datasource: DataSource = DataSource()
#     id: str = current.execution.id or str(Ksuid())

#     dag: Dict[Type[Layer], Set[Type[Layer]]] = Field(default_factory=dict)
#     mapping: Dict[str, Type[Layer]] = Field(default_factory=dict)

#     def __init__(__pydantic_self__, **data: Any) -> None:
#         super().__init__(**data)

#     @property
#     def _dag(self) -> Dict[str, str]:
#         return {child.__name__: {parent.__name__ for parent in parents} for child, parents in self._dag.items()}

#     @property
#     def name(self) -> str:
#         return self.__repr_name__()

#     def __call__(self) -> None:
#         def get_pending(dag: Dict[str, str], finished: Set[str]) -> Set[Type[Layer]]:
#             return {self.mapping[name] for name, parents in dag.items() if parents.issubset(finished)}

#         if current.layer.name is not None:
#             layer = self.mapping[current.layer.name]

#             configuration: Configuration = layer.configuration

#             parameters = {
#                 artifact: self.datasource.read(self.datasource.uri(self.name, self.id, source.__name__), artifact)
#                 for artifact, source in configuration.dependencies.data.items()
#             }

#             run = layer(configuration=configuration, **parameters)

#             run()

#             for artifact, value in vars(run).items():
#                 if artifact != "configuration":
#                     self.datasource.write(self.datasource.uri(self.name, self.id, layer.__name__), artifact, value)

#         else:
#             dag = self.dag
#             finished: Set[str] = set()

#             pending = get_pending(dag, finished)

#             while pending:
#                 for layer in pending:

#                     configuration: Configuration = layer.configuration

#                     archive = (
#                         f"{os.getcwd()}/{self.datasource.root}:{configuration.container.workdir}/{self.datasource.root}"
#                     )
#                     command = " ".join(
#                         [
#                             "docker",
#                             "run",
#                             "--rm",
#                             "--interactive",
#                             "--tty",
#                             f"--env LAMINAR_EXECUTION_ID={self.id}",
#                             f"--env LAMINAR_LAYER_NAME={layer.__name__}",
#                             f"--volume {archive}",
#                             f"--workdir {configuration.container.workdir}",
#                             configuration.container.image,
#                             configuration.container.command,
#                         ]
#                     )
#                     logger.info(command)
#                     subprocess.run(shlex.split(command), check=True)

#                     finished.add(layer.__name__)
#                     dag.pop(layer.__name__)

#                 pending = get_pending(dag, finished)

#                 if not pending and dag:
#                     raise FlowError(
#                         f"A dependency exists for a step that is not registered with the {self.name} flow. "
#                         f"Finished steps: {sorted(finished)}. "
#                         f"Remaining dag: {dag}."
#                     )

#     def layer(self, layer: LayerType) -> LayerType:
#         if layer.__name__ in self.mapping:
#             raise FlowError(f"The {layer.__name__} layer is being added more than once to the {self.name} flow.")

#         self.mapping[layer.__name__] = layer
#         self._dag[layer] = {
#             *layer.configuration.dependencies.layers,
#             *layer.configuration.dependencies.data.values(),
#         }

#         return layer
