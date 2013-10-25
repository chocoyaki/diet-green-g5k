diet-sched-example
==================

Summary
-------

Example of diet sed and diet plugin scheduler cooperating for
distributed scheduling using custom metrics from the grid5000 api. The
sed will retrieve the metrics (see list in next section) and send them
up the diet hierarchy in the estimation vector. The plugin scheduler
can retrieve these metrics and use them for a custom scheduling.

This example assumes one sed deployed per grid5000 node (no
aggregation of metrics for a sed frontend of several nodes).

The metrics
-----------

- num cores of the sed

- total flops of the sed

- flops per core of the sed

- average power consumption of the sed on the previous sed invocations

- average cpu idle percentage of the sed on the previous sed invocations

dependencies
------------

- for compilation: diet, boost, libcurl, jsoncpp

- at runtime: python, execo

compilation
-----------

We assume diet was installed in $HOME/opt/diet

    $ export DIET_PREFIX=$HOME/opt/diet
    $ make

example usage
-------------

To quickly check and see the whole running, you can just run
everything on a development station outside grid5000: a simple
hierarchy with a single diet master agent and a sed, and a client. In
this case, instruct the sed to retrieve the metrics not for itself but
for a given grid5000 node (any node providing power consumption
metrics will do):


- start a socks tunnel to grid5000:

        $ ssh -D 12345 access.grid5000.fr

- start agent:

        $ export LD_LIBRARY_PATH="$DIET_PREFIX/lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
        $ dietAgent ma1.cfg

- start server (gathering metrics from node taurus-16 in lyon):

        $ export LD_LIBRARY_PATH="$DIET_PREFIX/lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
        $ all_proxy=socks5h://127.0.0.1:12345 ./server taurus-16

- run client

        $ export LD_LIBRARY_PATH="$DIET_PREFIX/lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
        $ ./client
