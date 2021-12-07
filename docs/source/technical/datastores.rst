Datastores
==========

.. warning::

    This article covers internal technical details of datastores. The implementation of a datastore may change at any time without warning.

Artifacts
---------

An ``Artifact`` is a pickled and gzipped Python object and is written to ``<datastore-root>/artifacts/<hexdigest>.gz``. The ``<hexdigest>`` used to identify the ``Artifact`` is the SHA256 hexdigest of the underlying pickled Python object.

Archives
--------

When an artifact is written in ``laminar``, it is written in two parts. Once as an ``Archive`` and once as an ``Artifact``. ``laminar`` uses content addressable storage to automatically deduplicate artifacts with the same value across multiple executions.

The ``Archive`` schema is

.. code:: yaml

    artifacts:
      - hexdigest: str

and is written to ``<datastore-root>/archives/<execution>/<layer>/<index>/<artifact>.json``

Because each ``Layer`` is assigned a different index, multiple archives can exist for a single ``Artifact``. Archives can also be linked to one or more artifacts, and each ``Artifact`` is referenced via a SHA256 hexdigest that makes up the name of each stored ``Artifact``.

``Layer.shard()`` creates one archive with multiple linked artifacts. ``layers.ForEach`` creates multiple archives with one or many linked artifacts.

When the a flow's datastore reads an ``Archive`` it knows to create an ``Accessor`` if it has more than one ``Artifact`` hexdigest. A ``Layer`` also knows when multiple archives exist for an ``Artifact`` and will create an ``Accessor`` across all of them.

Archive Cache
*************

When an ``Artifact`` with multiple archives is read, it will speed up future accesses by creating a combined ``Archive`` at ``<datastore-root>/.cache/<execution>/<layer>/<artifact>.json``

Record
------

After each ``Layer`` is executed, it leaves behind a ``Record``. Records detail the execution of a ``Layer`` to aid in determining the size of downstream layers.

The ``Record`` schema is

.. code:: yaml

    flow:
      name: str
    layer:
      name: str
    execution:
      splits: int

and is written to ``<datastore-root>/.cache/<execution>/<layer>/.record.json``.
