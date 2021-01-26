from laminar import Flow, Response

flow = Flow(name="sentinel", project="gwas")


class Start(Response):
    a: str
    b: int


@flow.task()
def start(a: str, b: int) -> Start:
    return Start(a=a, b=b)


class Branch1(Response):
    branch_1: str


@flow.task(start)
def branch_1(a: str) -> Branch1:
    return Branch1(branch_1=a)


class Branch2(Response):
    branch_2: int


@flow.task(start)
def branch_2(b: int) -> Branch2:
    return Branch2(branch_2=b)


class End(Response):
    end: str


@flow.task(branch_1, branch_2)
def end(branch_1: str, branch_2: int) -> End:
    return End(end=branch_1 + str(branch_2))


if __name__ == "__main__":
    flow(a="hello world", b=5)
