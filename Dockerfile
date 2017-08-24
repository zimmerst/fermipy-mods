FROM fermipy/fermist:11-05-02
MAINTAINER Stephan Zimmer <zimmer@slac.stanford.edu>
ARG PYTHON_VERSION=2.7
ARG CONDA_DOWNLOAD=Miniconda-latest-Linux-x86_64.sh
ARG CONDA_DEPS="scipy matplotlib pyyaml ipython jupyter pandas"
ARG CONDA_DEPS_EXTRA="wcsaxes healpy subprocess32"
ARG PIP_DEPS=""
ENV PATH /opt/conda/bin:$PATH
RUN echo 'export PATH=/opt/conda/bin:$PATH' > /etc/profile.d/conda.sh && \
    curl -o miniconda.sh -L http://repo.continuum.io/miniconda/$CONDA_DOWNLOAD && \
    /bin/bash miniconda.sh -b -p /opt/conda && \
    rm miniconda.sh && conda update -y conda && conda config --append channels conda-forge 
RUN conda install -y python=$PYTHON_VERSION pip numpy astropy pytest $CONDA_DEPS && \
    conda install -y $CONDA_DEPS_EXTRA && \
    if [[ -n $PIP_DEPS ]]; then pip install $PIP_DEPS; fi
RUN conda install -y fermipy
RUN mkdir /workdir
ENV FERMI_DIFFUSE_DIR=/home/externals/diffuseModels/v5r0
ENV SLAC_ST_BUILD=true
ENV INST_DIR=/home/ScienceTools
ENV GLAST_EXT=/home/externals
ENV MATPLOTLIBRC=/home/matplotlib
RUN echo "source $INST_DIR/bin/redhat6-x86_64-64bit-gcc44-Optimized/_setup.sh" >> /root/.bashrc && \
    mkdir /home/matplotlib && echo "backend      : Agg" >> /home/matplotlib/matplotlibrc
RUN cd /home
RUN mkdir /home/pointlike
RUN curl -o pointlike.tgz -k -L https://dampevm3.unige.ch/misc/pointlike-20170824.tgz && \
    tar xzvf pointlike.tgz -C /home && \
    echo 'export PYTHONPATH=/home/pointlike/python:${PYTHONPATH}' >> /root/.bashrc
RUN ls -la /home
CMD ["usleep 10 && /opt/conda/bin/jupyter notebook --notebook-dir=/workdir --ip='*' --port=8888 --no-browser --allow-root"]
ENTRYPOINT ["/bin/bash","--login","-c"]