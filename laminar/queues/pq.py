"""PQ client for laminar flows"""

from pq import PQ

from laminar.databases import postgres


class Client:
    _pq: PQ = None

    @property
    def pq(self) -> PQ:
        if self._pq is None:
            self._pq = PQ(pool=postgres.client.pool)
        return self._pq


client = Client()
