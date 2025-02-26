# Assignment ea-03-climate

This repository contains the notebooks for this week's assignment. Complete
the homework in each .ipynb notebook, commit your work, and push the changes
to github. Your instructor will pull the completed assignment after the
deadline.

Once grading is complete, your instructor will push the results to a file
called `feedback.html`. You will need to pull the changes to your local copy
and open this file in a browser to view (because GitHub will not render html 
files).


Run locally
----

### Download/Clone Git Repository

    $cd <replace with desired location of project folder>
    $git clone https://github.com/earthlab-education/habitat-suitability-lauren-alexandra.git
    $cd habitat-suitability-lauren-alexandra

### Create Environment

    $conda create -n myenv python=3.11.11
    $conda activate myenv

### Install required packages

    $conda install pip conda-forge::dask conda-forge::xarray-spatial
    $pip install -r requirements.txt

### Set up Jupyter Notebook Kernel

    $pip install --user ipykernel
    $python -m ipykernel install --user --name=myenv

### Launch Jupyter Notebook

    (in git bash or other conda environment)
    $jupyter notebook

