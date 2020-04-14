# Exemplo
Nesse folder temos um modulo `agent.py` que define um classe `Agent` usada para monitorar os uso de
recursos por um processo.

Em sua atual implementação, o agente detecta o uso de recursos e imediatamente os envia para a
`stdout`. Algo assim:

```
Using streaming agent.
--------------------
{"cpu_usage": 0.0, "mem_usage_mb": 9}
{"cpu_usage": 0.8, "mem_usage_mb": 9}
{"cpu_usage": 0.8, "mem_usage_mb": 9}
{"cpu_usage": 0.8, "mem_usage_mb": 9}
{"cpu_usage": 1.0, "mem_usage_mb": 9}
```

Porém notou-se que em certas aplicações seria útil calcular valores agregados dessas métricas e
publicá-los de uma única vez assim que o processo sair (usemos o `stdout` mais uma vez).

De qual forma poderíamos adaptar `agent.py` de forma a suportar tal comportamento?

Em `agent-refact.py` há uma possível solução.