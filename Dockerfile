FROM fermipy/fermipy:latest
MAINTAINER Stephan Zimmer <zimmer@slac.stanford.edu>
RUN conda update -n base conda
RUN rm -v /opt/conda/conda-meta/ipaddress-1.0.22-py_1.json
RUN conda install -c conda-forge cython numpy astropy click regions ipaddress jupyterlab
RUN python -m pip install --user git+https://github.com/gammapy/gammapy.git
RUN python -m pip install --user git+https://github.com/fermipy/fermipy.git
EXPOSE 8888
CMD ["usleep 10 && /opt/conda/bin/jupyter lab --notebook-dir=/workdir --ip='*' --port=8888 --no-browser --allow-root"]
ENTRYPOINT ["/bin/bash","--login","-c"]
