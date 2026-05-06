# C++ Low-Latency Metrics Module

This folder demonstrates how latency-sensitive calculations could be moved from Python into C++.

Compile and run the standalone example:

```bash
g++ -O3 -std=c++17 low_latency_metrics.cpp -o low_latency_metrics
./low_latency_metrics
```

Build a shared library that Python can call with `ctypes`:

```bash
g++ -O3 -std=c++17 -shared -fPIC low_latency_metrics.cpp -o liblow_latency_metrics.so
```

Example Python call:

```python
import ctypes
import numpy as np

lib = ctypes.CDLL("./liblow_latency_metrics.so")
lib.compute_volatility.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_int]
lib.compute_volatility.restype = ctypes.c_double

prices = np.array([100.0, 101.2, 100.4, 103.1, 102.7], dtype=np.float64)
result = lib.compute_volatility(prices.ctypes.data_as(ctypes.POINTER(ctypes.c_double)), len(prices))
print(result)
```
