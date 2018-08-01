# ATCProcessor
[![Maintainability](https://api.codeclimate.com/v1/badges/084540289a09096fbc62/maintainability)](https://codeclimate.com/github/TransportScotland/ATCProcessor/maintainability)
[![Build Status](https://travis-ci.org/TransportScotland/ATCProcessor.svg?branch=master)](https://travis-ci.org/TransportScotland/ATCProcessor)
[![codecov](https://codecov.io/gh/TransportScotland/ATCProcessor/branch/master/graph/badge.svg)](https://codecov.io/gh/TransportScotland/ATCProcessor)

A Python interface for generalised processing of Automatic Traffic Counter data. In the main, this is aimed towards working with Transport Scotland's National Traffic Data System (NTDS) (formerly SRTDb) outputs, however it should be possible to process any ATC data in column-based CSV form. Generally, this is best suited to long-term datasets, however there may be some use in cleaning short-term data.

## Running the Processor
Once development has reached a stable state executable files will be provided for widespread use of the processor, however at present any user testing should be doing through a Python install. The use of Anaconda is recommended.

### Downloading the source code
#### Git users
Users of Git can clone the repository with:
```
git clone https://github.com/TransportScotland/ATCProcessor.git
```
#### Other users
Download the latest version of the source files in a zip folder from [here](https://github.com/TransportScotland/ATCProcessor/archive/master.zip).

### Setting up the environment
To set up the Conda environment, in an Anaconda Prompt window with the current directory set to the location of the downloaded source code, the user can use:
```
conda env create -f environment.yml
```
This will create an environment called `atcprocessor`.

### Viewing the GUI
With the Anaconda environment activated, the user can view the GUI through:
```
python gui.py
```
