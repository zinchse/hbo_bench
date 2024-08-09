**`TL;DR`** This is a dataset that allows us to run tens of thousands of experiments for query optimisation via using so-called hints in a *few minutes* on a laptop. 
The idea is that almost all the required calculations have been cached, and instead of execution we actually do simple look-up.

**Contribution:** were collected cached query execution results with different sets of hints, and implemented `torch`-like `Dataset` and `DataLoader`, vectorisation procedure 
for query execution plans and local search procedure for efficient exploration of parameter space.
 
# 💡 Idea behind this benchmark

**H**int-**B**ased query **O**ptimisation (HBO) is an approach to optimising the query execution time that allows accelerating the workload execution without changing a single line of DBMS kernel code.
This is achieved by selecting the planner hyperparameters (*hints*) influencing the construction of the query execution plan. Despite the fact that this approach
can speed up query execution many times over (*check it!*), it is associated with a fundamental complexity - the search space **is exponential**, and the cost of exploring a "point" in it **depends on its execution time**.


# 🧐 Why is it useful? 

As a simple observation demonstrating the potential usefulness of this project, - it has allowed us to reduce the search space from exponential to **linear** with virtually no loss in performance. 

# 📦 Setup 

```shell
python -m pip install --upgrade pip
python3 -v venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo apt-get install -y p7zip-full
7za x data/raw/raw_data.7z -odata/raw
python3 process_raw_data.py
pytest || [ $? -eq 5 ]
```

# 🚀 How To 

The key object that allows emulation of DBMS operation is `Oracle` (terminology is taken from maths, no connection with @Oracle). The simplest examples of using its functionality are presented in `example.ipynb` 

[![example.ipynb](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/zinchse/hbo_bench/blob/main/example.ipynb)

# 🔗 Details

<details>
  <summary>Server's Settings</summary>

  All data were obtained on @OpenGauss RDBMS on the server with the following settings:

  | Parameter                          | Value          |
  |------------------------------------|----------------|
  | `max_process_memory`               | 200GB          |
  | `cstore_buffers`                   | 100GB          |
  | `work_mem`                         | 80GB           |
  | `effective_cache_size`             | 32GB           |
  | `standby_shared_buffers_fraction`  | 0.1            |
  | `shared_buffers`                   | 160GB          |

  | Parameter                          | Value          |
  |------------------------------------|----------------|
  | Architecture                       | aarch64        |
  | CPU op-mode(s)                     | 64-bit         |
  | Byte Order                         | Little Endian  |
  | CPU(s)                             | 128            |
  | On-line CPU(s) list                | 0-127          |
  | Thread(s) per core                 | 1              |
  | Core(s) per socket                 | 64             |
  | Socket(s)                          | 2              |
  | NUMA node(s)                       | 4              |
  | Vendor ID                          | HiSilicon      |
  | Model                              | 0              |
  | Model name                         | Kunpeng-920    |
  | Stepping                           | 0x1            |
  | CPU MHz                            | 2600.000       |
  | CPU max MHz                        | 2600.0000      |

</details>


<details>
  <summary>Hints</summary>
  
  We used the following list of hints, which are controlled by the corresponding global user configuration parameters (`GUC`s):
  
  ```python
  HINTS: "List[Hint]" = [
      "Nested Loop",
      "Merge",
      "Hash",
      "Bitmap",
      "Index Only Scan",
      "Index Scan",
      "Seq Scan",
  ]

  GUCS: "List[GUC]" = [
      "nestloop",
      "mergejoin",
      "hashjoin",
      "bitmapscan",
      "indexonlyscan",
      "indexscan",
      "seqscan",
  ]
  ```

  To enumerate all combinations of such hints, we simply use bit masks corresponding to the above order (the high bit is responsible for "Nested Loop", the low bit for "Seq Scan").
  
</details>



# 📚 References

There are 2 main papers about the hint-based query optimisation approach.

1. Marcus, Ryan, et al. "Bao: Making learned query optimization practical." *Proceedings of the 2021 International Conference on Management of Data*, 2021, pp. 1275-1288.

2. Anneser, Christoph, et al. "Autosteer: Learned query optimization for any SQL database." *Proceedings of the VLDB Endowment*, vol. 16, no. 12, 2023, pp. 3515-3527.
