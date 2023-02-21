FROM ubuntu:20.04

# Install GL libraries
RUN apt-get -qq update && apt-get -qq -y install libgl1-mesa-glx build-essential gcc

# Install conda
RUN apt-get -qq update && apt-get -qq -y install curl bzip2 \
    && curl -sSL https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -o /tmp/miniconda.sh \
    && bash /tmp/miniconda.sh -bfp /usr/local \
    && rm -rf /tmp/miniconda.sh

RUN conda install -y python=3 \
    && conda update -y conda \
    && apt-get -qq -y remove curl bzip2 \
    && apt-get -qq -y autoremove \
    && apt-get autoclean \
    && rm -rf /var/lib/apt/lists/* /var/log/dpkg.log \
    && conda clean --all --yes
# Make conda activate command available from /bin/bash --interactive shells.
RUN conda init bash

# Workdir and input/output/log dir
WORKDIR .
RUN mkdir input output log

# Create conda environment
COPY environment_pysteps_git.yml .
RUN conda env create -f environment_pysteps_git.yml -n fmippn
RUN echo "conda activate fmippn" >> ~/.profile

# Copy fmippn directory
COPY fmippn /fmippn

# Disable dask
RUN export OMP_NUM_THREADS=1
RUN export HDF5_USE_FILE_LOCKING=FALSE

# Run
WORKDIR /fmippn
ENV domain ravake
ENV timestamp 201908230500
ENTRYPOINT conda run -n fmippn python run_ppn.py --config=$domain --timestamp=$timestamp

