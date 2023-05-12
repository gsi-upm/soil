There are two similar implementations of this simulation.

- `basic`. Using simple primites
- `improved`. Using more advanced features such as the delays to avoid unnecessary computations (i.e., skip steps).

The examples can be run directly in the terminal, and they accept command like arguments.
For example, to enable the CSV exporter and the Summary exporter, while setting `max_time` to `100` and `seed` to `CustomSeed`:

```
python rabbit_agents.py  --set max_time=100 --csv -e summary  --set 'seed="CustomSeed"'
```

To learn more about how this functionality works, check out the `soil.easy` function.

