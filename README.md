##*FLO*##

FLO is written as an RF circuit simulation tool based on the concept of signal flow.  Different from the conventional way of matrix manipulation, the FLO algorithm is simple and intuitive, sending input to one node and let it transmit and reflect at all the nodes until the steady state is achieved.  

![simulation of a LPF](/sim_files/lpf.png)
![simulation of a BPF](/sim_files/bpf.png)


**Progress:**

1. Currently, only L, R, C elements available for passive filter designing.

2. Currently, only two port network can be simulated.  The output results will be written into a .s2p file.

3. Future - add graph GUI in the later stage.

4. Future - add tools to analize data, such as plotting gain circles.

5. Future - add more element libraries.


**Prerequisite:**

1. Python 2.7.x or 3.x

2. gnuplot for making plot


**Usage:**

Retrieve git repository.
```
git clone https://github.com/antopenrf/FLO.git
```

Then start the program.
```
cd FLO
python sim.py [file_name.sim to run, e.g lpf.sim]

or

pypy sim.py [file to run] ## pypy can speed up the simulation.
```

All the simulation files are put under sim_files folder.  Two design examples can be found under this folder, lpf.sim and bpf.sim.  If no input sim file is given, the program will run lpf.sim as default.  The output files are one .s2p file and one .plt file.  The .plt file is used to make plot by gnuplot.  Here is the command to make plot.  The output of the plot.sh script is named as output.png.
```
cd sim_files
sh plot.sh (file_name.plt to plot, e.g. lpf.plt)
open output.png
```


