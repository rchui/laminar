import logging

from laminar.components import Pipeline, Step

logging.basicConfig(level=logging.INFO)


class Test(Step):
    foo = "bar"

    class Container:
        image = "test"


class One(Test):
    foo: str = "a"
    bar: bool = False

    def __call__(self) -> None:
        print(vars(self))


class Two(Test):
    foo: str

    def __call__(self) -> None:
        print(vars(self))


class Three(Test):
    def __call__(self) -> None:
        print(vars(self))


class Four(Test):
    def __call__(self) -> None:
        print(vars(self))


pipeline = Pipeline("second", One, [Two, Three], Four)
